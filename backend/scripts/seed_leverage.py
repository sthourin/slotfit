"""
Seed exercises.bodyweight_fraction from the curated table.

Idempotent: re-running rewrites the curated rows with the same values and
leaves everything else untouched. Like the pattern seed, this is NOT run by app
startup, Alembic, or CI - run it by hand on every database.

Run from backend/: python -m scripts.seed_leverage
"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.exercise import Exercise
from app.services.leverage import CURATED_FRACTIONS


async def seed_leverage(db) -> tuple[int, list[str]]:
    """Write curated fractions. Returns (rows updated, names not found)."""
    updated = 0
    missing: list[str] = []
    for name, fraction in CURATED_FRACTIONS.items():
        exercise = (
            await db.execute(select(Exercise).where(Exercise.name == name))
        ).scalar_one_or_none()
        if exercise is None:
            missing.append(name)
            continue
        exercise.bodyweight_fraction = fraction
        updated += 1
    await db.commit()
    return updated, missing


async def main() -> None:
    async with AsyncSessionLocal() as db:
        updated, missing = await seed_leverage(db)
        for name in missing:
            # A miss means the curated table names an exercise the catalogue
            # does not have. Fix the table - do not rename the exercise.
            print(f"  skip (not found): {name}")
        print(f"Seeded {updated} bodyweight fractions.")


if __name__ == "__main__":
    asyncio.run(main())
