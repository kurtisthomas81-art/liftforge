# LiftForge Roadmap

Self-hosted workout tracker on Unraid. FastAPI + SvelteKit + SQLite + Ollama.
Repo: https://github.com/kurtisthomas81-art/liftforge

---

## ✅ Phase 1 — Core Logger (COMPLETE)

- 108-exercise seeded library with muscle mapping, equipment tags, substitution chains
- Workout logger: exercises, sets, reps, weight, RIR
- Session history with estimated 1RM progression charts (Epley formula)
- Exercise browser with muscle/equipment filters
- Equipment profile (per-user available equipment)
- Ollama AI coach chat (context-aware, 8B model)
- Docker Compose deployment (nginx + FastAPI + SQLite)

---

## ✅ Phase 2 — Mesocycle Engine (COMPLETE)

- All workout splits: 13 built-in templates + custom split builder
  - 2-day: Full Body 2x, Upper/Lower
  - 3-day: Full Body 3x, PPL, Arnold, Upper/Lower/FB
  - 4-day: Upper/Lower 2x ⭐, PHUL, PPL+FB, Bro 4-Day
  - 5-day: ULPPL ⭐, PHAT, Bro 5-Day
- Mesocycle builder wizard (4 steps: days → split → goal → review exercises)
- Hybrid exercise selection: app suggests, user swaps before confirming
- Volume landmarks per muscle: MEV / MAV / MRV (RP methodology, user-editable)
- Week-over-week set progression (MEV → MRV linear accumulation)
- Deload week scheduling
- Planned session view with targets + overload suggestions
- Volume tracking: per session, week, mesocycle, all-time
- Program adherence infrastructure
- Rest timer (auto-start after set, +30s/+60s/Skip, color countdown)
- Warm-up set flagging (excluded from volume counts)
- PR tracking (e1RM, weight, reps — stored + flagged in logger)
- Pre-session readiness check-in (1–5 scale)
- Progressive overload suggestions (next session weight calculated from RIR)
- Volume landmarks editable in Settings

---

## ✅ Phase 3 — Polish & Tools (COMPLETE)

- **Workout Templates** — save any session as reusable template; start workout from template
- **Body Measurements** — log body weight + measurements (waist, chest, arms, quads); trend chart
- **Deload Auto-Detection** — fatigue banner on dashboard when RIR trends + readiness signal overtraining
- **Data Export** — workouts CSV, measurements CSV, full JSON backup (Settings page)
- **Plate Calculator** — full page + inline mini-calc in logger; exact match + nearest above/below
- **Training Calendar** — monthly view, completed + planned sessions, color-coded by type
- **Nav reorganized** — Training / Tools / Library groups with dividers

---

## ✅ Apex UI Redesign (COMPLETE)

Full mobile-first redesign replacing the original dark-orange sidebar UI.

- **Typography**: DM Serif Display (headings, italic accents) + DM Sans (body)
- **Design tokens**: `#0a0a10` bg, `#e8365d` red accent, `#6868a0` muted
- **Navigation**: Bottom tab bar (5 tabs) + More sheet overlay — no sidebar
- **Screens rewritten**: Home, Log, Program, History, Calendar, Library, Measurements, Settings
- **New `/progress` route**: Readiness score (0–100), 1RM trend chart, week-over-week volume bars, 4 science cards, front/back muscle heatmap
- **Logger enhancements**: Per-set done toggle, inline RPE picker (6–10 → RIR), inline rest timer ring (62px SVG), session progress bar

---

## ✅ Phase 4 — Caliber-Inspired Features (COMPLETE)

| Feature | Description |
|---------|-------------|
| ~~Post-session RPE~~ | Rate overall workout 1–10 after finishing; feeds fatigue model |
| ~~Program adherence score~~ | % of planned sessions completed per mesocycle; per-week pills on Program page |
| ~~Muscle recovery map~~ | Front/back SVG body diagram; green/amber/red by time since last trained + RIR |
| ~~Weekly check-ins~~ | Monday prompt: energy/sleep/stress/soreness 1–5 dots; feeds fatigue score (+3 pts max) |
| ~~Goal setting~~ | Performance goals (e1RM / weight / reps) with deadline; auto-detected on session finish via Epley |
| ~~In-logger exercise swap~~ | "Swap" button mid-session; filtered by same muscle + your equipment |
| ~~Liftosaur sync~~ | Connect via API token; import full workout history; idempotent (skips duplicates) |
| ~~Session duration optimizer~~ | Set preferred duration (30–90 min); "Generate Session" builds time-budgeted workout from mesocycle muscle focus + equipment filter + goal-based sets/reps/rest; Today's Plan panel in logger |

