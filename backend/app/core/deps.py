"""
FastAPI dependencies for authentication and database access
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.user import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current user based on device ID header.
    
    For MVP: Uses X-Device-ID header to identify/create users
    For Future: Will validate JWT token and return authenticated user
    
    This abstraction allows swapping auth mechanisms without changing endpoint code.
    """
    
    # MVP Mode: Device-based identification
    device_id = request.headers.get("X-Device-ID")
    
    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="X-Device-ID header is required. Generate a UUID on the client and send it with every request."
        )
    
    # Validate device_id format (should be UUID-like)
    if len(device_id) < 10 or len(device_id) > 50:
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Device-ID format. Should be a UUID."
        )
    
    # Find existing user or create new one
    result = await db.execute(
        select(User).where(User.device_id == device_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user for this device
        user = User(device_id=device_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update last seen timestamp
        user.last_seen_at = datetime.now(timezone.utc)
        await db.commit()
    
    return user


# Optional: Dependency that doesn't require auth (for public endpoints)
async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """
    Get current user if device ID provided, otherwise return None.
    Use for endpoints that work with or without user context.
    """
    device_id = request.headers.get("X-Device-ID")
    
    if not device_id:
        return None
    
    result = await db.execute(
        select(User).where(User.device_id == device_id)
    )
    return result.scalar_one_or_none()
