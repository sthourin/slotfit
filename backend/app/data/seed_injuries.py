"""
Seed data for injury types and movement restrictions.
Run with: python -m app.data.seed_injuries
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.injury import InjuryType, MovementRestriction

INJURY_SEED_DATA = [
    {
        "name": "Rotator Cuff Injury",
        "body_area": "Shoulder",
        "description": "Injury to the muscles and tendons stabilizing the shoulder joint",
        "restrictions": [
            {"type": "movement_pattern", "value": "Overhead Press", "severity": "mild"},
            {"type": "movement_pattern", "value": "Lateral Raise", "severity": "mild"},
            {"type": "movement_pattern", "value": "Upright Row", "severity": "mild"},
            {"type": "force_type", "value": "Push", "severity": "severe"},  # Only severe
        ]
    },
    {
        "name": "AC Joint Separation",
        "body_area": "Shoulder",
        "description": "Injury to the acromioclavicular joint at top of shoulder",
        "restrictions": [
            {"type": "movement_pattern", "value": "Horizontal Press", "severity": "mild"},
            {"type": "movement_pattern", "value": "Dip", "severity": "mild"},
            {"type": "movement_pattern", "value": "Fly", "severity": "moderate"},
        ]
    },
    {
        "name": "Tennis Elbow (Lateral Epicondylitis)",
        "body_area": "Elbow",
        "description": "Pain on the outside of the elbow from overuse",
        "restrictions": [
            {"type": "movement_pattern", "value": "Wrist Extension", "severity": "mild"},
            {"type": "movement_pattern", "value": "Reverse Curl", "severity": "mild"},
            {"type": "movement_pattern", "value": "Pull", "severity": "severe"},
        ]
    },
    {
        "name": "Golfer's Elbow (Medial Epicondylitis)",
        "body_area": "Elbow",
        "description": "Pain on the inside of the elbow from overuse",
        "restrictions": [
            {"type": "movement_pattern", "value": "Wrist Flexion", "severity": "mild"},
            {"type": "movement_pattern", "value": "Curl", "severity": "moderate"},
        ]
    },
    {
        "name": "Lower Back Pain / Herniated Disc",
        "body_area": "Back",
        "description": "Pain in the lumbar region, possibly from disc issues",
        "restrictions": [
            {"type": "movement_pattern", "value": "Deadlift", "severity": "mild"},
            {"type": "movement_pattern", "value": "Good Morning", "severity": "mild"},
            {"type": "movement_pattern", "value": "Bent Over Row", "severity": "moderate"},
            {"type": "posture", "value": "Bent Over", "severity": "mild"},
            {"type": "plane_of_motion", "value": "Spinal Flexion", "severity": "mild"},
        ]
    },
    {
        "name": "Knee Pain (General)",
        "body_area": "Knee",
        "description": "General knee discomfort or mild injury",
        "restrictions": [
            {"type": "movement_pattern", "value": "Deep Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Lunge", "severity": "moderate"},
            {"type": "movement_pattern", "value": "Leg Extension", "severity": "moderate"},
        ]
    },
    {
        "name": "ACL Injury / Recovery",
        "body_area": "Knee",
        "description": "Anterior cruciate ligament injury or post-surgery recovery",
        "restrictions": [
            {"type": "movement_pattern", "value": "Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Lunge", "severity": "mild"},
            {"type": "movement_pattern", "value": "Jump", "severity": "mild"},
            {"type": "movement_pattern", "value": "Pivot", "severity": "mild"},
            {"type": "laterality", "value": "Unilateral", "severity": "moderate"},
        ]
    },
    {
        "name": "Patellar Tendinitis (Jumper's Knee)",
        "body_area": "Knee",
        "description": "Inflammation of the patellar tendon",
        "restrictions": [
            {"type": "movement_pattern", "value": "Jump", "severity": "mild"},
            {"type": "movement_pattern", "value": "Deep Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Leg Extension", "severity": "mild"},
        ]
    },
    {
        "name": "Wrist Injury / Sprain",
        "body_area": "Wrist",
        "description": "Wrist pain or sprain affecting grip and wrist stability",
        "restrictions": [
            {"type": "movement_pattern", "value": "Wrist Curl", "severity": "mild"},
            {"type": "posture", "value": "Prone", "severity": "moderate"},  # Pushup position
            {"type": "movement_pattern", "value": "Push Up", "severity": "moderate"},
        ]
    },
    {
        "name": "Neck Pain / Strain",
        "body_area": "Neck",
        "description": "Cervical pain or muscle strain in the neck",
        "restrictions": [
            {"type": "movement_pattern", "value": "Shrug", "severity": "mild"},
            {"type": "movement_pattern", "value": "Overhead Press", "severity": "moderate"},
            {"type": "movement_pattern", "value": "Behind Neck", "severity": "mild"},
        ]
    },
    {
        "name": "Hip Impingement",
        "body_area": "Hip",
        "description": "Femoroacetabular impingement causing hip pain",
        "restrictions": [
            {"type": "movement_pattern", "value": "Deep Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Hip Flexion", "severity": "moderate"},
            {"type": "movement_pattern", "value": "Lunge", "severity": "moderate"},
        ]
    },
    {
        "name": "Ankle Sprain",
        "body_area": "Ankle",
        "description": "Sprained ankle ligaments",
        "restrictions": [
            {"type": "movement_pattern", "value": "Calf Raise", "severity": "mild"},
            {"type": "movement_pattern", "value": "Jump", "severity": "mild"},
            {"type": "laterality", "value": "Unilateral", "severity": "moderate"},
        ]
    },
]

# Body areas for filtering
BODY_AREAS = ["Shoulder", "Elbow", "Back", "Knee", "Wrist", "Neck", "Hip", "Ankle"]


async def seed_injuries():
    """Seed injury types and movement restrictions"""
    async with AsyncSessionLocal() as session:
        # Check if injuries already exist
        result = await session.execute(select(InjuryType))
        existing = result.scalars().all()
        if existing:
            print(f"Found {len(existing)} existing injury types. Skipping seed.")
            return
        
        print("Seeding injury types and movement restrictions...")
        
        for injury_data in INJURY_SEED_DATA:
            # Create injury type
            injury_type = InjuryType(
                name=injury_data["name"],
                body_area=injury_data["body_area"],
                description=injury_data["description"],
                is_system=True,
            )
            session.add(injury_type)
            await session.flush()  # Get the ID
            
            # Create movement restrictions
            for restriction_data in injury_data["restrictions"]:
                # Check if restriction already exists
                restriction_query = select(MovementRestriction).where(
                    MovementRestriction.restriction_type == restriction_data["type"],
                    MovementRestriction.restriction_value == restriction_data["value"]
                )
                result = await session.execute(restriction_query)
                restriction = result.scalar_one_or_none()
                
                if not restriction:
                    restriction = MovementRestriction(
                        restriction_type=restriction_data["type"],
                        restriction_value=restriction_data["value"],
                        severity_threshold=restriction_data["severity"],
                    )
                    session.add(restriction)
                    await session.flush()
                
                # Associate restriction with injury type using the association table directly
                # This avoids lazy loading issues
                from app.models.injury import injury_movement_restrictions
                from sqlalchemy import insert
                
                # Check if association already exists
                check_query = select(injury_movement_restrictions).where(
                    injury_movement_restrictions.c.injury_type_id == injury_type.id,
                    injury_movement_restrictions.c.restriction_id == restriction.id
                )
                result = await session.execute(check_query)
                if not result.first():
                    # Insert association
                    stmt = insert(injury_movement_restrictions).values(
                        injury_type_id=injury_type.id,
                        restriction_id=restriction.id
                    )
                    await session.execute(stmt)
        
        await session.commit()
        print(f"Successfully seeded {len(INJURY_SEED_DATA)} injury types.")


if __name__ == "__main__":
    asyncio.run(seed_injuries())
