# Quick Start - Backend Testing

## Prerequisites Check

1. **Python 3.10+** ✓ (You have 3.13.5)
2. **PostgreSQL** - Need to set up
3. **Virtual Environment** (recommended)

## Step-by-Step Setup

### 1. Create Virtual Environment (Recommended)

```bash
cd backend
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up PostgreSQL Database

#### Option A: Docker (Easiest)

```bash
# Install Docker Desktop if not installed
# Then run:
docker run --name slotfit-db -e POSTGRES_PASSWORD=slotfit -e POSTGRES_DB=slotfit -p 5432:5432 -d postgres:15
```

#### Option B: Local PostgreSQL

1. Install PostgreSQL from https://www.postgresql.org/download/
2. Create database:
   ```bash
   createdb slotfit
   ```

### 4. Create .env File

Create `backend/.env` file:

```env
DATABASE_URL=postgresql+asyncpg://postgres:slotfit@localhost:5432/slotfit
AI_PROVIDER=claude
ANTHROPIC_API_KEY=
API_V1_PREFIX=/api/v1
DEBUG=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

**For Docker PostgreSQL:**
- Username: `postgres`
- Password: `slotfit`
- Host: `localhost`
- Port: `5432`
- Database: `slotfit`

**For Local PostgreSQL:**
- Adjust username/password as needed

### 5. Create Database Tables

```bash
# Option A: Using init script (quick)
python -m app.core.init_db

# Option B: Using Alembic (proper way)
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 6. Import Exercise Database

```bash
python scripts/import_exercises.py
```

This will take 1-2 minutes to import ~3,244 exercises.

### 7. Start the Server

```bash
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 8. Test the API

#### Option A: Using Browser

1. Open http://localhost:8000/docs
2. Try the endpoints interactively

#### Option B: Using Test Script

```bash
# In another terminal
pip install requests
python test_backend.py
```

#### Option C: Using curl

```bash
# Health check
curl http://localhost:8000/health

# List exercises
curl "http://localhost:8000/api/v1/exercises/?limit=5"
```

## Common Issues

### "Module not found"
- Make sure you're in the `backend/` directory
- Activate virtual environment
- Run `pip install -r requirements.txt`

### "Connection refused" or database errors
- Check PostgreSQL is running: `docker ps` or `pg_isready`
- Verify `DATABASE_URL` in `.env`
- Ensure database exists

### Port 8000 already in use
```bash
uvicorn app.main:app --reload --port 8001
```

## Next Steps

Once everything works:
1. Explore API docs at http://localhost:8000/docs
2. Test all endpoints
3. Verify exercise data imported correctly
4. Test recommendations endpoint
