# SlotFit Plan Analysis - Web-First Development Strategy

## Development Strategy Change

**Previous Strategy**: Build Android app with web interface for routine design only
**New Strategy**: Web-first development - build fully-featured web app before Android

### Rationale
- Faster iteration cycles for UI/UX refinement
- Validate slot-based approach with real usage
- Lower risk - identify design issues when changes are cheap
- Same backend serves both web and future mobile

### Web App Scope
- ✅ Full workout execution (not just routine design)
- ✅ All slot-based features
- ✅ AI recommendations
- ✅ Analytics and history
- ❌ Bluetooth HR monitoring (Android only)
- ❌ True offline-first (Android only)
- ❌ Push notifications (Android only)

---

## New Features to Implement

### Priority 1: High Impact, Medium Effort

#### 1. Equipment Location Profiles ✅ DESIGNED
- **Status**: Schema and API designed
- **Model**: `equipment_profiles` table
- **Features**:
  - Save equipment configs tied to locations
  - Set default profile for auto-selection
  - Per-slot override capability
- **Implementation**: Phase 3

#### 2. Smart Slot Auto-Population ✅ DESIGNED
- **Status**: Feature designed
- **Features**:
  - Quick-Fill Mode: Auto-select all slots based on equipment + history
  - "Last Workout" Template: Copy from previous session
  - Progressive Overload Suggestions: Slightly higher than last session
- **Implementation**: Phase 4

#### 3. Movement Pattern Balance in AI ✅ DESIGNED
- **Status**: Enhancement to recommendation service
- **Features**:
  - Balance Horizontal Push vs. Pull
  - Balance Sagittal vs. Transverse plane
  - Balance Compound vs. Isolation ratio
- **Data Source**: Existing CSV has movement pattern data
- **Implementation**: Phase 2

### Priority 2: Medium Impact, Low-Medium Effort

#### 4. Slot Types ✅ DESIGNED
- **Status**: Schema designed
- **Types**:
  - `standard`: Regular exercise slot
  - `warmup`: Mobility/activation for subsequent slots
  - `finisher`: High-rep burnout for underworked muscles
  - `active_recovery`: Stretching/foam rolling between heavy sets
  - `wildcard`: No muscle group scope - full database available
- **Implementation**: Phase 3

#### 5. Time-Constrained Slots ✅ DESIGNED
- **Status**: Schema field added
- **Features**:
  - Optional `time_limit_seconds` per slot
  - Visual countdown during workout
  - Auto-suggest moving to next slot when expired
- **Implementation**: Phase 3

#### 6. Slot-Level Analytics ✅ DESIGNED
- **Status**: Schema and service designed
- **Metrics**:
  - Completion rates per slot
  - Average exercises used per slot
  - Frequently skipped slots identification
  - Volume trends per slot
- **Implementation**: Phase 5

#### 7. Personal Records Tracking ✅ DESIGNED
- **Status**: Schema designed
- **Model**: `personal_records` table
- **Features**:
  - PRs by exercise variant (HIIT vs Strength)
  - PR notifications during workout
  - PR history and dates
- **Implementation**: Phase 5

### Priority 3: Medium Impact, Low Effort

#### 8. "Why Not" Explanations ✅ DESIGNED
- **Status**: API response schema updated
- **Features**:
  - Expandable section showing NOT recommended exercises
  - Reasons: recovery, equipment, weekly volume
- **Implementation**: Phase 2

#### 9. Superset Templates ✅ DESIGNED
- **Status**: Schema designed
- **Model**: `superset_templates` table
- **Features**:
  - Pre-defined antagonist pairs (Biceps/Triceps, Chest/Back)
  - User can apply template to auto-link slots
- **Implementation**: Phase 3

#### 10. Reusable Slot Templates ✅ DESIGNED
- **Status**: Schema designed
- **Model**: `slot_templates` table
- **Features**:
  - Create reusable slot configurations
  - Import into multiple routines
  - Standardize slot setups
- **Implementation**: Phase 3

#### 11. Periodization Awareness ✅ DESIGNED
- **Status**: Schema designed
- **Model**: `weekly_volume` table
- **Features**:
  - Track weekly volume per muscle group
  - AI factors weekly load into recommendations
  - "You've done 15 sets of chest this week" warnings
