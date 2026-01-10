"""
Pydantic schemas for Recommendation API
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Re-export from base for API use
from app.services.ai.base import (
    ExerciseRecommendation,
    NotRecommendedExercise,
    RecommendationResponse,
)

# API-specific schemas (aliases for clarity)
NotRecommendedExerciseResponse = NotRecommendedExercise
RecommendationResponseSchema = RecommendationResponse
