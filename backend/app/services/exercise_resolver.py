"""
Exercise name resolution service.
Resolves free-form exercise names (e.g. from AI suggestions) to Exercise records
using a multi-step matching chain with fuzzy fallback.
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from rapidfuzz import fuzz, process

from app.core.logging import get_logger
from app.models import Exercise

logger = get_logger(__name__)


class ExerciseResolver:
    """
    Resolves free-form exercise names to database Exercise records.

    Matching chain:
      A. Exact match (case-insensitive)
      B. Starts-with, then contains (substring match)
      C. Multi-keyword AND match
      D. Single keyword fallback (longest keyword first)
      E. Fuzzy match using rapidfuzz token_sort_ratio
    """

    STOP_WORDS = {"or", "and", "the", "with", "for"}
    FUZZY_THRESHOLD = 70

    def __init__(self, db: AsyncSession):
        self.db = db
        self._exercise_cache: Optional[dict[str, Exercise]] = None

    async def _load_exercise_cache(self) -> dict[str, Exercise]:
        """Load all exercise names into memory for fuzzy matching."""
        if self._exercise_cache is not None:
            return self._exercise_cache

        result = await self.db.execute(select(Exercise))
        exercises = result.scalars().all()
        self._exercise_cache = {ex.name: ex for ex in exercises}
        return self._exercise_cache

    async def resolve(self, name: str) -> Optional[Exercise]:
        """Resolve a single exercise name through the full matching chain."""
        # Step A: Exact match (case-insensitive)
        exercise = await self._exact_match(name)
        if exercise:
            logger.info(f"Resolved '{name}' -> '{exercise.name}' (exact)")
            return exercise

        # Step B: Substring match (starts-with preferred, then contains)
        exercise = await self._substring_match(name)
        if exercise:
            logger.info(f"Resolved '{name}' -> '{exercise.name}' (substring)")
            return exercise

        # Step C: Multi-keyword AND
        exercise = await self._multi_keyword_match(name)
        if exercise:
            logger.info(f"Resolved '{name}' -> '{exercise.name}' (multi-keyword)")
            return exercise

        # Step D: Fuzzy match (before single-keyword — smarter matching)
        exercise, score = await self._fuzzy_match(name)
        if exercise:
            logger.info(f"Resolved '{name}' -> '{exercise.name}' (fuzzy, score={score:.0f})")
            return exercise

        # Step E: Single keyword fallback (last resort)
        exercise = await self._single_keyword_match(name)
        if exercise:
            logger.info(f"Resolved '{name}' -> '{exercise.name}' (single-keyword)")
            return exercise

        logger.warning(f"Could not resolve exercise name: '{name}'")
        return None

    async def resolve_many(self, names: List[str]) -> List[Exercise]:
        """Resolve multiple exercise names. Pre-loads cache once for efficiency."""
        await self._load_exercise_cache()

        resolved: list[Exercise] = []
        for name in names:
            exercise = await self.resolve(name)
            if exercise:
                resolved.append(exercise)

        logger.info(f"Resolved {len(resolved)}/{len(names)} exercises")
        return resolved

    # --- Matching steps ---

    async def _exact_match(self, name: str) -> Optional[Exercise]:
        q = select(Exercise).where(func.lower(Exercise.name) == name.lower()).limit(1)
        return (await self.db.execute(q)).scalar_one_or_none()

    async def _substring_match(self, name: str) -> Optional[Exercise]:
        # Prefer starts-with (more specific)
        q = (
            select(Exercise)
            .where(Exercise.name.ilike(f"{name}%"))
            .order_by(func.length(Exercise.name))
            .limit(1)
        )
        exercise = (await self.db.execute(q)).scalar_one_or_none()
        if exercise:
            return exercise

        # Fall back to contains
        q = (
            select(Exercise)
            .where(Exercise.name.ilike(f"%{name}%"))
            .order_by(func.length(Exercise.name))
            .limit(1)
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def _multi_keyword_match(self, name: str) -> Optional[Exercise]:
        keywords = self._extract_keywords(name)
        if len(keywords) < 2:
            return None

        q = select(Exercise)
        for kw in keywords:
            q = q.where(Exercise.name.ilike(f"%{kw}%"))
        q = q.order_by(func.length(Exercise.name)).limit(1)
        return (await self.db.execute(q)).scalar_one_or_none()

    async def _single_keyword_match(self, name: str) -> Optional[Exercise]:
        keywords = self._extract_keywords(name)
        for kw in sorted(keywords, key=len, reverse=True):
            q = (
                select(Exercise)
                .where(Exercise.name.ilike(f"%{kw}%"))
                .order_by(func.length(Exercise.name))
                .limit(1)
            )
            exercise = (await self.db.execute(q)).scalar_one_or_none()
            if exercise:
                return exercise
        return None

    async def _fuzzy_match(
        self, name: str
    ) -> Tuple[Optional[Exercise], float]:
        """
        Fuzzy match using rapidfuzz token_sort_ratio.

        token_sort_ratio splits into tokens, sorts alphabetically, then scores.
        This handles word reordering: "Barbell Deadlift" vs "Deadlift (Barbell)" -> high score.
        """
        cache = await self._load_exercise_cache()
        if not cache:
            return None, 0.0

        exercise_names = list(cache.keys())

        # Strip parentheses for matching so "Deadlift (Barbell)" becomes "Deadlift Barbell"
        def normalize(s: str) -> str:
            return s.replace("(", "").replace(")", "").replace("-", " ").lower().strip()

        result = process.extractOne(
            normalize(name),
            exercise_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=self.FUZZY_THRESHOLD,
            processor=normalize,
        )

        if result is None:
            return None, 0.0

        matched_name, score, _ = result
        return cache[matched_name], score

    @staticmethod
    def _extract_keywords(name: str) -> List[str]:
        return [
            w
            for w in name.replace("-", " ").replace("/", " ").split()
            if len(w) > 2 and w.lower() not in ExerciseResolver.STOP_WORDS
        ]
