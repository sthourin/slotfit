# SlotFit — Laptop Transition Bundle

Re-staged **2026-09-05** from `c:\projects\slotfit`, for the move to the
always-on host laptop. (First staged 2026-08-21; that bundle is superseded —
its dump predates two migrations and three sessions of training.)

All committed work is on GitHub at `https://github.com/sthourin/slotfit.git`.
**Everything now lives on `main`** — `feat/hevy-staple-seeding` was merged into
it and deleted on 2026-09-05, so any older instruction to check that branch out
will fail. `backup/pre-cleanup` still exists but is not needed for a restore.

## What is tracked and what is not

This file and `Restore-SlotFit.ps1` are **tracked in git** and arrive with the
clone. Everything else in the bundle — the dump, the `.env` files, the Hevy
export, the memory notes — is gitignored or untracked and can only travel by
being copied.

They were untracked until 2026-09-05, and that is exactly why they went stale:
nothing surfaced them in a diff, so the branch name rotted quietly until it
would have failed on the new laptop's very first command. Tooling that describes
the repo belongs under the same review as the repo.

The consequence to respect: **the repo copy is canonical.** Staging a bundle
copies these two files out of the checkout, so edit them in the repo and re-copy
— never the other way round, or the next restore will run against instructions
nobody can see in a diff.

## Quick start

`Restore-SlotFit.ps1` in this folder performs every step below. From an
elevated-not-required PowerShell 7 prompt on the new laptop:

```
cd "<this folder>"
.\Restore-SlotFit.ps1
```

It prints its plan and asks for confirmation first. Useful flags:

- `-RepoPath D:\src\slotfit` clone somewhere other than `C:\projects\slotfit`
- `-Force` overwrite existing config files and restore over a non-empty database
- `-Yes` skip the confirmation prompt
- `-SkipClone`, `-SkipFiles`, `-SkipDatabase`, `-SkipDeps` run a subset

The script is re-runnable. It will not overwrite a config file that already
exists, and it refuses to restore over a database that already has tables
unless `-Force` is given. It verifies the restore by comparing row counts
against the figures recorded at dump time, and fails loudly if any differ.

Prerequisites: git, Docker Desktop running, python and npm on PATH.

The manual procedure follows, for reference or if the script cannot be used.

## Contents and destinations

