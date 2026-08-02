"""Anchor and partner suggestion endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.suggestion import AnchorSuggestionsResponse, PartnerSuggestionsResponse
from app.services.suggestion_service import anchor_suggestions, partner_suggestions

router = APIRouter()


@router.get("/anchors", response_model=AnchorSuggestionsResponse)
async def get_anchor_suggestions(
    session_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Staples grouped by the session's uncovered pattern goals.

    Raises 404 if the session does not exist or belongs to another user -
    `_session_context`'s `scalar_one()` raises `NoResultFound` for both
    cases, which is what enforces cross-user isolation here.
    """
    try:
        return await anchor_suggestions(db, user.id, session_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/partners", response_model=PartnerSuggestionsResponse)
async def get_partner_suggestions(
    session_id: int = Query(...),
    anchor_exercise_id: int = Query(...),
    position: int = Query(..., ge=2, le=3),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Antagonist partners (position 2) or neutral/uncovered third entries (position 3).

    Raises 404 if the session does not exist or belongs to another user (see
    `get_anchor_suggestions`), or if the anchor exercise has no movement
    pattern mapping.
    """
    try:
        return await partner_suggestions(
            db, user.id, session_id, anchor_exercise_id, position
        )
    except NoResultFound:
        raise HTTPException(
            status_code=404, detail="Session or exercise mapping not found"
        )
