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

**Migrations** — all new columns go in `database.py` `migrate_db()` as `("table", "column", "TYPE DEFAULT x")` tuples. Never write raw `ALTER TABLE` anywhere else. SQLite `ADD COLUMN` is idempotent via the PRAGMA check pattern already in place. SQLModel table names are the class name fully lowercased with no separators: `MuscleVolumeLandmark` → `musclevolumelandmark`, `WorkoutSession` → `workoutsession`, etc.

**Single user** — `USER_ID = 1` is hardcoded throughout every router. No auth system.

**Adding a new Exercise field** requires touching all of these in order:
1. `models.py` — add the field
2. `database.py` → `migrate_db()` — add the ALTER TABLE entry
3. `seed_data.py` — add the value for all seeded exercises + any backfill function
4. `main.py` → `on_startup()` — add a backfill call if needed (see `_backfill_sub_patterns` pattern)
5. `routers/exercises.py` — include in the serializer response
6. `routers/programs.py` → `exercises_db` dict — include if used in mesocycle building

**Startup seeding** — exercises, splits, and landmarks are seeded only if the table is empty. Backfills run every startup (guarded by a no-op check). Existing backfill functions in `main.py`: `_backfill_sub_patterns`, `_backfill_secondary_muscles`, `_backfill_landmark_goals`. Add new backfills following the same pattern.

### Volume / Landmark System

`MuscleVolumeLandmark` stores `(mev, mav_low, mav_high, mrv)` per muscle per user, keyed by `goal`. The DB holds 48 rows (12 muscles × 4 goals). The active mesocycle's `goal` field determines which set of targets the volume chart uses. `_get_landmarks()` in `volume.py` filters by goal and falls back to `hypertrophy` if no rows exist for the requested goal.

Goal calibration (sets/week targets):

| Goal | Audience | MEV | MAV sweet spot | MRV |
|---|---|---|---|---|
| `general_fitness` | Athletic & functional — **default** | 3–4 | 6–12 | 12–16 |
| `hypertrophy` | Maximize muscle size | 6–10 | 12–22 | 20–26 |
| `strength` | Raw strength, compound focus | 2–4 | 4–8 | 8–14 |
| `recomp` | Build muscle, lose fat | 5–7 | 8–16 | 16–22 |

`_aggregate_sets_by_muscle()` in `routers/volume.py` is the single source of truth for set counting:
- Warm-up sets (`set_type == "warmup"`) are excluded
- Primary muscles count as **1.0 set** per set performed
- Secondary muscles (`exercise.secondary_muscles` JSON field) count as **0.5 sets**
- Returns `dict[str, float]` — values are rounded to 1 decimal in the API response

The weekly volume chart (`/program` page) shows 7 muscles: `chest, back, quads, hamstrings, shoulders, biceps, triceps`. The `lats` muscle is tracked in the DB but not shown in the chart.

### Mesocycle Engine

- `sub_pattern` drives slot assignment and rep/set prescriptions (not `movement_pattern`)
- `PATTERN_PRESCRIPTION` in `meso_builder.py` is the source of truth for sets/reps/RIR by pattern and goal — all 4 goals (`hypertrophy`, `general_fitness`, `strength`, `recomp`) are present; unknown goals fall back to `hypertrophy`
- `_DUP_PATTERNS` defines the rotating rep ranges for DUP periodization per goal
- `SESSION_SLOT_TEMPLATES` defines default slot order per split type
- Core/abs are never auto-populated in primary slots (`CORE_MUSCLES` constant)
- The A/B rotation (`num_variants=2`) produces an A/B/A → B/A/B pattern across 2-week blocks, giving each session type 1.5× weekly frequency on average
- `general_fitness` is the default goal in the mesocycle builder wizard

### Frontend (Svelte 4)

- Use `on:click`, `bind:value` — not Svelte 5 runes
- `api.js` is the single source of truth for all HTTP calls — add new endpoints there first
- Navigation uses `goto()` from `$app/navigation` — never `window.location.href`
- Step 5 of the mesocycle wizard branches on `sessionMode`: `'auto'` uses the preview+swap flow; `'custom_slots'` uses the Caliber-style exercise list builder
- The bottom nav has 4 primary tabs (Home, Log, Program, History) + a "More" sheet organized into sections (Training / Analytics / Library / App). Settings lives as a `⚙` icon in the app header, not in More.

---

## Roadmap File

`ROADMAP.md` tracks all shipped features and upcoming work. Update it when phases complete.
