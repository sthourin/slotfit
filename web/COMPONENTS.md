# Web Interface Components

## Pages

### RoutineDesigner (`/`)
Main page for creating and editing workout routines.

**Features:**
- Create new routines
- Edit routine metadata (name, type, style, description)
- Add/edit slots
- Select muscle groups for each slot
- Set superset tags
- Visual slot list with selection

### ExerciseBrowser (`/exercises`)
Browse and search the exercise database.

**Features:**
- Search exercises by name
- Filter by equipment (multi-select)
- Paginated exercise list
- Exercise details (difficulty, equipment, muscle groups, demo links)

## Components

### RoutineHeader
- Displays and edits routine metadata
- Fields: name, routine type, workout style, description

### SlotList
- Lists all slots in the routine
- Shows slot order, muscle group count, superset tags
- Add/remove slots
- Select slot to edit

### SlotEditor
- Edit slot muscle group scope
- Set superset tag
- Preview slot configuration

### MuscleGroupSelector
- Hierarchical muscle group selection
- Organized by level (Target → Prime → Secondary → Tertiary)
- Expandable/collapsible levels
- Multi-select with checkboxes

## State Management

### RoutineStore (Zustand)
Manages routine state:
- `currentRoutine`: Current routine being edited
- `addSlot`: Add new slot
- `updateSlot`: Update slot properties
- `removeSlot`: Delete slot
- `reorderSlots`: Reorder slots (for drag-and-drop)
- `setSlotSupersetTag`: Set superset grouping tag

## API Integration

### Exercise API
- `list()`: List exercises with filtering
- `get(id)`: Get single exercise

### Muscle Group API
- `list()`: Get all muscle groups (extracted from exercises for now)

### Equipment API
- `list()`: Get all equipment (extracted from exercises for now)

## Next Steps

1. **Backend Integration:**
   - Create routine template API endpoints
   - Save/load routines
   - Muscle group and equipment endpoints

2. **UI Enhancements:**
   - Drag-and-drop slot reordering
   - Routine preview
   - Export routine as JSON
   - Better error handling

3. **Testing:**
   - Test all components
   - Verify API integration
   - Test routine creation flow
