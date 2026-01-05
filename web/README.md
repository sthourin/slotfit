# SlotFit Web Interface

React + TypeScript web interface for designing workout routines.

## Features

- **Routine Designer**: Create and edit slot-based workout routines
- **Exercise Browser**: Browse and search the exercise database
- **Muscle Group Selection**: Hierarchical muscle group selector
- **Superset Support**: Tag-based superset grouping
- **Equipment Filtering**: Filter exercises by available equipment

## Setup

1. **Install dependencies:**
   ```bash
   cd web
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

   App will be available at `http://localhost:3000`

3. **Make sure backend is running:**
   - Backend should be running at `http://localhost:8000`
   - API endpoints available at `http://localhost:8000/api/v1/`

## Project Structure

```
web/
├── src/
│   ├── components/        # React components
│   │   ├── RoutineHeader.tsx
│   │   ├── SlotList.tsx
│   │   ├── SlotEditor.tsx
│   │   └── MuscleGroupSelector.tsx
│   ├── pages/            # Page components
│   │   ├── RoutineDesigner.tsx
│   │   └── ExerciseBrowser.tsx
│   ├── services/         # API clients
│   │   └── api.ts
│   ├── stores/           # State management (Zustand)
│   │   └── routineStore.ts
│   ├── App.tsx
│   └── main.tsx
└── public/
```

## Development

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Routing**: React Router
- **API Client**: Axios (connects to backend at `/api/v1/`)

## Current Status

✅ Routine Designer UI
✅ Exercise Browser
✅ Muscle Group Selector
✅ Slot Management
✅ Superset Tagging

🚧 TODO:
- Save/load routines to backend
- Routine preview
- Export routines
- Drag-and-drop slot reordering
