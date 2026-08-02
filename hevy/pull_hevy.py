"""Pull a full snapshot of a Hevy account via the public Hevy API.

Reads only. Writes one JSON file per resource into an output directory, plus a
manifest describing the run.

Auth: Hevy uses an ``api-key`` request header. The key is resolved, in order,
from ``--api-key``, the ``HEVY_API_KEY`` environment variable, then
``HEVY_API_KEY`` in the repo-root ``.env``. Keys are never written to the output.

Usage:
    python hevy/pull_hevy.py                 # full snapshot into hevy/data/
    python hevy/pull_hevy.py --out snap2     # snapshot into hevy/snap2/
    python hevy/pull_hevy.py --only workouts routines
    python hevy/pull_hevy.py --max-pages 3   # smoke test

Requires a Hevy Pro account. Get a key at https://hevy.com/settings?developer
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

BASE_URL = "https://api.hevyapp.com"
REPO_ROOT = Path(__file__).resolve().parent.parent

# name -> (path, response key holding the list, max pageSize allowed by the API)
PAGINATED_RESOURCES: dict[str, tuple[str, str, int]] = {
    "workouts": ("/v1/workouts", "workouts", 10),
    "routines": ("/v1/routines", "routines", 10),
    "routine_folders": ("/v1/routine_folders", "routine_folders", 10),
    "exercise_templates": ("/v1/exercise_templates", "exercise_templates", 100),
    "body_measurements": ("/v1/body_measurements", "body_measurements", 10),
}
SINGLETON_RESOURCES: dict[str, str] = {
    "user_info": "/v1/user/info",
    "workout_count": "/v1/workouts/count",
}
ALL_RESOURCES = list(SINGLETON_RESOURCES) + list(PAGINATED_RESOURCES)


class HevyError(RuntimeError):
    pass


def _read_env_file(path: Path, key: str) -> str | None:
    """Pull a single KEY=value out of a dotenv file without extra deps."""
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == key:
            return value.strip().strip("'\"") or None
    return None


def resolve_api_key(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    from_env = os.environ.get("HEVY_API_KEY")
    if from_env:
        return from_env.strip()
    from_file = _read_env_file(REPO_ROOT / ".env", "HEVY_API_KEY")
    if from_file:
        return from_file
    raise HevyError(
        f"No Hevy API key found. Set HEVY_API_KEY in {REPO_ROOT / '.env'}, export it, "
        "or pass --api-key. Get a key at https://hevy.com/settings?developer"
    )


class HevyClient:
    def __init__(self, api_key: str, *, delay: float = 0.2, retries: int = 4) -> None:
        self._api_key = api_key
        self._delay = delay
        self._retries = retries
        self.request_count = 0

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = BASE_URL + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url,
            headers={
                "api-key": self._api_key,
                "Accept": "application/json",
                "User-Agent": "slotfit-hevy-pull/1.0",
            },
        )

        last_error: Exception | None = None
        for attempt in range(self._retries):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    self.request_count += 1
                    time.sleep(self._delay)
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")[:400]
                if exc.code in (401, 403):
                    raise HevyError(
                        f"{exc.code} from {path}: the API key was rejected. Confirm the "
                        f"key is current and the account has Hevy Pro. Response: {body}"
                    ) from exc
                if exc.code == 429 or exc.code >= 500:
                    wait = float(exc.headers.get("Retry-After") or 2 ** attempt)
                    print(f"  {exc.code} on {path}; retrying in {wait:.0f}s", file=sys.stderr)
                    time.sleep(wait)
                    last_error = exc
                    continue
                raise HevyError(f"{exc.code} from {path}: {body}") from exc
            except urllib.error.URLError as exc:
                wait = 2 ** attempt
                print(f"  network error on {path} ({exc.reason}); retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                last_error = exc

        raise HevyError(f"Gave up on {path} after {self._retries} attempts: {last_error}")

    def paginate(
        self, path: str, list_key: str, page_size: int, max_pages: int | None
    ) -> Iterator[list[dict]]:
        page = 1
        while max_pages is None or page <= max_pages:
            payload = self.get(path, {"page": page, "pageSize": page_size})
            if not isinstance(payload, dict) or list_key not in payload:
                raise HevyError(
                    f"Unexpected response shape from {path} page {page}: "
                    f"expected key '{list_key}', got {list(payload)[:8] if isinstance(payload, dict) else type(payload)}"
                )
            items = payload[list_key] or []
            yield items
            page_count = payload.get("page_count")
            if not items or (isinstance(page_count, int) and page >= page_count):
                return
            page += 1


def pull(client: HevyClient, resources: list[str], out_dir: Path, max_pages: int | None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "resources": {},
    }

    for name in resources:
        if name in SINGLETON_RESOURCES:
            print(f"Fetching {name} ...", flush=True)
            data = client.get(SINGLETON_RESOURCES[name])
            count: int | None = None
            if name == "workout_count" and isinstance(data, dict):
                count = data.get("workout_count")
        else:
            path, list_key, max_page_size = PAGINATED_RESOURCES[name]
            records: list[dict] = []
            for page_items in client.paginate(path, list_key, max_page_size, max_pages):
                records.extend(page_items)
                print(f"Fetching {name} ... {len(records)}", end="\r", flush=True)
            print(f"Fetching {name} ... {len(records)} records" + " " * 12, flush=True)
            data = records
            count = len(records)

        target = out_dir / f"{name}.json"
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest["resources"][name] = {
            "file": target.name,
            "count": count,
            "truncated": bool(max_pages) and name in PAGINATED_RESOURCES,
        }

    manifest["request_count"] = client.request_count
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def summarize(out_dir: Path) -> None:
    """Print a short human-readable summary of whatever landed in out_dir."""
    workouts_file = out_dir / "workouts.json"
    if not workouts_file.is_file():
        return
    workouts = json.loads(workouts_file.read_text(encoding="utf-8"))
    if not workouts:
        return

    dates = sorted(w.get("start_time", "") for w in workouts if w.get("start_time"))
    sets = sum(len(e.get("sets") or []) for w in workouts for e in (w.get("exercises") or []))
    tally: dict[str, int] = {}
    for workout in workouts:
        for exercise in workout.get("exercises") or []:
            title = exercise.get("title") or exercise.get("exercise_template_id") or "?"
            tally[title] = tally.get(title, 0) + len(exercise.get("sets") or [])

    print()
    print(f"Workouts:  {len(workouts)}")
    if dates:
        print(f"Range:     {dates[0][:10]} to {dates[-1][:10]}")
    print(f"Total sets: {sets}")
    print("Most-logged exercises by set count:")
    for title, n in sorted(tally.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {n:5}  {title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull a Hevy account snapshot to JSON.")
    parser.add_argument("--api-key", help="Hevy API key (prefer HEVY_API_KEY in a .env instead)")
    parser.add_argument("--out", default="data", help="Output dir, relative to hevy/ (default: data)")
    parser.add_argument(
        "--only", nargs="+", choices=ALL_RESOURCES, help="Limit the pull to these resources"
    )
    parser.add_argument("--max-pages", type=int, help="Stop each resource after N pages (smoke test)")
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds between requests")
    args = parser.parse_args(argv)

    try:
        api_key = resolve_api_key(args.api_key)
    except HevyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = Path(__file__).resolve().parent / out_dir

    client = HevyClient(api_key, delay=args.delay)
    try:
        manifest = pull(client, args.only or ALL_RESOURCES, out_dir, args.max_pages)
    except HevyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"\nWrote {len(manifest['resources'])} files to {out_dir}")
    summarize(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
