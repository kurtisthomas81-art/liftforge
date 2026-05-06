# CLAUDE.md — LiftForge

Instructions for Claude Code when working in this repository.

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

## Stack

- **Backend:** FastAPI + SQLModel + SQLite (`/backend`)
- **Frontend:** SvelteKit 4 + static adapter (`/frontend`)
- **Deployment:** Docker Compose on Unraid; nginx serves the built frontend, FastAPI runs as a separate container
- **AI:** Ollama (local, llama3.1:8b) for coach chat

---

## Project Layout

```
backend/
  main.py           startup, migration, backfill
  models.py         SQLModel table definitions
  database.py       migrate_db() — safe ALTER TABLE migrations
  seed_data.py      108 exercises, 13 splits, landmarks
  engine/
    meso_builder.py  mesocycle generation + preview engine
  routers/          14 router files (programs, sessions, exercises, ...)

frontend/
  src/routes/       SvelteKit pages
  src/lib/api.js    single API client object
```

---

## Key Conventions

### Backend
- All migrations go in `database.py` `migrate_db()` as `("table", "column", "TYPE DEFAULT x")` tuples — never raw `ALTER TABLE` elsewhere
- `USER_ID = 1` throughout — single-user, no auth
- New Exercise fields need: model change → migrate_db entry → seed_data backfill → exercises API serializer → exercises_db dict in programs.py

### Frontend (Svelte 4)
- Use `on:click`, `bind:value` — not Svelte 5 runes
- `api.js` is the single source of truth for all HTTP calls — add new endpoints there first
- Step 5 of the mesocycle wizard branches on `sessionMode`: `'auto'` uses the existing preview+swap flow; `'custom_slots'` uses the Caliber-style exercise list builder

### Mesocycle Engine
- `sub_pattern` drives slot assignment and rep/set prescriptions (not `movement_pattern`)
- `PATTERN_PRESCRIPTION` in `meso_builder.py` is the source of truth for sets/reps/RIR by movement pattern and goal
- `SESSION_SLOT_TEMPLATES` defines the default slot order per split type
- Core/abs are never auto-populated in primary slots (`CORE_MUSCLES` constant)

---

## Roadmap File

`ROADMAP.md` tracks all shipped features and upcoming work. Update it when phases complete.
