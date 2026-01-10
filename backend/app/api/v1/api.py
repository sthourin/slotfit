"""
API v1 router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import exercises, recommendations, routines, muscle_groups, equipment, equipment_profiles, slot_templates, personal_records, analytics, workouts, injuries, users

api_router = APIRouter()

# Include route modules
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(routines.router, prefix="/routines", tags=["routines"])
api_router.include_router(muscle_groups.router, prefix="/muscle-groups", tags=["muscle-groups"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(equipment_profiles.router, prefix="/equipment-profiles", tags=["equipment-profiles"])
api_router.include_router(slot_templates.router, prefix="/slot-templates", tags=["slot-templates"])
api_router.include_router(personal_records.router, prefix="/personal-records", tags=["personal-records"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(injuries.router, prefix="", tags=["injuries"])
api_router.include_router(users.router, prefix="/users", tags=["users"])