---

## 🔮 Phase 5 — Advanced & Polish

| Feature | Status | Description |
|---------|--------|-------------|
| ~~Muscle activation diagrams~~ | ✅ Done | SVG front/back body on `/recovery` + `/progress`; colored by recovery status and weekly volume |
| ~~Session comparison~~ | ✅ Done | Week-over-week volume bars on `/progress`; this week vs. last week sets per muscle |
| ~~Systemic fatigue score~~ | ✅ Done | 0–10 score on `/progress` from RIR trends + readiness + deload recency + RPE + check-in |
| Habit tracking | 🔶 Partial | Weekly check-ins done (Mon: energy/sleep/stress/soreness); daily log + steps + protein still pending |
| ~~Published programs library~~ | ✅ Done | Starting Strength, GZCLP, 5/3/1 BBB, nSuns CAP3, Jeff Nippard PHUL — one-tap install from More → Programs Library |
| Superset support | — | Pair exercises, shared rest timer, logged back-to-back |
| Progress photos | — | Date-stamped, local storage only; side-by-side comparison |
| ~~Training notes search~~ | ✅ Done | Full-text search across session names, session notes, set notes — `/search` route + More sheet |
| ~~1RM percent calculator~~ | ✅ Done | 1RM % tab on Plates page — enter max, get table of 50–100% weights rounded to 2.5 |
| PWA / mobile install | — | Manifest + service worker so it installs as a home screen app on phone |
| ~~Periodization types~~ | ✅ Done | DUP / Linear / Block — picker in mesocycle wizard Step 3; engine applies correct rep/RIR scheme per week/session |
| ~~1RM test protocol~~ | ✅ Done | 4-step guided protocol: pick exercise → working max → warmup ramp (40–100%) → result with e1RM + PR badge; linked from exercises page + More sheet |
| ~~Post-mesocycle review~~ | ✅ Done | Auto-summary on completion: adherence %, per-muscle volume vs landmarks, RIR trend, MEV/MRV adjustment suggestions |
| ~~Injury / limitation tracking~~ | ✅ Done | Flag body parts + severity in Settings; ⚠ badge on affected exercises in library and logger |

---

## Architecture Notes

```
/home/cashbux/liftforge/
  backend/         FastAPI + SQLModel + SQLite
    engine/        meso_builder.py, progression logic
    routers/       14 router files
    seed_data.py   108 exercises + 13 splits + landmarks
  frontend/        SvelteKit (static adapter) + Chart.js
    src/routes/    16 pages
  docker-compose.yml
  data/            SQLite DB persisted here (mount on Unraid)
```

---

## Unraid Deployment

**Server path:** `/mnt/user/appdata/liftforge`
**GitHub repo:** `https://github.com/kurtisthomas81-art/liftforge`

### Initial setup (first time only)
```bash
cd /mnt/user/appdata
git clone https://github.com/kurtisthomas81-art/liftforge
cd liftforge
docker compose up -d --build
```

### Deploy an update
```bash
cd /mnt/user/appdata/liftforge
git pull && docker compose up -d --build
```

### Useful commands
```bash
# View backend logs (errors, startup)
docker logs liftforge-backend-1 2>&1 | tail -30

# View frontend logs
docker logs liftforge-frontend-1

# Restart without rebuilding
docker compose restart

# Stop everything
docker compose down

# DB is at (persisted across rebuilds)
/mnt/user/appdata/liftforge/data/liftforge.db
```

### Dev → Unraid workflow
```bash
# On Chromebook (Claude Code)
git add <files> && git commit -m "..." && git push

# On Unraid
cd /mnt/user/appdata/liftforge && git pull && docker compose up -d --build
```

---

## Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Users | Single user (user_id=1), FK-ready | Self-hosted, no auth complexity |
| DB | SQLite | Single file, zero config, easy backup |
| Volume metric | Sets per muscle (not tonnage) | Matches RP methodology |
| Olllama model | 8B (llama3.1:8b) | Fast on home hardware |
| Nutrition | Separate app | User decision |
| Calorie tracking | Excluded | User decision |
| CSS | Custom, no framework | Apex theme (#0a0a10 bg, #e8365d accent, DM Serif Display) |
