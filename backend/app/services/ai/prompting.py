"""Prompt construction and output schema shared by every AI provider.

`_build_context` and `_create_prompt` used to be duplicated, near byte for byte,
in `claude_provider.py` and `gemini_provider.py` - 155 lines each. They had
already drifted: the Claude copy asked the model for
`"movement_balance": "<boolean>"`, a quoted string, where the Gemini copy asked
for a real boolean. One source means a prompt improvement lands for every
provider and cannot drift again.

`RecommendationPayload` is the schema the model fills in. Constraining the
response replaces the old approach of asking for "only valid JSON, no additional
text" and then stripping markdown fences by hand - a parser that failed whenever
the model wrapped its answer in prose.
"""
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecommendationFactors(BaseModel):
    """Why an exercise scored the way it did.

    Typed rather than a free-form dict so the response schema can be strict.
    The keys match what `fallback_provider` emits and what the web client reads,
    so a recommendation looks the same whichever provider produced it.
    """

    # Defaults throughout. A provider constrained by this schema fills every
    # field, but one that only reads the JSON description in the prompt may omit
    # any of them - and losing a whole recommendation over a missing
    # `variety_boost` flag trades the useful part for the decorative part.
    frequency: str = Field(default="medium", description="low | medium | high")
    last_performed: Optional[str] = Field(
        default=None, description="ISO 8601 date, or null if never performed"
    )
    progression_opportunity: bool = False
    variety_boost: bool = False
    weekly_volume_status: str = Field(default="low", description="low | moderate | high")
    movement_balance: bool = Field(
        default=False,
        description="true if this exercise helps balance the workout's movement patterns",
    )


class RecommendedExercise(BaseModel):
    exercise_id: int
    exercise_name: str
    priority_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    factors: RecommendationFactors


class NotRecommended(BaseModel):
    exercise_id: int
    exercise_name: str
    reason: str = Field(
        description=(
            "Human-readable explanation, e.g. 'Equipment not available: Cable "
            "Machine', 'Weekly volume exceeded for Chest (22 sets)', "
            "'Performed 1 day ago - insufficient recovery'"
        )
    )


class RecommendationPayload(BaseModel):
    """The whole model response. Providers convert this to RecommendationResponse."""

    recommendations: List[RecommendedExercise]
    not_recommended: List[NotRecommended] = []
    total_candidates: int = 0
    filtered_by_equipment: int = 0


# Most exercises a candidate list may carry. Equipment filtering already brings
# a realistic request down to tens of rows; this only guards the pathological
# case (a huge muscle group with everything available). Truncation is logged
# rather than silent - a quietly clipped list looks like "the AI never suggests
# X" and is impossible to diagnose from the outside.
MAX_CANDIDATES = 150


