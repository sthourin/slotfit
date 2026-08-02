"""Seed a user's staple pool from a pulled Hevy history.

Two steps, with a human review in between:

    python -m scripts.hevy_staples generate       # writes hevy/exercise_map.yaml
    # ... edit the file, resolving every entry ...
    python -m scripts.hevy_staples apply          # dry run, prints the plan
    python -m scripts.hevy_staples apply --commit # writes

Run from backend/. Requires hevy/data/*.json from hevy/pull_hevy.py and a
database where scripts.seed_patterns has been run.
"""

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Equipment, Exercise, MovementPattern, User
from app.services.hevy_import import (
    MACHINE_EQUIPMENT,
    CatalogueEntry,
    apply_map,
    build_map_document,
    dump_map,
    select_exercises,
    validate_map,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "hevy" / "data"
MAP_PATH = REPO_ROOT / "hevy" / "exercise_map.yaml"


def _load_hevy_data() -> tuple[list[dict], dict[str, dict]]:
    workouts_path = DATA_DIR / "workouts.json"
    templates_path = DATA_DIR / "exercise_templates.json"
    if not workouts_path.is_file():
        raise SystemExit(
            f"error: {workouts_path} not found. Run: python hevy/pull_hevy.py"
        )
    workouts = json.loads(workouts_path.read_text(encoding="utf-8"))
    templates = {}
    if templates_path.is_file():
        templates = {
            t["id"]: t for t in json.loads(templates_path.read_text(encoding="utf-8"))
        }
    return workouts, templates


async def _resolve_user(db, device_id: str | None) -> User:
    if device_id:
        user = (
            await db.execute(select(User).where(User.device_id == device_id))
        ).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"error: no user with device_id {device_id!r}")
        return user
    users = (await db.execute(select(User))).scalars().all()
    if not users:
        raise SystemExit("error: no users in the database")
    if len(users) > 1:
        ids = ", ".join(u.device_id or f"id={u.id}" for u in users)
        raise SystemExit(f"error: several users exist, pass --device-id. Found: {ids}")
    print(f"Targeting the only user: {users[0].device_id}")
    return users[0]


async def generate(args: argparse.Namespace) -> int:
    workouts, templates = _load_hevy_data()
    exercises = select_exercises(
        workouts,
        templates,
        window_days=args.window_days,
        min_sessions=args.min_sessions,
    )
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Exercise.name, Equipment.name).outerjoin(
                    Equipment, Exercise.primary_equipment_id == Equipment.id
                )
            )
        ).all()
    catalogue = [CatalogueEntry(name=n, equipment=e) for n, e in rows]

    document = build_map_document(
        exercises,
        catalogue,
        generated_at=date.today().isoformat(),
        window_days=args.window_days,
        min_sessions=args.min_sessions,
    )
    MAP_PATH.write_text(dump_map(document), encoding="utf-8")

    prefilled = sum(1 for r in document["exercises"] if r["slotfit"])
    total = len(document["exercises"])
    print(f"Wrote {MAP_PATH}")
    print(f"  {total} exercises, {prefilled} pre-filled, {total - prefilled} to review")
    return 0


async def apply(args: argparse.Namespace) -> int:
    if not MAP_PATH.is_file():
        raise SystemExit(
            f"error: {MAP_PATH} not found. Run: python -m scripts.hevy_staples generate"
        )
    document = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as db:
        known_exercises = set((await db.execute(select(Exercise.name))).scalars().all())
        known_patterns = set(
            (await db.execute(select(MovementPattern.slug))).scalars().all()
        )
        if not known_patterns:
            raise SystemExit(
                "error: movement_patterns is empty. Run: python -m scripts.seed_patterns"
            )
        known_equipment = set(
            (await db.execute(select(Equipment.name))).scalars().all()
        ) | {name for name, _ in MACHINE_EQUIPMENT}

        errors = validate_map(document, known_exercises, known_patterns, known_equipment)
        if errors:
            print(f"{len(errors)} problem(s) in {MAP_PATH}:", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            return 1

        user = await _resolve_user(db, args.device_id)
        result = await apply_map(db, document, user)

        print(f"  equipment created : {result.equipment_created}")
        print(f"  exercises created : {result.exercises_created}")
        print(f"  staples created   : {result.staples_created}")
        print(f"  already staple    : {result.skipped_existing}")
        print(f"  no pattern mapping: {result.skipped_no_pattern}")
        print(f"  skipped (SKIP)    : {result.skipped_explicit}")

        if args.commit:
            await db.commit()
            print("Committed.")
        else:
            await db.rollback()
            print("Dry run - nothing written. Re-run with --commit to apply.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="write the reviewable mapping file")
    gen.add_argument("--window-days", type=int, default=365)
    gen.add_argument("--min-sessions", type=int, default=3)
    gen.set_defaults(func=generate)

    app = sub.add_parser("apply", help="seed staples from the reviewed mapping file")
    app.add_argument("--commit", action="store_true", help="actually write")
    app.add_argument("--device-id", help="target user; optional when only one exists")
    app.set_defaults(func=apply)

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
