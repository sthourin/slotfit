"""
Movement pattern taxonomy: curated pattern list, seed helpers, and the
rollup that classifies raw exercise movement patterns into the curated ten.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movement_pattern import MovementPattern

# Curated taxonomy. Opposites drive antagonist pairing; neutral patterns
# are valid as a superset's third entry with any pair.
PATTERNS: list[dict] = [
    {"slug": "horizontal_pull", "name": "Horizontal Pull", "opposite": "horizontal_push", "is_neutral": False, "display_order": 1},
    {"slug": "horizontal_push", "name": "Horizontal Push", "opposite": "horizontal_pull", "is_neutral": False, "display_order": 2},
    {"slug": "vertical_pull", "name": "Vertical Pull", "opposite": "vertical_push", "is_neutral": False, "display_order": 3},
    {"slug": "vertical_push", "name": "Vertical Push", "opposite": "vertical_pull", "is_neutral": False, "display_order": 4},
    {"slug": "knee_dominant", "name": "Knee Dominant", "opposite": "hip_hinge", "is_neutral": False, "display_order": 5},
    {"slug": "hip_hinge", "name": "Hip Hinge", "opposite": "knee_dominant", "is_neutral": False, "display_order": 6},
    {"slug": "core", "name": "Core", "opposite": None, "is_neutral": True, "display_order": 7},
    {"slug": "carry", "name": "Carry / Locomotion", "opposite": None, "is_neutral": True, "display_order": 8},
    {"slug": "isolation", "name": "Isolation", "opposite": None, "is_neutral": True, "display_order": 9},
    {"slug": "conditioning", "name": "Conditioning", "opposite": None, "is_neutral": True, "display_order": 10},
]


async def seed_movement_patterns(db: AsyncSession) -> None:
    """Idempotently seed the curated movement patterns and wire opposites."""
    result = await db.execute(select(MovementPattern))
    existing = {p.slug: p for p in result.scalars().all()}

    # Pass 1: ensure rows exist
    for spec in PATTERNS:
        if spec["slug"] not in existing:
            row = MovementPattern(
                slug=spec["slug"],
                name=spec["name"],
                is_neutral=spec["is_neutral"],
                display_order=spec["display_order"],
            )
            db.add(row)
            existing[spec["slug"]] = row
    await db.flush()

    # Pass 2: wire opposite FKs by slug
    for spec in PATTERNS:
        opposite_slug = spec["opposite"]
        existing[spec["slug"]].opposite_pattern_id = (
            existing[opposite_slug].id if opposite_slug else None
        )
    await db.commit()
