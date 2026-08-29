# SlotFit UI Design Review

> **HISTORICAL — pre-pivot. Not the current state of the app.**
>
> Captured against the routine-template UI retired on 2026-07-28. Items 5
> (routine management), 6 (first-run on the Routine Designer) and 7 (exercise
> modal default tab) describe screens that no longer exist. Item 1 (mobile
> navigation) was fixed on 2026-08-11; the nav now collapses below `sm`.
>
> The method still stands as a template: Playwright capture at 1440x900 and
> 390x844, then review. Phase B of
> `docs/superpowers/specs/2026-08-22-android-client-decision.md` calls for
> re-running exactly this exercise against the session flow.

Date: 2026-07-28
Method: Playwright-driven capture of all pages at desktop (1440x900) and mobile (390x844) viewports against the seeded e2e database, followed by visual and interaction review. Companion to `feature-matrix.md`; findings here feed the Phase 1 plan.

## Critical (broken experience)

### 1. Mobile navigation is unusable
At 390px the top nav wraps into overlapping rows, "Exercise Browser" splits across lines, and Records/Settings render off-screen and cannot be reached. There is no hamburger menu or bottom nav. This confirms the Phase 1 responsive priority with concrete evidence: several pages are unreachable on a phone.

Recommendation: bottom tab bar on mobile (Workout, Routines, Exercises, More) with the remaining pages under More. Bottom tabs suit one-handed gym use better than a hamburger.

### 2. Route changes do not reset scroll position
Navigating from a scrolled page (e.g., clicking Start Workout lower on the start page) lands on the next page still scrolled down, hiding the header and nav entirely. Reproduced on desktop and mobile. React Router needs a scroll-to-top on route change (ScrollRestoration or a scrollTo effect).

### 3. Completed workouts show zero data in History
History cards for completed workouts show Duration 0m, Total Volume 0 lbs, Total Sets 0, and "Exercises: 0/0 completed" even for a session where an exercise was selected and a set logged in the UI. Either sets/exercise assignments logged during a workout never persist to the backend, or History computes from the wrong relation. Needs a functional investigation, not just styling: the copy-last-workout and pre-fill features depend on this data existing. Filed as P1 in the feature matrix backlog.

### 4. Timestamps display in UTC
An evening workout displays as "2:53:14 AM". Dates render raw (`7/28/2026 2:53:14 AM`). Convert to local time and use friendlier formatting; date-fns is already a dependency.

## High-impact UX gaps

### 5. No routine management
Routines cannot be listed, edited, deleted, or duplicated from the UI. The Routine Designer only creates new routines (the store's loadRoutine exists but nothing calls it from a picker), and the Start Workout page happily lists duplicate "E2E Push Day" entries with no way to remove them. Users will accumulate near-identical routines with no cleanup path. Recommendation: a routines list as the Designer's landing state (cards with edit/duplicate/delete), replacing the bare "No routine loaded" screen.

### 6. No home orientation or first-run experience
The app opens on the Routine Designer's empty state: "No routine loaded" and one button. Nothing explains the slot concept — SlotFit's core differentiator — or points a new user through the create-routine → start-workout loop. Recommendation: a simple dashboard/home (resume banner slot, quick actions, recent workouts) or at minimum an explanatory empty state with the three-step flow.

### 7. Exercise selection modal dead-ends on its default tab
The modal defaults to AI Recommendations, which for a slot without muscle groups shows only "No recommendations available. Try searching for exercises instead." The user must discover the second tab themselves, and the message never explains why there are no recommendations. Recommendation: auto-select the Search tab when the slot has no muscle groups; when muscle groups exist but recommendations fail, say why and offer the search tab inline.

### 8. Workout controls lack hierarchy
Pause, Complete, and Abandon are three equal-weight, full-width, saturated buttons (yellow, blue, red) permanently stacked in the sidebar. Abandon — the destructive action — has the same visual weight as Complete. Recommendation: Complete as the single primary action; Pause secondary/outline; Abandon a small text-level destructive link with its confirm.

### 9. Empty states are inconsistent
The Analytics Weekly Volume chart renders an empty dashed rectangle with a legend and no message; Records has a proper "No personal records yet" message; Routine Designer has a bare line. Standardize: every empty state names what will appear there and offers the action that produces it.

### 10. Meaningless metadata chips
Routine cards show "custom custom 1 slot" — routine type and workout style both default to "custom", producing duplicate noise chips. Only render chips that carry information (non-default values), and label them ("Type: anterior") or style them distinctly.

## Visual system and consistency

### 11. No coherent color system
Five saturated hues carry unrelated meanings: blue (brand/primary), purple (Select Exercise), green (Start Workout / active), yellow (pause), red (abandon/remove). Purple in particular is a one-off. Define tokens — primary, secondary, success, warning, destructive — and map actions consistently; Select Exercise should be primary, not a unique color.

### 12. Slot progress chips are cryptic
The progress bar renders a small "1" chip with an unexplained yellow corner dot and a small circle glyph. State encoding is color/glyph-only and undocumented. Recommendation: larger chips with slot name (or muscle group), explicit state styling (not started / in progress / done / skipped), and a text progress summary. On mobile these must be comfortable touch targets (44px+).

### 13. Label-heavy exercise cards
Cards repeat bolded field labels ("Equipment:", "Muscle Groups:", "Region:") on every card, which reads as a form rather than a browsable catalog. Use hierarchy instead: name, difficulty badge, then muted single-line metadata ("Clubbell · Shoulders · Upper Body").

### 14. Equipment filter does not scale
The Filter by Equipment control is 39 checkboxes inside a roughly 130px scrollbox with no search, showing 4 items at a time. Recommendation: searchable multi-select with selected-as-chips, or group by equipment category.

### 15. Inconsistent page containers
Pages mix container widths and paddings (some max-w-4xl, some 6xl, some plain container), so the content column visibly jumps between routes. Pick one content width scale and apply it app-wide.

## Accessibility

### 16. Form labels are not programmatically associated
Labels lack htmlFor/id association (discovered when Playwright's getByLabel failed on Settings and set inputs). Screen readers announce nothing for these inputs. Associate every label; this also improves test resilience.

### 17. Native confirm() dialogs
Skip slot, remove set, complete workout, and abandon all use window.confirm, which is unstylable, jarring on mobile, and inconsistent with the app's visual language. Replace with an in-app confirm dialog component.

### 18. Icon-only and color-only signals
The keyboard-shortcuts toggle is an emoji-only button with no accessible name; slot states are color-only. Add aria-labels and text/shape redundancy.

## Suggested sequencing

Phase 1 (already planned, confirmed by this review): mobile bottom nav, scroll restoration, container normalization, empty-state standardization, workout-controls hierarchy, timestamp localization, label association.

Phase 1 additions proposed: routine management list (item 5), exercise modal default-tab logic (item 7), History data persistence investigation (item 3 — functional, highest priority of the additions).

Phase 2 candidates: color token system, exercise card redesign, equipment filter redesign, in-app confirm dialogs, home dashboard.

Screenshot set: captured to the session scratchpad (d-*.png desktop, m-*.png mobile); regenerate anytime with playwright-cli against the running dev servers.
