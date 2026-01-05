# SlotFit Project Structure

## Overview

Complete project structure for SlotFit workout planning and tracking application.

## Directory Structure

```
slotfit/
├── backend/                    # FastAPI Backend
│   ├── alembic/               # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   ├── v1/
│   │   │   │   ├── api.py
│   │   │   │   └── endpoints/
│   │   ├── core/              # Configuration
│   │   │   └── config.py
│   │   ├── models/            # SQLAlchemy models
│   │   │   └── base.py
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   │   ├── ai/            # AI providers
│   │   │   └── sync/          # Sync logic (future)
│   │   └── main.py            # FastAPI app
│   ├── alembic.ini
│   ├── requirements.txt
│   └── README.md
│
├── web/                       # React + TypeScript Web Interface
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── services/          # API clients
│   │   │   └── api.ts
│   │   ├── stores/            # State management (Zustand)
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── README.md
│
├── android/                   # Native Android App
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/slotfit/app/
│   │   │   │   ├── data/      # Room database, repositories
│   │   │   │   ├── ui/        # Activities, fragments, ViewModels
│   │   │   │   ├── bluetooth/ # BLE heart rate monitoring
│   │   │   │   ├── sync/      # Offline sync (future)
│   │   │   │   ├── services/  # Background services
│   │   │   │   └── MainActivity.kt
│   │   │   ├── res/
│   │   │   │   ├── layout/
│   │   │   │   └── values/
│   │   │   └── AndroidManifest.xml
│   │   └── build.gradle
│   ├── build.gradle
│   ├── settings.gradle
│   ├── gradle.properties
│   └── README.md
│
├── assets/                    # Exercise database
│   └── slotfit_exercise_database_with_urls.csv
│
├── .cursor/                   # Planning documents
│   └── plans/
│       ├── slotfit_plan.md
│       └── slotfit_plan_analysis.md
│
├── .gitignore
└── README.md
```

## Configuration Files Created

### Backend
- ✅ `requirements.txt` - Python dependencies
- ✅ `alembic.ini` - Alembic configuration
- ✅ `app/core/config.py` - Application settings
- ✅ `app/main.py` - FastAPI application entry point
- ✅ `app/models/base.py` - SQLAlchemy base model

### Web
- ✅ `package.json` - Node.js dependencies
- ✅ `tsconfig.json` - TypeScript configuration
- ✅ `vite.config.ts` - Vite build configuration
- ✅ `src/services/api.ts` - API client setup

### Android
- ✅ `build.gradle` (project & app level) - Gradle build configuration
- ✅ `settings.gradle` - Project settings
- ✅ `gradle.properties` - Gradle properties
- ✅ `AndroidManifest.xml` - App manifest with BLE permissions
- ✅ Resource files (strings.xml, themes.xml, colors.xml)

## Next Steps

1. **Backend Development:**
   - Create database models (Exercise, RoutineTemplate, WorkoutSession, etc.)
   - Implement API endpoints
   - Set up Alembic migrations
   - Create AI service abstraction

2. **Web Development:**
   - Build routine designer UI
   - Implement exercise browser
   - Create slot management interface

3. **Android Development:**
   - Set up Room database schema
   - Implement BLE heart rate monitoring
   - Build workout interface
   - Create navigation structure

## Notes

- All projects are configured for `/api/v1/` API versioning
- MVP is offline-only (no authentication/sync initially)
- Exercise database CSV is ready for import
- All critical plan issues have been resolved
