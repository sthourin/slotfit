"""Training session lifecycle endpoints"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    TrainingSession,
    SupersetRound,
    RoundEntry,
    EntrySet,
    SessionState,
    ExercisePatternMap,
    MovementPattern,
    PatternGoal,
    User,
)
from app.schemas.training_session import (
    TrainingSessionCreate,
    TrainingSessionResponse,
    SupersetRoundResponse,
    RoundEntryCreate,
    RoundEntryResponse,
    EntrySetCreate,
    EntrySetResponse,
    TargetResponse,
    CoverageResponse,
    CoverageGoal,
)
from app.services.progression_service import compute_entry_target

router = APIRouter()

_SESSION_LOAD = (
    selectinload(TrainingSession.rounds)
    .selectinload(SupersetRound.entries)
    .selectinload(RoundEntry.sets),
    selectinload(TrainingSession.rounds)
    .selectinload(SupersetRound.entries)
    .selectinload(RoundEntry.exercise),
    selectinload(TrainingSession.rounds)
    .selectinload(SupersetRound.entries)
    .selectinload(RoundEntry.pattern),
)


async def _load_session(
    db: AsyncSession, user: User, session_id: int
) -> TrainingSession:
    """Fetch a training session by id, scoped to the current user, fully eager-loaded.

    Raises 404 if the session does not exist or belongs to another user.
    """
    result = await db.execute(
        select(TrainingSession)
        .where(TrainingSession.id == session_id, TrainingSession.user_id == user.id)
        .options(*_SESSION_LOAD)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _rep_range_for(
    db: AsyncSession, session: TrainingSession, pattern_id: int
) -> tuple[int, int]:
    """Resolve the rep range to target for a pattern, from the session's day plan goal if set.

    Falls back to the service defaults (8-12) when there is no day plan or no
    goal for this pattern.
    """
    if session.day_plan_id:
        goal = (
            await db.execute(
                select(PatternGoal).where(
                    PatternGoal.day_plan_id == session.day_plan_id,
                    PatternGoal.pattern_id == pattern_id,
                )
            )
        ).scalar_one_or_none()
        if goal:
            return (goal.rep_range_min or 8, goal.rep_range_max or 12)
    return (8, 12)


async def _entry_response(
    db: AsyncSession, user: User, session: TrainingSession, entry: RoundEntry
) -> RoundEntryResponse:
    """Build the API response for a round entry, including its computed progression target.

    RoundEntryResponse carries exercise_name, pattern_slug, and target, none of
    which are attributes on the RoundEntry model, so they must be hand-built
    here rather than via model_validate.
    """
    rep_min, rep_max = await _rep_range_for(db, session, entry.pattern_id)
    target = await compute_entry_target(
        db, user.id, entry.exercise_id, rep_min, rep_max
    )
    return RoundEntryResponse(
        id=entry.id,
        round_id=entry.round_id,
        position=entry.position,
        exercise_id=entry.exercise_id,
        exercise_name=entry.exercise.name,
        pattern_id=entry.pattern_id,
        pattern_slug=entry.pattern.slug,
        sets=[EntrySetResponse.model_validate(s) for s in entry.sets],
        target=TargetResponse(**target) if target else None,
    )


async def _session_response(
    db: AsyncSession, user: User, session: TrainingSession
) -> TrainingSessionResponse:
    """Build the full nested API response for a training session (rounds -> entries -> sets)."""
    rounds = []
    for rnd in session.rounds:
        entries = [await _entry_response(db, user, session, e) for e in rnd.entries]
        rounds.append(
            SupersetRoundResponse(
                id=rnd.id,
                session_id=rnd.session_id,
                order=rnd.order,
                entries=entries,
            )
        )
    return TrainingSessionResponse(
        id=session.id,
        day_plan_id=session.day_plan_id,
        state=session.state.value,
        started_at=session.started_at,
        completed_at=session.completed_at,
        notes=session.notes,
        rounds=rounds,
    )


@router.post("/", response_model=TrainingSessionResponse, status_code=201)
async def create_session(
    data: TrainingSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a new training session for the current user.

    Returns 409 if the user already has a draft or active session in
    progress, since only one workout may be live at a time.
    """
    existing = (
        (
            await db.execute(
                select(TrainingSession).where(
                    TrainingSession.user_id == user.id,
                    TrainingSession.state.in_(
                        [SessionState.DRAFT, SessionState.ACTIVE]
                    ),
                )
            )
        )
        .scalars()
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Session {existing.id} is already in progress"
        )

    session = TrainingSession(
        user_id=user.id,
        day_plan_id=data.day_plan_id,
        state=SessionState.ACTIVE,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    return await _session_response(db, user, await _load_session(db, user, session.id))


@router.get("/active", response_model=TrainingSessionResponse)
async def get_active_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the current user's in-progress (draft or active) session, or 404 if none.

    Declared before GET /{session_id} so "active" is never captured by the
    int path parameter.
    """
    result = await db.execute(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user.id,
            TrainingSession.state.in_([SessionState.DRAFT, SessionState.ACTIVE]),
        )
        .options(*_SESSION_LOAD)
    )
    session = result.scalars().first()
    if session is None:
        raise HTTPException(status_code=404, detail="No active session")
    return await _session_response(db, user, session)


@router.get("/", response_model=List[TrainingSessionResponse])
async def list_sessions(
    state: Optional[SessionState] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the current user's training sessions (history), optionally filtered by state."""
    query = (
        select(TrainingSession)
        .where(TrainingSession.user_id == user.id)
        .options(*_SESSION_LOAD)
        .order_by(TrainingSession.started_at.desc())
        .limit(limit)
    )
    if state:
        query = query.where(TrainingSession.state == state)
    result = await db.execute(query)
    return [await _session_response(db, user, s) for s in result.scalars().all()]


@router.get("/{session_id}", response_model=TrainingSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve a single training session, fully nested, if owned by the current user."""
    return await _session_response(db, user, await _load_session(db, user, session_id))


@router.post(
    "/{session_id}/rounds", response_model=SupersetRoundResponse, status_code=201
)
async def create_round(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Append a new superset round to the session, with order auto-incremented."""
    session = await _load_session(db, user, session_id)
    next_order = max((r.order for r in session.rounds), default=0) + 1
    rnd = SupersetRound(session_id=session.id, order=next_order)
    db.add(rnd)
    await db.commit()
    return SupersetRoundResponse(
        id=rnd.id, session_id=rnd.session_id, order=rnd.order, entries=[]
    )


@router.post(
    "/rounds/{round_id}/entries", response_model=RoundEntryResponse, status_code=201
)
async def create_entry(
    round_id: int,
    data: RoundEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add an entry (exercise) to a round at the given position.

    The pattern_id is resolved server-side from ExercisePatternMap and
    denormalized onto the entry so later edits to the mapping don't rewrite
    history. Returns 404 if the round isn't owned by the user or the
    exercise has no pattern mapping, 409 if the position is already filled.
    """
    rnd = (
        await db.execute(
            select(SupersetRound)
            .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
            .where(SupersetRound.id == round_id, TrainingSession.user_id == user.id)
            .options(selectinload(SupersetRound.entries))
        )
    ).scalar_one_or_none()
    if rnd is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if any(e.position == data.position for e in rnd.entries):
        raise HTTPException(
            status_code=409, detail=f"Position {data.position} already filled"
        )

    mapping = (
        await db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == data.exercise_id
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Exercise has no pattern mapping")

    entry = RoundEntry(
        round_id=rnd.id,
        position=data.position,
        exercise_id=data.exercise_id,
        pattern_id=mapping.pattern_id,
    )
    db.add(entry)
    await db.commit()

    entry = (
        await db.execute(
            select(RoundEntry)
            .where(RoundEntry.id == entry.id)
            .options(
                selectinload(RoundEntry.exercise),
                selectinload(RoundEntry.pattern),
                selectinload(RoundEntry.sets),
            )
        )
    ).scalar_one()
    session = await _load_session(db, user, rnd.session_id)
    return await _entry_response(db, user, session, entry)


@router.post(
    "/entries/{entry_id}/sets", response_model=EntrySetResponse, status_code=201
)
async def create_set(
    entry_id: int,
    data: EntrySetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Log a set against a round entry, scoped to the current user's own session."""
    entry = (
        await db.execute(
            select(RoundEntry)
            .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
            .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
            .where(RoundEntry.id == entry_id, TrainingSession.user_id == user.id)
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry_set = EntrySet(entry_id=entry.id, **data.model_dump())
    db.add(entry_set)
    await db.commit()
    return EntrySetResponse.model_validate(entry_set)


@router.post("/{session_id}/complete", response_model=TrainingSessionResponse)
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a session completed, stamping completed_at now."""
    session = await _load_session(db, user, session_id)
    session.state = SessionState.COMPLETED
    session.completed_at = datetime.utcnow()
    await db.commit()
    return await _session_response(db, user, await _load_session(db, user, session_id))


@router.post("/{session_id}/discard", response_model=TrainingSessionResponse)
async def discard_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a session discarded (abandoned workout)."""
    session = await _load_session(db, user, session_id)
    session.state = SessionState.DISCARDED
    await db.commit()
    return await _session_response(db, user, await _load_session(db, user, session_id))


@router.get("/{session_id}/coverage", response_model=CoverageResponse)
async def get_coverage(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Report pattern coverage for a session against its day plan's goals.

    For each goal, reports target_sets (default 3 when unset), sets_done
    (counting only completed sets logged against entries with that pattern),
    and whether the goal is covered. Sessions without a day plan yield an
    empty goals list.
    """
    session = await _load_session(db, user, session_id)
    goals: list[PatternGoal] = []
    if session.day_plan_id:
        goals = (
            (
                await db.execute(
                    select(PatternGoal)
                    .where(PatternGoal.day_plan_id == session.day_plan_id)
                    .options(selectinload(PatternGoal.pattern))
                )
            )
            .scalars()
            .all()
        )

    sets_by_pattern: dict[int, int] = {}
    for rnd in session.rounds:
        for entry in rnd.entries:
            done = sum(1 for s in entry.sets if s.completed)
            sets_by_pattern[entry.pattern_id] = (
                sets_by_pattern.get(entry.pattern_id, 0) + done
            )

    coverage_goals = []
    for goal in goals:
        target = goal.target_sets or 3
        done = sets_by_pattern.get(goal.pattern_id, 0)
        coverage_goals.append(
            CoverageGoal(
                pattern_id=goal.pattern_id,
                slug=goal.pattern.slug,
                name=goal.pattern.name,
                required=goal.required,
                target_sets=target,
                sets_done=done,
                covered=done >= target,
            )
        )
    return CoverageResponse(goals=coverage_goals)
