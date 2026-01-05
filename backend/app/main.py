"""
SlotFit FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.models.base import Base
from app.api.v1.api import api_router

app = FastAPI(
    title="SlotFit API",
    description="Workout planning and tracking API with AI exercise recommendations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for web interface
# Allow Swagger UI to work by allowing the server's own origin
cors_origins = settings.cors_origins_list.copy()
cors_origins.extend([
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "SlotFit API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
