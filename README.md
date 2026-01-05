# SlotFit - Workout Planning and Tracking App

SlotFit is a novel workout app that uses flexible slot-based routines instead of prescriptive exercise lists. Users define routine types (anterior, posterior, full body) and workout styles (5x5, HIIT), then select exercises on-the-fly during workouts based on available equipment.

## 🎯 Development Strategy: Web-First

We're building a **fully-featured web application first** to refine functionality and UI/UX before investing in Android native development.

### Why Web-First?
- **Rapid Iteration**: Faster development cycles, instant updates
- **UI/UX Refinement**: Test and refine user flows before native build
- **Feature Validation**: Validate slot-based approach with real usage
- **Lower Risk**: Identify design issues when changes are cheap

### Web App Includes
- ✅ Full workout execution (start, track, complete workouts)
- ✅ All slot-based features (navigation, reordering, supersets)
- ✅ AI exercise recommendations
- ✅ Complete analytics and history
- ✅ Equipment profiles and filtering
- ✅ Intelligent slot features (warmup, finisher, wildcard slots)

### Deferred to Android
- ❌ Bluetooth heart rate monitoring (Polar H10)
- ❌ True offline-first with background sync
- ❌ Push notifications

## ✨ Key Features

### Slot-Based Routines
- Flexible workout structure with muscle group scoped slots
- **Slot Types**: Standard, Warmup, Finisher, Active Recovery, Wildcard
- Superset linking with pre-defined templates
- Time-constrained slots for HIIT/circuit workouts

### Smart Workout Features
- **Equipment Profiles**: Save equipment by location (Home Gym, Work Gym, etc.)
- **Quick-Fill Mode**: Auto-populate all slots with AI recommendations
- **"Last Workout" Template**: One-tap to repeat previous session
- **Progressive Overload Suggestions**: Automatic weight/rep progression

### AI Exercise Recommendations
- Prioritized suggestions based on workout history
- Movement pattern balance (push/pull, compound/isolation)
- Periodization awareness (weekly volume tracking)
- "Why Not" explanations for deprioritized exercises

### Comprehensive Analytics
- Slot-level performance metrics
- Personal records tracking (by exercise variant)
- Weekly volume by muscle group
- Exercise progression curves

## 📁 Project Structure

```
slotfit/
├── backend/          # FastAPI backend (Python)
├── web/              # React + TypeScript web interface
├── android/          # Native Android app (Kotlin) - Future
└── assets/           # Exercise database CSV
```

## 🚀 Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

### Web Interface

```bash
cd web
npm install
npm run dev
```

App available at `http://localhost:3000`

## 📚 Documentation

- [Main Plan](./.cursor/plans/slotfit_plan.md) - Complete project plan with web-first strategy
- [Plan Analysis](./.cursor/plans/slotfit_plan_analysis.md) - Resolved issues and new feature specifications

## 🛠 Technology Stack

- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, Alembic
- **Web**: React, TypeScript, Vite, Zustand, Tailwind CSS
- **Android** (Future): Kotlin, Room, Android BLE APIs
- **AI**: Claude API (swappable to Ollama)

## 📋 Current Phase

**Phase 3-4: Web App Development**

Focus areas:
1. Enhanced routine designer with slot types
2. Equipment profile management
3. Active workout interface with slot navigation
4. Quick-Fill and smart auto-population
5. Analytics dashboard

## 🗺 Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Backend Foundation | ✅ Complete |
| 2 | AI Integration | 🔄 In Progress |
| 3 | Web - Routine Designer | 📋 Planned |
| 4 | Web - Workout Execution | 📋 Planned |
| 5 | Web - Analytics & History | 📋 Planned |
| 6 | Web - Polish & Refinement | 📋 Planned |
| 7 | Android App | 📋 Future |

## 📊 Exercise Database

- **3,244 exercises** with comprehensive metadata
- 4-level muscle group hierarchy
- Equipment requirements
- Movement patterns, planes of motion
- YouTube demonstration links
- Difficulty levels

## License

[To be determined]
