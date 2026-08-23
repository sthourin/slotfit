"""How much of a person's bodyweight each movement actually loads.

Applying one number to everything would be worse than useless: a push-up moves
roughly two thirds of bodyweight, a pull-up all of it, an arm circle almost
none. An e1RM computed without that distinction is not comparable across
exercises, which is the only thing it is for.

Only the movements the user actually trains are curated. Everything else gets
DEFAULT_BODYWEIGHT_FRACTION, which is the push-up value rather than 1.0 -
assuming full bodyweight for hundreds of unreviewed catalogue rows would
overstate load far more often than it would be right.

Values are conventional strength-training estimates, not measurements. They are
differentiated and defensible, not exact; adjust one and re-run
`scripts.seed_leverage`.
"""

# Push-up. The most common bodyweight movement shape in the catalogue, and a
# deliberately conservative stand-in for anything uncurated.
DEFAULT_BODYWEIGHT_FRACTION = 0.64

CURATED_FRACTIONS: dict[str, float] = {
    # Plank-support upper body: hands and feet share the load.
    "Bodyweight Push Up": 0.64,
    "Plank Jacks": 0.64,
    "Bodyweight Mountain Climber (HIIT AMRAP)": 0.64,
    # Full lower body: trunk and both legs above the knee joint. The jumping
    # variants move the same mass - the jump adds velocity, not load.
    "Bodyweight Squat": 0.85,
    "Bodyweight Walking Lunge": 0.85,
    "Bodyweight Squat Jump": 0.85,
    "Jumping Lunge": 0.85,
    "Bodyweight Skater Jump (HIIT AMRAP)": 0.85,
    # Composite: push-up and squat-jump phases in one movement.
    "Bodyweight HIIT Burpee": 0.70,
    # Partially supported.
    "Bodyweight Glute Bridge": 0.55,
    "Bodyweight Copenhagen Plank": 0.50,
    # Trunk and limbs only.
    "Bodyweight Crunch": 0.35,
    "Superman": 0.35,
    "High Knees": 0.30,
    "Arm Circles": 0.05,
    # Locomotion. Walking and running carry the whole body over ground, so the
    # fraction is 1.0 rather than the push-up default, which describes a
    # supported movement and is meaningless here. External load adds on top -
    # `effective_load` does that already - so a ruck resolves to bodyweight plus
    # the pack, which is exactly what the legs are moving.
    "Rucking": 1.0,
    "Bodyweight Walk": 1.0,
    "Bodyweight Run": 1.0,
    "Bodyweight March": 1.0,
}

# Ergometers are deliberately absent. A rower, air bike or ski erg has its own
# equipment row, so `is_bodyweight` is false and `effective_load` returns the
# logged weight - which is None, because an erg reports no load. They therefore
# contribute no tonnage without needing a fraction, and adding one here would be
# dead configuration that reads as though it did something. Their duration and
# distance are what describe the effort, and those are counted in full.


def fraction_for(name: str, stored: float | None) -> float:
    """Resolve a movement's bodyweight fraction.

    `stored` is the seeded column value and wins when present, so a
    hand-adjusted row is not silently overridden by this table at read time.
    """
    if stored is not None:
        return stored
    return CURATED_FRACTIONS.get(name, DEFAULT_BODYWEIGHT_FRACTION)
