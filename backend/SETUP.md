# SlotFit Backend Setup Guide

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Virtual environment (recommended)

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` with your database URL and API keys:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/slotfit
ANTHROPIC_API_KEY=your_claude_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

**AI Provider Priority:**
1. Claude API (if `ANTHROPIC_API_KEY` is set and `AI_PROVIDER=claude`)
2. Gemini API (if `GEMINI_API_KEY` is set, used as fallback)
3. Rule-based fallback (database queries, always available)

To get a Gemini API key:
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

### 3. Create Database

```bash
# Using psql
createdb slotfit

# Or using SQL
psql -U postgres
CREATE DATABASE slotfit;
```

### 4. Run Database Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

**Alternative:** For development, you can create tables directly:

```bash
python -m app.core.init_db
```

### 5. Import Exercise Database

Import the exercise database from CSV:

```bash
python scripts/import_exercises.py
```

This will:
- Create muscle groups (hierarchical structure)
- Create equipment entries
- Import all exercises from `assets/slotfit_exercise_database_with_urls.csv`

### 6. Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

All endpoints are prefixed with `/api/v1/`:

### Exercises

- `GET /api/v1/exercises/` - List exercises (with filtering)
  - Query params: `skip`, `limit`, `search`, `muscle_group_id`, `equipment_id`, `difficulty`
- `GET /api/v1/exercises/{exercise_id}` - Get single exercise

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/           # API routes
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   ├── core/          # Configuration, database
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   └── services/      # Business logic
├── alembic/           # Migrations
├── scripts/           # Utility scripts
└── tests/             # Tests
```

### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Running Tests

```bash
pytest
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Ensure database exists

### Import Script Issues

- Verify CSV file path: `assets/slotfit_exercise_database_with_urls.csv`
- Check database connection
- Ensure migrations have been run

### API Not Starting

- Check all dependencies are installed
- Verify `.env` file exists
- Check for port conflicts (default: 8000)
