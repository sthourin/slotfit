"""
Seed the movement pattern taxonomy and exercise->pattern map.
Run from backend/: python -m scripts.seed_patterns
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.services.pattern_taxonomy import seed_movement_patterns, seed_exercise_pattern_map


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed_movement_patterns(db)
        written = await seed_exercise_pattern_map(db)
        print(f"Patterns seeded; exercise map rows written/updated: {written}")


if __name__ == "__main__":
    asyncio.run(main())