| File in this bundle | Destination on the new laptop |
| --- | --- |
| `slotfit-db-2026-09-05.dump` | PostgreSQL `slotfit` database (see restore steps) |
| `slotfit-.env` | `<repo>\.env` |
| `slotfit-.env.e2e` | `<repo>\.env.e2e` |
| `slotfit-vscode-settings.json` | `<repo>\.vscode\settings.json` |
| `hevy-data\*.json` (8 files) | `<repo>\hevy\data\` |
| `claude-memory\*.md` (**9 files**) | `C:\Users\<user>\.claude\projects\c--projects-slotfit\memory\` |

There is no `web/.env` — the web client runs on its defaults. Only create one
if a `VITE_`-prefixed variable is actually needed.

The memory files are per-machine **and per-account**: a different Claude account
on the new laptop starts with none of them. They are supplementary rather than
essential — `CLAUDE.md` in the repo carries the project's design decisions and
travels with the clone — but copying them preserves the operational notes
(venv path, e2e setup, Hevy backfill ordering) that would otherwise be
rediscovered the hard way.

## Restore steps

1. Clone the repo and check out the working branch.

   ```
   git clone https://github.com/sthourin/slotfit.git
   cd slotfit
   ```

   `main` is the only working branch as of 2026-09-05 — no checkout needed.

2. Drop the config and data files into the destinations in the table above.
   The `.env` files are gitignored, so they will not arrive with the clone.
   `.env.example` in the repo documents every variable if anything needs
   checking against it.

3. Start PostgreSQL. It runs in Docker, defined by `backend/docker-compose.yml`
   (container `slotfit-db`, postgres:15, port 5432).

   ```
   cd backend
   docker compose up -d
   ```

4. Restore the database dump. The compose file creates an empty `slotfit`
   database on first start, so restore into it directly.

   ```
   docker cp ..\path\to\slotfit-db-2026-09-05.dump slotfit-db:/tmp/slotfit.dump
   docker exec slotfit-db pg_restore -U postgres -d slotfit --clean --if-exists /tmp/slotfit.dump
   ```

   In Git Bash rather than PowerShell, the container path gets rewritten to a
   Windows path and `pg_dump`/`pg_restore` fail with "No such file or
   directory". Either prefix with `MSYS_NO_PATHCONV=1` or skip the copy and
   stream it: `docker exec -i slotfit-db pg_restore -U postgres -d slotfit
   --clean --if-exists < slotfit-db-2026-09-05.dump`.

   Verify the history came across:

   ```
   docker exec slotfit-db psql -U postgres -d slotfit -Atc "SELECT count(*) FROM workout_sets;"
   ```

   Expected counts as of this dump (2026-09-05): 3267 exercises,
   228 workout_sessions, 932 workout_exercises, 2959 workout_sets,
   6 training_sessions, 17 round_entries, 15 entry_sets,
   14 bodyweight_readings, 2 day_plans, 10 movement_patterns,
   57 staple_exercises, 12 users.

   Alembic revision in this dump: `a3d81b6e4f27` (users.max_hr). After
   restoring, `alembic current` should report exactly that and `alembic upgrade
   head` should be a no-op. If it wants to run migrations, the dump and the
   checkout have drifted — stop and work out which is older before proceeding.

   **These figures are recorded at dump time and the restore script checks
   against them, so a stale dump verifies as "correct".** They prove the restore
   was faithful to the dump, not that the dump was current. If the source
   machine is still reachable, count it there and compare before trusting this.

5. Recreate the e2e database. It was deliberately not dumped — it drifts and is
   rebuilt from migrations.

   ```
   docker exec slotfit-db psql -U postgres -c "CREATE DATABASE slotfit_e2e;"
   ```

   Then run migrations against it with `E2E_DATABASE_URL` set, per the e2e notes.

6. Rebuild the dependency trees. These were not copied (359 MB combined) and
   are reproducible.

   ```
   cd backend && python -m venv venv && .\venv\Scripts\pip install -r requirements.txt
   cd ..\web && npm install
   ```

   Use `backend\venv\Scripts\python.exe` explicitly for all backend commands.
   A bare `python` or `pytest` resolves to the wrong interpreter.

7. If step 4 was skipped in favor of a fresh database, run migrations and both
   seed scripts. The seeds are required setup, not optional — without
   `seed_patterns` the `movement_patterns` table is empty and the pattern-based
   session feature returns 404 on entry and staple creation.

   ```
   cd backend
   .\venv\Scripts\python.exe -m alembic upgrade head
   .\venv\Scripts\python.exe -m scripts.seed_patterns
   .\venv\Scripts\python.exe -m scripts.seed_leverage
   ```

   Restoring the dump in step 4 already includes all seeded data.

   `seed_conditioning --commit` is a third seed the older bundles predate. It
   creates Rucking, Bodyweight Walk and Bodyweight Run, which the CSV catalogue
   has no rows for. The dump already contains them; only a from-scratch database
   needs it.

8. **Set the device id in the browser, or the app will look empty.** This is the
   step most likely to cause a false alarm right after a move: the database
   restores perfectly, the app loads, and there is no history anywhere.

   All history belongs to `device_id setup-verify-0001`. The web client reads
   that from `localStorage`, which a new machine's browser does not have — and
   `get_current_user` *creates* a fresh empty user for an unrecognised id rather
   than erroring, so nothing looks broken. Open the app and run:

   ```js
   localStorage.setItem('slotfit_device_id','setup-verify-0001')
   ```

   then reload. If history is still missing after that, *then* start diagnosing.
   Check `SELECT id, device_id FROM users` first — a dozen orphan accounts in
   that table are previous instances of exactly this.

## Deliberately not included

Regenerated by the steps above or by normal use: `backend/venv` (161 MB),
`web/node_modules` (198 MB), `backend/logs` (21 MB), `backend/htmlcov` (3.8 MB),
`.playwright-cli` (1.1 MB of debug captures), `web/test-results`,
`backend/.coverage`, `backend/.pytest_cache`, and all `__pycache__` directories.

`.claude/settings.local.json` is tracked in git and arrives with the clone.

`web/.env` does not exist despite being described in `CLAUDE.md`. There is
nothing to move for it.

## Secrets note

`slotfit-.env` and `slotfit-.env.e2e` contain live API keys (Anthropic, Gemini,
Hevy). Delete them from this OneDrive folder once they are in place on the new
laptop.
