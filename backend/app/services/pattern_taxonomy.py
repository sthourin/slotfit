"""
Movement pattern taxonomy: curated pattern list, seed helpers, and the
rollup that classifies raw exercise movement patterns into the curated ten.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movement_pattern import MovementPattern, ExercisePatternMap
from app.models.exercise import Exercise

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


# Raw movement_pattern_1 values that always classify as core, regardless of mechanics
CORE_RAW = {
    "Anti-Extension", "Anti-Rotational", "Anti-Lateral Flexion",
    "Spinal Flexion", "Spinal Extension", "Rotational", "Isometric Hold",
}

# Direct raw -> curated mapping for compound movements
DIRECT_MAP = {
    "Horizontal Pull": "horizontal_pull",
    "Vertical Pull": "vertical_pull",
    "Horizontal Push": "horizontal_push",
    "Horizontal Adduction": "horizontal_push",
    "Vertical Push": "vertical_push",
    "Knee Dominant": "knee_dominant",
    "Hip Hinge": "hip_hinge",
    "Hip Extension": "hip_hinge",
}


def classify_exercise(raw_pattern: str | None, mechanics: str | None) -> str:
    """Roll up a raw movement pattern + mechanics into a curated pattern slug.

    Rule order matters: core > carry/conditioning > isolation mechanics > direct map > isolation fallback.
    """
    raw = (raw_pattern or "").strip()
    if raw in CORE_RAW:
        return "core"
    if raw == "Loaded Carry":
        return "carry"
    if raw == "Locomotion":
        return "conditioning"
    if (mechanics or "").strip() == "Isolation":
        return "isolation"
    return DIRECT_MAP.get(raw, "isolation")


async def seed_exercise_pattern_map(db: AsyncSession) -> int:
    """Classify every exercise into the map. Preserves is_override rows. Returns rows written."""
    result = await db.execute(select(MovementPattern))
    pattern_by_slug = {p.slug: p for p in result.scalars().all()}

    result = await db.execute(select(ExercisePatternMap))
    existing = {m.exercise_id: m for m in result.scalars().all()}

    result = await db.execute(select(Exercise))
    written = 0
    for exercise in result.scalars().all():
        slug = classify_exercise(exercise.movement_pattern_1, exercise.mechanics)
        pattern_id = pattern_by_slug[slug].id
        row = existing.get(exercise.id)
        if row is None:
            db.add(ExercisePatternMap(exercise_id=exercise.id, pattern_id=pattern_id))
            written += 1
        elif not row.is_override and row.pattern_id != pattern_id:
            row.pattern_id = pattern_id
            written += 1
    await db.commit()
    return written
