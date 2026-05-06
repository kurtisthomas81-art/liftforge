# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Deployment Rule — Always Do This After Every Change

After completing any code change, always:
1. Commit and push to GitHub
2. Provide the single-line Unraid rebuild command

```
cd /mnt/user/appdata/liftforge && git pull && docker compose up -d --build
```

Never split this across multiple lines. Never skip it. Always ask if the user wants to pull and rebuild on Unraid.

---

## App Philosophy

LiftForge is for the **average person who wants to get/stay in shape** — athletic and built, not stage-ready. The target physique is "Chris Evans Captain America / Evander Holyfield", not competitive bodybuilding. Volume landmarks, guidance language, and recommendations should reflect this. Hypertrophy-mode targets are available but are not the default experience.

---

## Stack

- **Backend:** FastAPI + SQLModel + SQLite (`/backend`)
- **Frontend:** SvelteKit 4 + static adapter (`/frontend`)
- **Deployment:** Docker Compose on Unraid; nginx serves the built frontend, FastAPI runs as a separate container
- **AI:** Ollama (local, llama3.1:8b) for coach chat

---

## Running Locally

```bash
# Backend (from /backend)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (from /frontend)
npm install
npm run dev        # dev server on :5173
npm run build      # static build (output to /frontend/build)
```

There are no automated tests. Verify changes manually via the app UI or by hitting `http://localhost:8000/api/health`.

---

## Project Layout

```
backend/
  main.py           startup, migration, seeding, backfill
  models.py         all SQLModel table definitions
  database.py       migrate_db() — safe ALTER TABLE migrations
  seed_data.py      108 exercises, 13 splits, landmarks per goal
  engine/
    meso_builder.py  mesocycle generation + preview engine
  routers/          15 router files — one per domain

frontend/
  src/routes/       SvelteKit pages (file-based routing)
  src/lib/api.js    single API client — all HTTP calls go here
  src/lib/stores.js activeSession, userProfile, sessionPlan stores
  src/lib/utils.js  formatDate, epley1RM, autoSessionName helpers
```

---

## Key Conventions

### Backend

**Migrations** — all new columns go in `database.py` `migrate_db()` as `("table", "column", "TYPE DEFAULT x")` tuples. Never write raw `ALTER TABLE` anywhere else. SQLite `ADD COLUMN` is idempotent via the PRAGMA check pattern already in place.

**Single user** — `USER_ID = 1` is hardcoded throughout every router. No auth system.

**Adding a new Exercise field** requires touching all of these in order:
1. `models.py` — add the field
2. `database.py` → `migrate_db()` — add the ALTER TABLE entry
3. `seed_data.py` — add the value for all seeded exercises + any backfill function
4. `main.py` → `on_startup()` — add a backfill call if needed (see `_backfill_sub_patterns` pattern)
5. `routers/exercises.py` — include in the serializer response
6. `routers/programs.py` → `exercises_db` dict — include if used in mesocycle building

**Startup seeding** — exercises, splits, and landmarks are seeded only if the table is empty. Backfills run every startup (guarded by a no-op check). If you add a new backfill, follow the `_backfill_sub_patterns` pattern.

### Volume / Landmark System

`MuscleVolumeLandmark` stores `(mev, mav_low, mav_high, mrv)` per muscle per user, keyed by `goal` (hypertrophy / general_fitness / strength / recomp). The active mesocycle's `goal` field determines which landmark row is used for volume chart targets.

`_aggregate_sets_by_muscle()` in `routers/volume.py` is the single source of truth for set counting:
- Warm-up sets (`set_type == "warmup"`) are excluded
- Primary muscles count as **1.0 set** per set performed
- Secondary muscles (`exercise.secondary_muscles` JSON field) count as **0.5 sets**
- Returns a `dict[str, float]` — display values may be fractional

The weekly volume chart (`/program` page) shows 7 muscles: `chest, back, quads, hamstrings, shoulders, biceps, triceps`. The `lats` muscle is tracked separately in the DB but not shown in the chart.

### Mesocycle Engine

- `sub_pattern` drives slot assignment and rep/set prescriptions (not `movement_pattern`)
- `PATTERN_PRESCRIPTION` in `meso_builder.py` is the source of truth for sets/reps/RIR by pattern and goal
- `SESSION_SLOT_TEMPLATES` defines default slot order per split type
- Core/abs are never auto-populated in primary slots (`CORE_MUSCLES` constant)
- The A/B rotation (`num_variants=2`) produces an A/B/A → B/A/B pattern across 2-week blocks, giving each session type 1.5× weekly frequency on average

### Frontend (Svelte 4)

- Use `on:click`, `bind:value` — not Svelte 5 runes
- `api.js` is the single source of truth for all HTTP calls — add new endpoints there first
- Navigation uses `goto()` from `$app/navigation` — never `window.location.href`
- Step 5 of the mesocycle wizard branches on `sessionMode`: `'auto'` uses the preview+swap flow; `'custom_slots'` uses the Caliber-style exercise list builder
- The bottom nav has 4 primary tabs (Home, Log, Program, History) + a "More" sheet organized into sections (Training / Analytics / Library / App). Settings lives as a `⚙` icon in the app header, not in More.

---

## Roadmap File

`ROADMAP.md` tracks all shipped features and upcoming work. Update it when phases complete.
