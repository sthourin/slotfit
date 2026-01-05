# Backend Testing Guide

## Quick Start Testing

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Set Up Database

#### Option A: Using Docker (Easiest)

```bash
# Start PostgreSQL in Docker
docker run --name slotfit-db -e POSTGRES_PASSWORD=slotfit -e POSTGRES_DB=slotfit -p 5432:5432 -d postgres:15

# Wait a few seconds for database to start
```

#### Option B: Local PostgreSQL

```bash
# Create database
createdb slotfit

# Or using psql
psql -U postgres
CREATE DATABASE slotfit;
\q
```

### Step 3: Configure Environment

Create `.env` file in `backend/` directory:

```bash
# Copy example
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:slotfit@localhost:5432/slotfit
AI_PROVIDER=claude
ANTHROPIC_API_KEY=your_key_here  # Optional for testing
API_V1_PREFIX=/api/v1
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Note:** For Docker PostgreSQL, use:
- Username: `postgres`
- Password: `slotfit` (or whatever you set)
- Database: `slotfit`

### Step 4: Create Database Tables

#### Option A: Using Alembic (Recommended)

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

#### Option B: Direct Table Creation (Quick Test)

```bash
python -m app.core.init_db
```

### Step 5: Import Exercise Database

```bash
python scripts/import_exercises.py
```

This will:
- Create muscle groups
- Create equipment entries
- Import ~3,244 exercises
- Takes 1-2 minutes

### Step 6: Start the Server

```bash
uvicorn app.main:app --reload
```

Server will start at `http://localhost:8000`

## Testing Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 2. API Root

```bash
curl http://localhost:8000/
```

### 3. API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. List Exercises

```bash
# Get first 10 exercises
curl "http://localhost:8000/api/v1/exercises/?skip=0&limit=10"

# Search exercises
curl "http://localhost:8000/api/v1/exercises/?search=push"

# Filter by difficulty
curl "http://localhost:8000/api/v1/exercises/?difficulty=Beginner&limit=5"
```

### 5. Get Single Exercise

```bash
# Get exercise by ID (use an ID from the list endpoint)
curl "http://localhost:8000/api/v1/exercises/1"
```

### 6. Get Recommendations

```bash
# Get recommendations for muscle groups [1, 2] with equipment [1, 2]
# Note: You'll need to find actual muscle_group_ids and equipment_ids from the database
curl "http://localhost:8000/api/v1/recommendations/?muscle_group_ids=1&muscle_group_ids=2&available_equipment_ids=1&available_equipment_ids=2&limit=5"
```

## Using Python Requests

Create `test_backend.py`:

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# List exercises
response = requests.get(f"{BASE_URL}/exercises/", params={"limit": 5})
print("Exercises:", response.json())

# Get single exercise
response = requests.get(f"{BASE_URL}/exercises/1")
print("Exercise 1:", response.json())

# Get recommendations
response = requests.get(
    f"{BASE_URL}/recommendations/",
    params={
        "muscle_group_ids": [1, 2],
        "available_equipment_ids": [1],
        "limit": 5
    }
)
print("Recommendations:", response.json())
```

## Troubleshooting

### Database Connection Error

- Verify PostgreSQL is running: `docker ps` or `pg_isready`
- Check `DATABASE_URL` in `.env`
- Ensure database exists: `psql -l | grep slotfit`

### Import Script Errors

- Verify CSV file exists: `assets/slotfit_exercise_database_with_urls.csv`
- Check database connection
- Ensure tables are created (run migrations first)

### Port Already in Use

- Change port: `uvicorn app.main:app --reload --port 8001`
- Or kill existing process on port 8000

### Module Not Found

- Ensure you're in the `backend/` directory
- Activate virtual environment if using one
- Reinstall dependencies: `pip install -r requirements.txt`

## Next Steps

Once backend is working:
1. Test all endpoints via Swagger UI
2. Verify exercise import completed successfully
3. Test recommendations endpoint
4. Move on to Android/Web development
