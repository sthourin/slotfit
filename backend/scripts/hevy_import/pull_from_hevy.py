"""
Pull full workout history from Hevy API and save in SlotFit import format.

Usage:
    cd backend
    python scripts/hevy_import/pull_from_hevy.py
    python scripts/hevy_import/pull_from_hevy.py --output custom_output.json
"""
import json
import sys
import argparse
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

HEVY_API_BASE = "https://api.hevyapp.com/v1"


def get_api_key() -> str:
    """Get Hevy API key from environment or .env file"""
    import os
    key = os.environ.get("HEVY_API_KEY")
    if key:
        return key

    # Try reading from hevy-mcp-clone .env
    env_path = Path("C:/Projects/hevy-mcp-clone/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("HEVY_API_KEY="):
                return line.split("=", 1)[1].strip()

    print("Error: HEVY_API_KEY not found in environment or C:/Projects/hevy-mcp-clone/.env")
    sys.exit(1)


def fetch_workout_count(client: httpx.Client) -> int:
    """Get total workout count from Hevy API"""
    resp = client.get(f"{HEVY_API_BASE}/workouts/count")
    resp.raise_for_status()
    return resp.json()["workout_count"]


def fetch_all_workouts(client: httpx.Client, total: int) -> list[dict[str, Any]]:
    """Fetch all workouts page by page (max 10 per page)"""
    all_workouts: list[dict[str, Any]] = []
    page = 1
    page_size = 10

    while len(all_workouts) < total:
        print(f"  Fetching page {page} (got {len(all_workouts)}/{total})...")
        resp = client.get(
            f"{HEVY_API_BASE}/workouts",
            params={"page": page, "pageSize": page_size},
        )
        resp.raise_for_status()
        data = resp.json()

        workouts = data.get("workouts", [])
        if not workouts:
            break

        all_workouts.extend(workouts)
        page += 1

        # Rate limit: be nice to the API
        time.sleep(0.3)

    return all_workouts


def transform_workout(hevy_workout: dict[str, Any]) -> dict[str, Any]:
    """Transform a single Hevy API workout to SlotFit import format"""
    exercises = []
    for ex in hevy_workout.get("exercises", []):
        sets = []
        for i, s in enumerate(ex.get("sets", []), start=1):
            set_data: dict[str, Any] = {
                "set_number": s.get("index", i - 1) + 1 if "index" in s else i,
                "type": s.get("type", "normal"),
                "weight_kg": s.get("weight_kg"),
                "reps": s.get("reps"),
                "rpe": s.get("rpe"),
                "duration_sec": s.get("duration_seconds"),
                "distance_m": s.get("distance_meters"),
            }
            sets.append(set_data)

        exercises.append({
            "name": ex.get("title", ex.get("exercise_template_id", "Unknown")),
            "hevy_template_id": ex.get("exercise_template_id", ""),
            "notes": ex.get("notes", ""),
            "sets": sets,
        })

    return {
        "hevy_id": hevy_workout.get("id", ""),
        "title": hevy_workout.get("title", "Untitled Workout"),
        "started_at": hevy_workout.get("start_time", ""),
        "completed_at": hevy_workout.get("end_time", ""),
        "exercises": exercises,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull workout history from Hevy API")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: hevy_workouts_data.json in same directory)",
    )
    args = parser.parse_args()

    api_key = get_api_key()
    print(f"Using Hevy API key: {api_key[:8]}...")

    client = httpx.Client(
        headers={"api-key": api_key},
        timeout=30.0,
    )

    try:
        # Get total count
        total = fetch_workout_count(client)
        print(f"\nTotal workouts in Hevy: {total}")

        # Fetch all workouts
        print("\nFetching all workouts...")
        raw_workouts = fetch_all_workouts(client, total)
        print(f"Fetched {len(raw_workouts)} workouts")

        # Transform to SlotFit format
        print("\nTransforming to SlotFit import format...")
        transformed = [transform_workout(w) for w in raw_workouts]

        # Sort by date (oldest first)
        transformed.sort(key=lambda w: w["started_at"])

        # Build output
        dates = [w["started_at"][:10] for w in transformed if w["started_at"]]
        output = {
            "export_date": time.strftime("%Y-%m-%d"),
            "date_range": {
                "start": min(dates) if dates else "",
                "end": max(dates) if dates else "",
            },
            "workouts": transformed,
        }

        # Save
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(__file__).parent / "hevy_workouts_data.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(transformed)} workouts to {output_path}")
        print(f"Date range: {output['date_range']['start']} to {output['date_range']['end']}")

        # Summary
        total_exercises = sum(len(w["exercises"]) for w in transformed)
        total_sets = sum(
            len(s)
            for w in transformed
            for e in w["exercises"]
            for s in [e["sets"]]
        )
        print(f"Total exercises: {total_exercises}")
        print(f"Total sets: {total_sets}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