- **Implementation**: Phase 2

---

## Previously Resolved Issues (Unchanged)

### ✅ All Original Critical Issues Remain Resolved

1. **Exercise Database Seeding** - CSV provided in `assets/`
2. **Slot Structure** - One exercise per slot, can link for supersets
3. **Equipment Tracking** - Per-slot filter with CSV-derived equipment list
4. **Conflict Resolution** - User chooses which write to keep (Android phase)
5. **Heart Rate Storage** - Time-series until analytics, then drop (Android phase)
6. **Heart Rate Analytics** - Comprehensive metrics at all levels (Android phase)
7. **AI Response Format** - Structured JSON with recommendations
8. **Muscle Group Taxonomy** - 4-level hierarchy from exercise database
9. **Workout State Management** - Fully editable, auto-save, crash recovery
10. **Slot Behavior** - Can skip, re-order, return to skipped slots
11. **API Versioning** - URL-based `/api/v1/` approach
12. **Superset Linking** - Tag-based visual grouping

### ⏸️ Deferred to Android Phase

- **Authentication** - Using browser local storage for MVP
- **Bluetooth HR Monitoring** - Requires native BLE APIs
- **Offline Sync** - Limited to browser storage in web
- **Push Notifications** - Requires native capabilities

---

## New Considerations for Web-First

### Browser Storage Strategy
- **Technology**: localStorage + IndexedDB
- **Scope**: 
  - Workout in progress (auto-save)
  - Recent exercise selections
  - Equipment profile preference
- **Limitations**:
  - Not true offline-first
  - Data tied to browser/device
  - No background sync
- **Migration Path**: When auth added, sync local data to server

### Keyboard Navigation
- **Priority**: P3 (Phase 6)
- **Shortcuts**:
  - `←/→`: Previous/Next slot
  - `S`: Skip current slot
  - `Enter`: Complete current set
  - `Space`: Start/Stop rest timer
  - `Escape`: Cancel current action
- **Accessibility**: All actions also mouse/touch accessible

### Mobile Web Considerations
- **Responsive Design**: Required for mobile web usage
- **Touch Gestures**: Swipe for slot navigation
- **Screen Wake Lock API**: Keep screen on during workout
- **Limitations vs Native**:
  - No haptic feedback
  - Browser chrome takes space
  - Less reliable background operation

### Performance Requirements
- **Page Load**: < 2 seconds on 3G
- **Action Response**: < 100ms for UI updates
- **API Response**: < 500ms for most endpoints
- **Auto-Save**: Debounced, max 2 second delay

---

## Database Migration Plan

### New Tables Required
1. `equipment_profiles` - Equipment location presets
2. `slot_templates` - Reusable slot configurations
3. `superset_templates` - Pre-defined superset pairings
4. `personal_records` - PR tracking
5. `weekly_volume` - Periodization tracking
6. `exercise_substitutions` - Substitution history

### Schema Changes to Existing Tables
1. `routine_slots`:
   - Add `slot_type` (enum)
   - Add `time_limit_seconds`
   - Add `required_equipment_ids` (JSONB)
   - Add `target_reps_min`, `target_reps_max` (ranges)
   - Add `progression_rule` (JSONB)
   - Add `slot_template_id` (FK)

### Migration Order
1. Create new tables first (no dependencies)
2. Add new columns to `routine_slots`
3. Backfill default values
4. Add foreign key constraints

---

## API Endpoint Summary

### New Endpoints Required

```
# Equipment Profiles
GET    /api/v1/equipment-profiles
POST   /api/v1/equipment-profiles
GET    /api/v1/equipment-profiles/{id}
PUT    /api/v1/equipment-profiles/{id}
DELETE /api/v1/equipment-profiles/{id}
POST   /api/v1/equipment-profiles/{id}/set-default

# Slot Templates
GET    /api/v1/slot-templates
POST   /api/v1/slot-templates
GET    /api/v1/slot-templates/{id}
PUT    /api/v1/slot-templates/{id}
DELETE /api/v1/slot-templates/{id}

# Superset Templates
GET    /api/v1/superset-templates
POST   /api/v1/superset-templates
GET    /api/v1/superset-templates/{id}

# Personal Records
GET    /api/v1/personal-records
GET    /api/v1/personal-records/exercise/{exercise_id}
POST   /api/v1/personal-records  (usually auto-created)

# Analytics
GET    /api/v1/analytics/weekly-volume
GET    /api/v1/analytics/slot-performance
GET    /api/v1/analytics/exercise-progression/{exercise_id}
GET    /api/v1/analytics/movement-balance

# Enhanced Recommendations
POST   /api/v1/recommendations/slot
POST   /api/v1/recommendations/quick-fill
POST   /api/v1/recommendations/generate-routine  (goal-based)
```

