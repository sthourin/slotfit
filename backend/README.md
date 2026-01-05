# SlotFit Backend API

FastAPI backend for SlotFit workout planning and tracking application.

## Features

- RESTful API with `/api/v1/` versioning
- PostgreSQL database with SQLAlchemy ORM
- Alembic database migrations
- AI-powered exercise recommendations (Claude API)
- Offline-first architecture support (sync deferred to future phase)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database URL and API keys
   ```

3. **Set up database:**
   ```bash
   # Create PostgreSQL database
   createdb slotfit

   # Run migrations
   alembic upgrade head
   ```

4. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

   API will be available at `http://localhost:8000`
   API docs at `http://localhost:8000/docs`

## Project Structure

```
backend/
├── app/
│   ├── api/           # API routes
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   │   ├── ai/        # AI provider abstractions
│   │   └── sync/      # Sync logic (future)
│   └── core/          # Config, auth, etc.
├── alembic/           # Migrations
└── tests/             # Tests
```

## API Endpoints

All endpoints are prefixed with `/api/v1/`:

- `/exercises` - Exercise CRUD
- `/routines` - Routine template CRUD
- `/workouts` - Workout session endpoints
- `/recommendations` - AI exercise recommendations
- `/heart-rate` - Heart rate data endpoints

## Development

- **API Versioning**: URL-based (`/api/v1/`)
- **Database**: PostgreSQL with async SQLAlchemy
- **Migrations**: Alembic
- **AI Provider**: Claude API (swappable to Ollama)
