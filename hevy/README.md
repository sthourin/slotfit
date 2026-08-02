# Hevy Export

Pulls a read-only snapshot of a Hevy account into JSON so the training history can
be analyzed and, later, imported into SlotFit.

## API notes

- Base URL: `https://api.hevyapp.com`
- Auth: an `api-key` request header (not a bearer token)
- Requires a Hevy Pro account; the key is issued at https://hevy.com/settings?developer
- Page size caps: 100 for `exercise_templates`, 10 for everything else
- Hevy's own docs call the API experimental and reserve the right to change it

## Setup

Set `HEVY_API_KEY` in the repo-root `.env` (gitignored — see `.env.example`):

```
HEVY_API_KEY=<key>
```

An exported `HEVY_API_KEY` environment variable also works and takes precedence.
`--api-key` exists but leaves the key in shell history.

## Usage

```bash
python hevy/pull_hevy.py                    # full snapshot into hevy/data/
python hevy/pull_hevy.py --max-pages 1      # smoke test, one page per resource
python hevy/pull_hevy.py --only workouts    # single resource
python hevy/pull_hevy.py --out data-2026-08-02   # keep a dated snapshot
```

Standard library only, so any Python 3.9+ interpreter works — the backend venv is
not required.

## Output

`hevy/data/` (gitignored — it holds personal training data):

| File | Contents |
| --- | --- |
| `user_info.json` | Account username |
| `workout_count.json` | Total workouts on the account |
| `workouts.json` | Every workout with its exercises and sets |
| `routines.json` | Saved routines |
| `routine_folders.json` | Routine folders |
| `exercise_templates.json` | Exercise templates, built-in and custom |
| `body_measurements.json` | Body measurement entries |
| `manifest.json` | Pull timestamp, per-resource counts, request count |

Re-running overwrites the output directory in place. Use `--out` for dated snapshots.

## Mapping to SlotFit

Not built yet. The relevant join is Hevy's `exercise_template_id` (and its
`primary_muscle_group` / `equipment` fields) against SlotFit's exercise database
and movement patterns, which is what would let logged Hevy sets seed the staple
pool and pattern coverage.