### Enhanced Existing Endpoints

```
# Recommendations - Enhanced Response
POST   /api/v1/recommendations
- Add: not_recommended[] with reasons
- Add: movement_balance factor
- Add: weekly_volume_status factor

# Workouts - New Features
POST   /api/v1/workouts/{id}/quick-fill
POST   /api/v1/workouts/{id}/copy-last
```

---

## Testing Strategy for Web App

### Unit Tests
- AI recommendation logic
- Progression rule evaluation
- PR detection logic
- Weekly volume calculations

### Integration Tests
- Workout flow (start → exercise → complete)
- Quick-Fill with equipment profile
- Slot navigation state management
- Auto-save and recovery

### E2E Tests (Playwright)
- Full workout execution
- Routine creation with all slot types
- Equipment profile management
- Analytics page rendering

### Manual Testing Focus
- Mobile web experience
- Keyboard navigation
- Edge cases (browser refresh mid-workout)
- Performance on slow connections

---

## Success Criteria for Web Launch

### Functional Requirements
- [ ] Create routines with all slot types (standard, warmup, finisher, active_recovery, wildcard)
- [ ] Execute workouts with full slot navigation
- [ ] Track sets/reps/weight accurately
- [ ] Auto-save prevents data loss on refresh
- [ ] AI recommendations work with fallback
- [ ] Equipment profiles reduce setup friction
- [ ] Quick-Fill mode works for repeat workouts
- [ ] View workout history
- [ ] Basic analytics (volume, frequency)

### Non-Functional Requirements
- [ ] Responsive on desktop, tablet, mobile web
- [ ] Page load < 2 seconds
- [ ] No data loss from browser issues
- [ ] Works on Chrome, Firefox, Safari, Edge

### User Experience Goals
- Workout setup time < 30 seconds (with Quick-Fill)
- Intuitive slot navigation without documentation
- Clear visual feedback for progress
- Minimal friction for repeat workouts

---

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Browser storage limits | Low | Medium | Monitor usage, warn user |
| AI API rate limits | Medium | Low | Caching, fallback logic |
| Complex state management | Medium | Medium | Zustand, clear patterns |
| Mobile web performance | Medium | Medium | Optimize, test on devices |

### Product Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Feature creep | High | Medium | Stick to priority matrix |
| Over-engineering slots | Medium | Medium | Start simple, iterate |
| UI/UX complexity | Medium | High | User testing, simplify |

---

## Timeline Estimate

### Phase 1-2: Backend Enhancement (1-2 weeks)
- New models and migrations
- Enhanced AI service
- New API endpoints

### Phase 3: Routine Designer (2-3 weeks)
- Equipment profiles
- Slot templates
- Enhanced slot types
- Superset templates

### Phase 4: Workout Execution (3-4 weeks)
- Active workout interface
- Slot navigation
- Set tracking
- Quick-Fill mode
- Rest timer

### Phase 5: Analytics & History (2 weeks)
- Workout history
- Analytics dashboard
- Personal records

### Phase 6: Polish (1-2 weeks)
- Responsive design
- Keyboard shortcuts
- Dark mode
- Bug fixes

### Total: 9-13 weeks for full web app

---

## Open Questions

1. **User Testing**: When to recruit beta testers for web app?
2. **Analytics Tools**: Add usage analytics (Mixpanel, Amplitude)?
3. **Error Tracking**: Integrate Sentry for error monitoring?
4. **Hosting**: Where to deploy web app (Vercel, Netlify, self-hosted)?
5. **Domain**: slotfit.app? slotfit.io? Other?
