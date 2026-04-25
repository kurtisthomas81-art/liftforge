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

## 🔄 Phase 4 — Caliber-Inspired Features (In Progress)

### High Priority
| Feature | Status | Description |
|---------|--------|-------------|
| ~~Post-session RPE~~ | ✅ Done | Rate overall workout 1–10 after finishing; feeds fatigue model |
| Program adherence score | 🔜 Next | % of planned sessions completed per mesocycle, per week |
| ~~Muscle recovery map~~ | ✅ Done | Front/back SVG body diagram; green/amber/red by time since last trained + RIR |
| Weekly check-ins | — | Monday prompt: energy, sleep quality, stress, soreness, adherence notes |
| Goal setting | — | Performance goals (e.g., "Bench 225 by July 1") with auto-detection when hit |
| ~~In-logger exercise swap~~ | ✅ Done | "Swap" button mid-session; filtered by same muscle + your equipment |

### Plate Calculator Enhancements (Phase 3.5)
| Feature | Status | Description |
|---------|--------|-------------|
| ~~Plate count stepper~~ | ✅ Done | Per-plate owned count; solver respects per-side limits |
| ~~Cable machine mode~~ | ✅ Done | Stack setup + pulley ratio (1:1 / 2:1); target resistance → plates to pin |

### Medium Priority
| Feature | Description |
|---------|-------------|
| Periodization types | DUP (rep ranges rotate per session), Linear, Block — in mesocycle wizard |
| 1RM test protocol | Guided warmup → max attempt progression; stores tested (not estimated) 1RM |
| Injury / limitation tracking | Flag body parts; exercises with affected movement patterns get ⚠ warning |
| Post-mesocycle review | Auto-summary on completion; adjust MEV/MAV landmarks for next meso |

---

## 🔮 Phase 5 — Advanced & Polish

| Feature | Description |
|---------|-------------|
| Published programs library | Seed 5/3/1, GZCLP, nSuns, Starting Strength, Jeff Nippard PHUL — just pick and run |
| Superset support | Pair exercises, shared rest timer, logged back-to-back |
| Muscle activation diagrams | SVG body map on exercise detail + session summary |
| Habit tracking | Daily log: sleep hours, steps, stress, protein hit → feeds weekly check-in |
| Progress photos | Date-stamped, local storage only; side-by-side comparison |
| Session comparison | This week vs. last week same session: volume delta, RIR delta, weight delta |
| Systemic fatigue score | Single 0–10 number from RIR trends + readiness + check-ins |
| Training notes search | Full-text search across all session + exercise notes |
| 1RM percent calculator | Given 1RM, show weight for any % (50%, 65%, 80%, etc.) |
| PWA / mobile install | Manifest + service worker so it installs as a home screen app on phone |

---

## Architecture Notes

```
/home/cashbux/liftforge/
  backend/         FastAPI + SQLModel + SQLite
    engine/        meso_builder.py, progression logic
    routers/       13 router files
    seed_data.py   108 exercises + 13 splits + landmarks
  frontend/        SvelteKit (static adapter) + Chart.js
    src/routes/    16 pages
  docker-compose.yml
  data/            SQLite DB persisted here (mount on Unraid)
```

**Update workflow:**
```bash
# On Chromebook (Claude Code)
git add -A && git commit -m "..." && git push

# On Unraid
cd /mnt/user/appdata/liftforge
git pull && docker compose up -d --build
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
