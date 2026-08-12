"""
Backfill SlotFit history from the local Hevy export.

Imports completed workouts into the legacy workout tables and dated bodyweight
readings, converting Hevy's kilograms to pounds on the way in.

Reads `hevy/data/workouts.json`, `hevy/data/body_measurements.json` and the
reviewed `hevy/exercise_map.yaml`. No Hevy API call is made.

Dry run by default, because this writes years of history:

    python -m scripts.backfill_hevy --device-id setup-verify-0001
    python -m scripts.backfill_hevy --device-id setup-verify-0001 --commit

Both halves are idempotent: workouts on (user, started_at), readings on the
(user, recorded_at, source) unique constraint. Re-running is safe.
"""
import argparse
import asyncio
import json
from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.hevy_backfill import (
    backfill_bodyweight,
    backfill_workouts,
    exercises_by_name,
    title_map_from_document,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "hevy"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


async def main(device_id: str, commit: bool) -> None:
    workouts = _load(DATA_DIR / "data" / "workouts.json")
    measurements = _load(DATA_DIR / "data" / "body_measurements.json")
    document = yaml.safe_load((DATA_DIR / "exercise_map.yaml").read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.device_id == device_id))
        ).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"No user with device_id {device_id!r}")

        mapping = title_map_from_document(document, await exercises_by_name(db))
        print(f"Resolved {len(mapping)} Hevy titles to SlotFit exercises.")
        print(f"Source: {len(workouts)} workouts, {len(measurements)} measurements.")

        if not commit:
            titles = {e.get("title") for w in workouts for e in (w.get("exercises") or [])}
            unmapped = sorted(t for t in titles if t and t not in mapping)
            covered = sum(
                len(e.get("sets") or [])
                for w in workouts
                for e in (w.get("exercises") or [])
                if e.get("title") in mapping
            )
            total = sum(
                len(e.get("sets") or [])
                for w in workouts
                for e in (w.get("exercises") or [])
            )
            print(f"\nDRY RUN - nothing written.")
            print(f"  sets covered by the reviewed map: {covered}/{total}")
            print(f"  titles with no mapping: {len(unmapped)}")
            for title in unmapped[:15]:
                print(f"    - {title}")
            if len(unmapped) > 15:
                print(f"    ... and {len(unmapped) - 15} more")
            print("\nRe-run with --commit to write.")
            return

        sessions, sets, unmapped_sets = await backfill_workouts(
            db, user, workouts, mapping
        )
        created, skipped = await backfill_bodyweight(db, user, measurements)
        print(f"\nWorkouts:   {sessions} sessions, {sets} sets imported.")
        print(f"            {unmapped_sets} sets skipped (title not in the reviewed map).")
        print(f"Bodyweight: {created} readings imported, {skipped} skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True)
    parser.add_argument(
        "--commit", action="store_true", help="Write. Without this, reports only."
    )
    args = parser.parse_args()
    asyncio.run(main(args.device_id, args.commit))
