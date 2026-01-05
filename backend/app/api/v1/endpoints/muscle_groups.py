"""
Muscle Group API endpoints
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import MuscleGroup
from app.schemas.muscle_group import MuscleGroupBase, MuscleGroupListResponse
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/", response_model=MuscleGroupListResponse)
async def list_muscle_groups(
    db: AsyncSession = Depends(get_db),
):
    """List all muscle groups"""
    query = select(MuscleGroup).order_by(MuscleGroup.level, MuscleGroup.name)
    
    result = await db.execute(query)
    muscle_groups = result.scalars().all()
    
    return MuscleGroupListResponse(
        muscle_groups=[MuscleGroupBase.model_validate(mg) for mg in muscle_groups]
    )