def build_context(
    muscle_group_ids: List[int],
    available_equipment_ids: List[int],
    user_workout_history: Optional[Dict[str, Any]],
    weekly_volume: Optional[Dict[int, Dict[str, Any]]],
    movement_patterns: Optional[Dict[str, Dict[str, int]]],
    injury_restrictions: Optional[List[Dict[str, Any]]],
    candidates: Optional[List[Dict[str, Any]]] = None,
    muscle_group_names: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """Assemble the facts a prompt is rendered from.

    `candidates` is the list the model must choose from, and `muscle_group_names`
    turns bare ids into words. Without both, the prompt said only
    "Target muscle groups: [17]" with no catalogue - so the model invented
    exercises and invented ids to match them. A request for Chest came back with
    "Dumbbell Lateral Raise" at id 1101, which is really Bar Pull Up. Every
    field was plausible and every one was wrong.
    """
    return {
        "muscle_group_ids": muscle_group_ids,
        "available_equipment_ids": available_equipment_ids,
        "user_history": user_workout_history or {},
        "weekly_volume": weekly_volume or {},
        "movement_patterns": movement_patterns or {},
        "injury_restrictions": injury_restrictions or [],
        "candidates": candidates or [],
        "muscle_group_names": muscle_group_names or {},
    }


def format_candidates(candidates: List[Dict[str, Any]]) -> str:
    """The catalogue the model picks from, one exercise per line.

    Compact on purpose - id, name, equipment, mechanics - because the list can
    run to a hundred-plus rows and prose per row buys nothing.
    """
    if not candidates:
        return "None available."
    lines = []
    for row in candidates[:MAX_CANDIDATES]:
        equipment = row.get("equipment") or "bodyweight"
        mechanics = row.get("mechanics") or "?"
        lines.append(f"  {row['id']} | {row['name']} | {equipment} | {mechanics}")
    if len(candidates) > MAX_CANDIDATES:
        lines.append(
            f"  ... {len(candidates) - MAX_CANDIDATES} further candidates omitted "
            f"for length; choose from the {MAX_CANDIDATES} above."
        )
    return "\n".join(lines)


JSON_SHAPE_INSTRUCTIONS = """

Return your response as a JSON object with this exact structure:
{
    "recommendations": [
        {
            "exercise_id": <integer>,
            "exercise_name": "<string>",
            "priority_score": <float 0.0-1.0>,
            "reasoning": "<brief explanation>",
            "factors": {
                "frequency": "<low|medium|high>",
                "last_performed": "<ISO8601 date or null>",
                "progression_opportunity": <boolean>,
                "variety_boost": <boolean>,
                "weekly_volume_status": "<low|moderate|high>",
                "movement_balance": <boolean>
            }
        }
    ],
    "not_recommended": [
        {
            "exercise_id": <integer>,
            "exercise_name": "<string>",
            "reason": "<string>"
        }
    ],
    "total_candidates": <integer>,
    "filtered_by_equipment": <integer>
}

Only return valid JSON, no additional text."""


def create_prompt(
    context: Dict[str, Any], limit: int, *, include_json_shape: bool = False
) -> str:
    """Render the recommendation prompt.

    `include_json_shape` appends a literal description of the expected JSON.
    Providers that can constrain the response to `RecommendationPayload` leave
    it off - the schema is enforced, so describing it again only invites the
    two descriptions to disagree. Providers that parse free text need it, and
    for them the instruction is load-bearing: without it there is nothing
    telling the model what to emit.
    """
    weekly_volume = context.get("weekly_volume", {})

    weekly_volume_text = "None"
    if weekly_volume:
        volume_lines = []
        for mg_id, volume_data in weekly_volume.items():
            sets = volume_data.get("total_sets", 0)
            status = "high" if sets > 20 else "moderate" if sets > 10 else "low"
            volume_lines.append(f"  - Muscle group {mg_id}: {sets} sets/week ({status} volume)")
        weekly_volume_text = "\n".join(volume_lines) if volume_lines else "None"

    target_mg_ids = context.get("muscle_group_ids", [])
    high_volume_mgs = [
        mg_id
        for mg_id in target_mg_ids
        if mg_id in weekly_volume and weekly_volume[mg_id].get("total_sets", 0) > 20
    ]

    deprioritize_note = ""
    if high_volume_mgs:
        deprioritize_note = (
            f"\n\nIMPORTANT: The following target muscle groups have exceeded 20 sets "
            f"this week and should be DEPRIORITIZED: {high_volume_mgs}. Consider "
            f"recommending exercises that target other muscle groups or lighter variations."
        )

    movement_patterns = context.get("movement_patterns", {})
    movement_balance_text = "None"
    boost_note = ""
    if movement_patterns:
        force_type_counts = movement_patterns.get("force_type", {})
        mechanics_counts = movement_patterns.get("mechanics", {})
        pattern_counts = movement_patterns.get("movement_patterns", {})

        balance_lines = []
        if force_type_counts:
            balance_lines.append(f"Force Type Balance: {json.dumps(force_type_counts, indent=2)}")
        if mechanics_counts:
            balance_lines.append(f"Mechanics Balance: {json.dumps(mechanics_counts, indent=2)}")
        if pattern_counts:
            balance_lines.append(f"Movement Patterns: {json.dumps(pattern_counts, indent=2)}")
        if balance_lines:
            movement_balance_text = "\n".join(balance_lines)

        push_count = force_type_counts.get("Push", 0)
        pull_count = force_type_counts.get("Pull", 0)
        compound_count = mechanics_counts.get("Compound", 0)
        isolation_count = mechanics_counts.get("Isolation", 0)

        boost_suggestions = []
        if push_count > pull_count + 1:
            boost_suggestions.append("PULL exercises")
        elif pull_count > push_count + 1:
            boost_suggestions.append("PUSH exercises")
        if compound_count > isolation_count + 1:
            boost_suggestions.append("ISOLATION exercises")
        elif isolation_count > compound_count + 1:
            boost_suggestions.append("COMPOUND exercises")

        if boost_suggestions:
            boost_note = (
                f"\n\nMOVEMENT BALANCE: The current workout has an imbalance. Consider "
                f"boosting: {', '.join(boost_suggestions)} to achieve better balance."
            )

    injury_note = ""
    injury_restrictions = context.get("injury_restrictions", [])
    if injury_restrictions:
        injury_lines = [
            f"  - {restriction['injury_name']} (severity: {restriction['severity']}): "
            f"Avoid {restriction['restriction_type']} = '{restriction['restriction_value']}'"
            for restriction in injury_restrictions
        ]
        injury_note = f"""

User Injuries:
The user has the following active injuries. DO NOT recommend exercises that may aggravate these conditions:
{chr(10).join(injury_lines)}

For any exercise that could aggravate an injury, include it in not_recommended with reason "May aggravate [injury name]".
IMPORTANT: This feature helps avoid potentially problematic exercises but is NOT medical advice. When in doubt, exclude the exercise (safety first)."""

    # `user_history` is rendered with json.dumps, so every value in it must be
    # JSON-serialisable. `last_performed` is serialised to ISO strings at its
    # source for exactly this reason - a raw datetime here raised
    # "Object of type datetime is not JSON serializable" and took down every
    # provider that built a prompt.
    names = context.get("muscle_group_names", {})
    targets = ", ".join(
        f"{names[mg_id]} (id {mg_id})" if mg_id in names else f"id {mg_id}"
        for mg_id in context["muscle_group_ids"]
    ) or "none specified"

    return f"""You are an expert fitness coach helping to recommend exercises for a workout slot.

Context:
- Target muscle groups: {targets}
- Available equipment ids: {context['available_equipment_ids']}

Candidate exercises (id | name | equipment | mechanics).
You MUST choose only from this list, and you MUST use each exercise's exact id
and name as given. Do not invent an exercise, and do not pair a name with a
different id:
{format_candidates(context.get('candidates', []))}
- User workout history: {json.dumps(context['user_history'], indent=2) if context['user_history'] else 'None'}
- Current week's training volume per muscle group:
{weekly_volume_text}
- Current workout's movement pattern balance:
{movement_balance_text}{injury_note}

Task:
Provide up to {limit} exercise recommendations, chosen from the candidate list
above, prioritized based on:
1. Muscle group targeting accuracy
2. Equipment availability match
3. User's past performance and progression opportunities
4. Workout variety (avoid recent exercises for variety)
5. Weekly volume management (deprioritize muscle groups with >20 sets/week to prevent overtraining)
6. Movement pattern balance (balance push/pull and compound/isolation exercises){deprioritize_note}{boost_note}

Also populate not_recommended with exercises you ruled out, using clear reasons:
- Equipment not available: {{equipment_name}}
- Weekly volume exceeded for {{muscle_group}} ({{X}} sets)
- Performed {{X}} days ago - insufficient recovery
- Does not target selected muscle groups
- May aggravate {{injury_name}} (if the exercise matches an injury restriction)

Limit not_recommended to ~10 entries with diverse reason types.

weekly_volume_status reflects the current week's volume for the primary muscle
group(s) the exercise targets: "low" (<10 sets/week), "moderate" (10-20),
"high" (>20).

movement_balance is true when the exercise helps balance the workout - adding a
Pull when Push is overrepresented, or Isolation when Compound is.{JSON_SHAPE_INSTRUCTIONS if include_json_shape else ""}"""
