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
- Mesocycle builder wizard (5 steps: days → split → goal + periodization + duration → variation mode → review exercises)
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

## ✅ Phase 5 — Advanced & Polish (COMPLETE)

| Feature | Status | Description |
|---------|--------|-------------|
| ~~Muscle activation diagrams~~ | ✅ Done | SVG front/back body on `/recovery` + `/progress`; colored by recovery status and weekly volume |
| ~~Session comparison~~ | ✅ Done | Week-over-week volume bars on `/progress`; this week vs. last week sets per muscle |
| ~~Systemic fatigue score~~ | ✅ Done | 0–10 score on `/progress` from RIR trends + readiness + deload recency + RPE + check-in |
| ~~Habit tracking~~ | ✅ Done | Weekly check-ins (Mon: energy/sleep/stress/soreness) |
| ~~Published programs library~~ | ✅ Done | Starting Strength, GZCLP, 5/3/1 BBB, nSuns CAP3, Jeff Nippard PHUL — one-tap install from More → Programs Library |
| ~~Superset support~~ | ✅ Done | Pair any two exercises via SS button; combined card with red accent border; shared rest timer shows both names; pairings persist to templates |
| Progress photos | — | Date-stamped, local storage only; side-by-side comparison |
| ~~Training notes search~~ | ✅ Done | Full-text search across session names, session notes, set notes — `/search` route + More sheet |
| ~~1RM percent calculator~~ | ✅ Done | 1RM % tab on Plates page — enter max, get table of 50–100% weights rounded to 2.5 |
| ~~PWA / mobile install~~ | ✅ Done | Manifest + service worker; installs as home screen app on Android/iOS; offline shell cache |
| ~~Periodization types~~ | ✅ Done | DUP / Linear / Block — picker in mesocycle wizard Step 3; engine applies correct rep/RIR scheme per week/session |
| ~~1RM test protocol~~ | ✅ Done | 4-step guided protocol: pick exercise → working max → warmup ramp (40–100%) → result with e1RM + PR badge; linked from exercises page + More sheet |
| ~~Post-mesocycle review~~ | ✅ Done | Auto-summary on completion: adherence %, per-muscle volume vs landmarks, RIR trend, MEV/MRV adjustment suggestions |
| ~~Injury / limitation tracking~~ | ✅ Done | Flag body parts + severity in Settings; ⚠ badge on affected exercises in library and logger |

---

## 🔮 Phase 6 — Smart Programming

Intelligent program generation that accounts for session time, lifter experience, and auto-detected strength level.

### 6A — Lifter Profile Foundation ✅ COMPLETE

| Feature | Status | Description |
|---------|--------|-------------|
| ~~Sex field on profile~~ | ✅ Done | Male/Female toggle in Settings → Profile; persisted to UserProfile; used for sex-specific strength standards in the auto-grader |
| ~~Body weight in weekly check-in~~ | ✅ Done | Monday prompt includes optional body weight field; on submit auto-creates a BodyMeasurement entry flowing into the existing measurements trend chart |

### Bug Fixes Shipped Alongside 6A

| Fix | Description |
|-----|-------------|
| ~~Settings save 500 error~~ | `default_rest_seconds` and other UserProfile columns were missing from `migrate_db()` — PRAGMA-based migration now covers all columns, safe to re-run |
| ~~Silent save failures~~ | `saveProfile()` was swallowing all errors silently; now shows error message below Save button |
| ~~Home page greeting~~ | Greeting read `$userProfile?.name` but API returns `display_name`; always showed "Athlete" regardless of saved name |

### 6B — Strength Level Auto-Grader ✅ COMPLETE

| Feature | Status | Description |
|---------|--------|-------------|
| ~~Strength level calculator~~ | ✅ Done | `GET /api/profile/strength-level` — pulls best e1RM PRs for squat/bench/deadlift/OHP, divides by body weight, scores against sex-specific Symmetric Strength thresholds |
| ~~Auto-update on PR~~ | ✅ Done | `POST /api/prs/check/{session_id}` triggers grader after any e1RM PR; writes result back to `experience_level` on UserProfile |
| ~~Progress page strength card~~ | ✅ Done | Card on `/progress` showing overall level + per-lift badges with progress bars to next threshold |

**Grading thresholds (bodyweight multiples):**

| Lift | Beginner | Intermediate | Advanced | Elite |
|------|----------|--------------|----------|-------|
| Squat (M/F) | < 1.25 / 0.75× | 1.25–1.75 / 0.75–1.2× | 1.75–2.25 / 1.2–1.6× | > 2.25 / 1.6× |
| Bench (M/F) | < 1.0 / 0.6× | 1.0–1.35 / 0.6–0.9× | 1.35–1.75 / 0.9–1.2× | > 1.75 / 1.2× |
| Deadlift (M/F) | < 1.5 / 0.9× | 1.5–2.0 / 0.9–1.4× | 2.0–2.5 / 1.4–1.9× | > 2.5 / 1.9× |
| OHP (M/F) | < 0.65 / 0.35× | 0.65–0.85 / 0.35–0.55× | 0.85–1.1 / 0.55–0.75× | > 1.1 / 0.75× |

Overall level = weakest lift (Caliber-style — you're only as strong as your weakest link).

### 6C — Smart Mesocycle Builder ✅ COMPLETE

| Feature | Status | Description |
|---------|--------|-------------|
| ~~Wizard exercise preview + swap~~ | ✅ Done | Step 4 shows auto-selected exercises per day; swap any before generating; overrides passed to engine |
| ~~Session duration in wizard~~ | ✅ Done | Step 3 pulls `preferred_session_minutes` from profile as default (30/45/60/75/90 min slider); overrideable per mesocycle |
| ~~Time-budget exercise cap~~ | ✅ Done | Engine computes `max_exercises_per_session` from duration + goal (hypertrophy: ~8.75 min/ex; strength: ~11.75 min/ex); compounds prioritized, session capped before isolation work |
| ~~Level-aware exercise selection~~ | ✅ Done | Beginners: compounds only, max 4 exercises, 12–15 reps. Intermediate: compounds + isolation, standard reps. Advanced: full range. |
| ~~Level-aware volume progression~~ | ✅ Done | Beginners: MEV + 1 set/week. Intermediate: MEV + 2/week (standard). Advanced: MEV + 3/week toward full MRV. |
| ~~Periodization gating by level~~ | ✅ Done | Linear pre-selected for beginners. DUP/Block locked with lock icon + tooltip for beginners; unlock at Intermediate. |

### 6D — Engine Overhaul ✅ COMPLETE

Rewrote `meso_builder.py` and `generate_session()` to produce physiologically sound, realistic workouts.

| Fix | Status | Description |
|-----|--------|-------------|
| ~~Realistic time budgets~~ | ✅ Done | 90s/compound set + 45s/isolation set + 10-min warmup reserve. Never cuts exercises — reduces sets/reps first, silent 10% inflation as last resort |
| ~~Prescribed rest per exercise~~ | ✅ Done | 3 min compounds, 2 min isolations, 1 min 15 sec supersets — included in session response |
| ~~Dynamic warm-up sets~~ | ✅ Done | 3 sets before first heavy compound, 2 before first compound, 1 before first isolation, 0 if muscle already warm from a prior exercise |
| ~~Secondary muscle volume credit~~ | ✅ Done | Bench press credits triceps at 50%; reduces or eliminates need for direct isolation work |
| ~~High-fatigue compound blocking~~ | ✅ Done | No squat + deadlift in same session — any second axial-load compound is blocked regardless of pattern |
| ~~Same-primary compound blocking~~ | ✅ Done | Max 1 compound per primary muscle group per session (bench+incline blocked; bench+OHP allowed; pullup+lat pulldown blocked; pullup+row allowed) |
| ~~Push/pull compound balance~~ | ✅ Done | Push and pull compound counts stay within 1 of each other throughout selection |
| ~~Muscle frequency warnings~~ | ✅ Done | `frequency_warnings` in preview response flags any muscle hit < 2x/week |
| ~~Exercise ordering~~ | ✅ Done | High-fatigue compounds first → medium compounds → isolations (CNS-optimal order) |

---

### 6E — Mesocycle Engine V2 + Custom Builder ✅ COMPLETE

Complete rewrite of slot selection, rep/set prescriptions, and A/B/C variant system. New custom builder UI (Caliber/RP-style).

#### Engine fixes & data layer

| Fix | Description |
|-----|-------------|
| ~~exercises_db missing fields~~ | `movement_pattern`, `force`, `secondary_muscles` were never included in the exercises dict — silently broke all blocking/balance rules. Fixed. |
| ~~`sub_pattern` field~~ | New field on `Exercise` model. Computed from `movement_pattern` + `force` + `primary_muscles`. Drives slot assignment and prescriptions. Backfilled on startup. |
| ~~Abs excluded from auto-selection~~ | `CORE_MUSCLES` constant; abs/core never fill a primary slot in any split |
| ~~Pattern × Goal rep/set matrix~~ | `PATTERN_PRESCRIPTION`: hip/knee dominant → 5–10 reps heavy; push/pull → 8–12; isolation → 12–20. Beginners get conservative RIR end. Sets ramp MEV→MRV across weeks. |
| ~~Slot-based session structure~~ | `SESSION_SLOT_TEMPLATES` covers all split types (full_body, push, pull, legs, lower, upper, chest, back, shoulders, arms). Axial-load rule enforced structurally — one knee_dominant and one hip_dominant max per template. |
| ~~A/B/C variant system~~ | `num_variants` (1/2/3) on Mesocycle; `session_counter` increments on each start; variant letter cycles A→B→C. A=horizontal push/pull, B=vertical, C=horizontal with different exercise index. |
| ~~`sub_pattern` in exercises API~~ | Added to `_serialize()` and `?sub_pattern=` query filter for client-side picker |
| ~~Validate-slots endpoint~~ | `POST /api/programs/mesocycles/validate-slots` — returns per-slot prescriptions, push/pull balance, axial-load warnings, estimated session time |
| ~~Preview-custom-slots endpoint~~ | `POST /api/programs/mesocycles/preview-custom-slots` — returns exercise assignments for user-defined slot lists; honors pinned exercise IDs |

#### Custom mesocycle builder wizard (5-step)

| Feature | Description |
|---------|-------------|
| ~~Step 3: Variation picker~~ | A / A-B / A-B-C rotation; options bounded by days/week (2-day can't pick A/B/C) |
| ~~Step 3: Mode toggle~~ | Auto (engine picks) vs Custom (user builds) |
| ~~Step 5 Auto mode~~ | Engine auto-populates exercises; variant badge per day; swap any exercise before generating |
| ~~Step 5 Custom mode — empty start~~ | Days open empty; user builds from scratch (Caliber/RP style) |
| ~~Add exercise picker~~ | Searchable bottom sheet with muscle filters; shows `sub_pattern` for context |
| ~~Drag-to-reorder~~ | `svelte-dnd-action` — touch + mouse; ⠿ grip handle; prescriptions refresh after reorder |
| ~~Superset pairing~~ | SS button pairs adjacent exercises; gold left border + SS badge; time estimate accounts for reduced rest |
| ~~Set type toggle~~ | ST / RP / DS badge per exercise; cycles on tap |
| ~~Live time estimate~~ | Per-day `~N min` in header; computed client-side from sub_pattern rest times (high 3 min / medium 2 min / low 90 sec); 15% reduction for supersets |
| ~~Delete variant days~~ | × on each day card; re-letters remaining A/B/C; payload `num_variants` matches actual count |
| ~~superset_group passthrough~~ | Flows from wizard through `custom_slot_sessions` → `generate_mesocycle` → `PlannedExercise` |

---

### 6F — Volume Gauge, Progression Schemes & Builder UX ✅ COMPLETE

Real-time volume feedback, two new periodization styles, set techniques, and builder quality-of-life polish.

#### Volume Gauge

| Feature | Description |
|---------|-------------|
| ~~Real-time Volume Check~~ | Collapsible "Volume Check" card above the step 5 review — shows per-muscle set count vs. goal's MEV/MAV/MRV thresholds; color-coded (red/green/amber/orange) |
| ~~Frequency-weighted gauge~~ | A/B rotation with 3 training days counts each unique session 1.5×/week so gauge reflects actual weekly sets, not per-session sets |
| ~~Calves & abs always visible~~ | Fixed bug where muscles with 0 sets were hidden; all muscles with landmark data show even at 0% |
| ~~Compound secondary muscles seeded~~ | abs added to deadlift / squat / OHP / pull-up variants; calves added to squat / leg press / lunge variants; startup backfill merges into already-populated arrays |
| ~~`GET /landmarks/{goal}` endpoint~~ | New route returns `{ muscle: { mev, mav_low, mav_high, mrv } }` for a given goal; used by gauge without extra round-trips |

#### Progression Schemes

| Feature | Description |
|---------|-------------|
| ~~Double Progression~~ | Rep range fixed across all weeks; RIR descends 3→1 linearly; "hit the top of your range → add weight" model — most approachable for beginners/intermediates |
| ~~Wave Loading~~ | 3-week repeating wave: heavy (strength reps, RIR 1) → moderate → volume (hypertrophy reps, RIR 3); models 5/3/1 heavy/medium/light structure |
| ~~Remove experience locks~~ | DUP and Block no longer locked for beginners; replaced with "Intermediate+" / "Advanced" info badges; all 6 schemes accessible to anyone |

#### Set Techniques A La Carte

| Feature | Description |
|---------|-------------|
| ~~Chip selector in builder~~ | Straight / Drop / Rest-Pause / Myo-Reps chip row per exercise; replaces cycling ST/RP/DS button; active chip highlighted in gold |
| ~~`set_technique` on PlannedExercise~~ | New DB field (`TEXT DEFAULT 'straight'`); migration-safe; persists through mesocycle generation |
| ~~Fixed set_technique passthrough bug~~ | `set_type` was captured from the frontend slot payload but never written to `PlannedExercise`; now passed correctly through `meso_builder.py` |
| ~~Technique badge in logger~~ | When `set_technique` is not straight, a badge shows on the exercise header in the planned session view |

#### Builder UX Polish

| Feature | Description |
|---------|-------------|
| ~~Editable sets/reps in custom mode~~ | Sets, reps min/max, and RIR are inline number inputs in step 5 exercise cards; gauge responds immediately as values change |
| ~~refreshPrescriptions preserves edits~~ | After adding a new exercise, existing exercises retain their user-tuned sets/reps; only the new exercise receives fresh prescriptions |
| ~~A/B rotation UX fix~~ | Full-body splits with A/B rotation show exactly 2 session cards (not 3); PPL-style splits always show all days; variant picker hidden in custom mode |
| ~~Unified A/B rotation display~~ | All 6 screens (home, program, program detail, planned session, calendar ×2) show stripped base name + gold variant badge pill ("Full Body" + "A") instead of raw "Full Body A" |
| ~~Rotation pattern pill~~ | Program page "This Week" section shows "A/B/A pattern" or "B/A/B pattern" pill computed from current week number |

---

## ✅ Phase 7 — Intelligence & Automation (SHIPPED)

### Autoregulation

RIR-driven weight auto-adjustments. When a user logs avg RIR ≤ 1 on straight sets for the same exercise across 2 consecutive completed sessions, the next planned session shows an **AR badge** with a pre-filled suggested weight.

| Feature | Description |
|---------|-------------|
| ~~`_compute_ar()` helper~~ | Queries last 2 completed sessions per exercise; checks avg RIR ≤ 1.0 on straight sets; returns `ar_triggered` + `ar_suggested_weight` |
| ~~Movement-based increments~~ | `hip_dominant` (deadlift family) = +10 lbs; `knee_dominant` (squat family) = +5 lbs; all others (bench, OHP, rows) = +2.5 lbs |
| ~~% floor fallback~~ | If the fixed increment is < 1% of current weight (very heavy lifts), falls back to 2.5% rounded to nearest 2.5 lbs |
| ~~AR badge in planned session~~ | "AR" pill + suggested weight shown per exercise in `/planned/[id]` view |
| ~~AR hints carried to logger~~ | `arHints` store populated before `goto('/log')`; logger checks hints first in `loadOverloadSuggestion()` and shows red "AR: X lbs (auto-reg +2.5%)" hint |
| ~~Manual overload uses same increment~~ | `get_planned_session()` overload suggestion also uses `_ar_increment()` instead of flat 2.5% |

### Advanced Analytics (`/progress` page)

| Feature | Description |
|---------|-------------|
| ~~Strength / Bodyweight ratio chart~~ | Multi-line Chart.js showing squat/bench/deadlift/OHP × bodyweight ratio over time; requires PRs + body weight measurements; hidden if < 2 data points per lift |
| ~~Volume sweet spot detection~~ | For each Big 4 lift with 3+ PRs: counts working sets in the 7 days preceding each PR session; buckets into `0–5 / 6–9 / 10–13 / 14–17 / 18+`; shows peak bucket ("Chest — best results at 10–13 sets/week") |
| ~~Predicted 1RM trajectory~~ | Linear regression on last 8 history points; projects 8 weeks forward as a dashed muted line overlaid on the 1RM trend chart; hidden if < 3 sessions |
| ~~`GET /analytics/strength-ratio-history`~~ | New `analytics.py` router; returns per-lift `{date, e1rm, body_weight, ratio}` arrays |
| ~~`GET /analytics/volume-sweet-spot`~~ | Same router; reuses `_aggregate_sets_by_muscle()` from `volume.py` |

### Rest Timer Chime

| Feature | Description |
|---------|-------------|
| ~~Audible chime on timer expiry~~ | Web Audio API 880 Hz sine wave with 1-second exponential fade; fires at end of countdown in logger; works offline (no files, no external deps) |

### Data Management

| Feature | Description |
|---------|-------------|
| ~~Individual session delete~~ | "Delete" button in expanded session detail on `/history`; cascade-deletes sets |
| ~~Clear All sessions~~ | Red "Clear All" button above session list on `/history`; wipes all completed sessions |
| ~~Liftosaur: clear imported data~~ | "Clear imported data" button in Settings → Liftosaur section; deletes only sessions tagged `source="liftosaur"` |
| ~~App Reset (Danger Zone)~~ | Red "Reset App" button in Settings → Danger Zone; `DELETE /api/reset` wipes all user data while preserving exercise library, splits, and landmarks |
| ~~Liftosaur sync fix~~ | Fixed date regex (`[T ]` separator) and incomplete set parsing (comma-split before regex); `source="liftosaur"` tag on imported sessions |
| ~~WorkoutSession.source field~~ | New column; migration-safe; enables targeted import clearing |

---

## ✅ Phase 8 — Smart Session Quality (SHIPPED)

### Liftosaur Import Pipeline

| Feature | Description |
|---------|-------------|
| ~~Exercise alias system~~ | `aliases` JSON field on `Exercise`; sync lookup checks name + all aliases (case-insensitive); no more duplicate DB entries when Liftosaur uses a different name for the same exercise |
| ~~Import queue~~ | Unrecognized Liftosaur exercise names land in `ExerciseImportQueue` instead of auto-creating junk entries. User reviews each in `/import-queue`: match to existing (auto-adds alias for future imports), add as new, or dismiss |
| ~~Queue badge~~ | Amber pill badge on Settings gear icon when queue has pending items; `importQueueCount` store refreshed after every sync |
| ~~Alias backfill~~ | Startup backfill seeds common variant aliases ("flat bench press", "overhead press", "bent over row", "pull up/ups", "chin up/ups", "barbell squat", "dl") |

### Session Generation Intelligence

| Feature | Description |
|---------|-------------|
| ~~Injury-aware exercise selection~~ | Active injuries (from Settings) exclude related movement patterns and primary muscles from auto-selection; `INJURY_EXCLUDED_PATTERNS` + `INJURY_EXCLUDED_MUSCLES` maps in engine |
| ~~Cross-session recovery check~~ | 72-hour lookback; per-muscle `RECOVERY_HOURS` thresholds (24–72h); `recovery_warnings` returned in generate response flagging muscles trained too recently |
| ~~Readiness modulation~~ | `?readiness=1–5` query param on `POST /sessions/generate`; ≤2 → 65% volume + RIR+2; ==3 → 85% volume + RIR+1; 4–5 → standard programming |

### Warmup Pre-population

| Feature | Description |
|---------|-------------|
| ~~Already-warm rule~~ | `_warmup_sets_needed` returns 0 when primary muscle already activated — no barbell exception; all warmups skipped |
| ~~Barbell sequence~~ | Fresh barbell compound → 3 sets: empty bar (45 lbs) → 50% → 75% of last working weight. Isolation → 2 sets: bar → 65% |
| ~~Non-barbell sequence~~ | Fresh compound → 2 sets: 50% → 75%. Isolation → 1 set: 50% |
| ~~Auto-created at session start~~ | `generate_session` pre-creates warmup `WorkoutSet` rows immediately; weights pulled from last straight set for that exercise; rounded to nearest 5 lbs; graduated sets null if no history |
| ~~Warmup rest time~~ | `rest_seconds = 60` stored on all auto-created warmup sets; log page rest timer uses per-set value (warmup completions start 1-min countdown instead of default) |
| ~~Quick Test updated~~ | Sandbox session uses `_build_warmup_sets` directly — always reflects current warmup rules |

### Logger Polish

| Feature | Description |
|---------|-------------|
| ~~Timer starts on first set~~ | Workout elapsed timer now starts when first set is checked done (warmup or working), not on session creation; persisted in `sessionStorage` across page navigations |
| ~~Quick Test sandbox~~ | "Quick Test" button on empty log page creates a pre-populated Bench/Squat/Row session for UI exploration without building a real workout |
| ~~Warmup toggle~~ | "W" button on each set row flips `set_type` between warmup and straight; warmup rows render at 65% opacity; excluded from all volume calculations |

---

## ✅ Phase 9 — Logger UX Overhaul (SHIPPED)

Fixes and improvements to the active session experience driven by real-world testing.

### Exercise Library

| Feature | Description |
|---------|-------------|
| ~~Exercise edit + delete~~ | Full edit modal (name, aliases, muscles, equipment, pattern, mechanics, force, bilateral, notes); delete blocked with 409 if exercise has logged sets |
| ~~Exercise deduplication~~ | Removed duplicate/miscategorized exercises (Machine Lateral Raise, Cross-Body Hammer Curl) via startup purge; no data loss if sets exist |
| ~~Category fixes~~ | Reverse Curl, Upright Row, Band Pull-Apart, Shrug recategorized; secondary muscle arrays corrected for curl/tricep/fly movements |
| ~~Forearms + calves tracked~~ | Added to volume chart, landmarks (all 4 goals), and fatigue report; 4 new forearm exercises seeded (Wrist Curl, Reverse Wrist Curl, Reverse Curl, Farmer's Carry) |

### Volume & Weight Tracking

| Feature | Description |
|---------|-------------|
| ~~Weight moved per exercise~~ | `weight_moved` (lbs) shown per exercise on session detail in history; session total also shown |
| ~~Warmup exclusion everywhere~~ | Warmup sets excluded from set_count and weight_moved in history, progression charts, and all volume endpoints |
| ~~Correct set counting rule~~ | Only sets where `reps > 0` (user entered actual reps) count toward volume and weight moved; blank/unattempted sets contribute nothing |

### Active Session Logger

| Feature | Description |
|---------|-------------|
| ~~Sticky session header~~ | Timer, session name, progress bar, and rest card are always visible while scrolling; fixed by changing page layout from `min-height` to `height: 100dvh` |
| ~~Remove exercise from session~~ | ✕ button on each exercise card with inline confirmation ("Remove + all sets?" → Remove / Keep); backend `DELETE /sessions/{id}/exercises/{ex_id}` |
| ~~Superset remove support~~ | ✕ button present on superset exercise cards too |
| ~~Target reps label + actual reps input~~ | Set row now shows target as non-editable label (e.g. `8 →`) sourced from session plan or last session history; separate blank input for actual reps; input turns **green** if ≥ target, **red** if below |
| ~~Live color feedback~~ | Color updates instantly while typing (on:input), saves to DB on blur/change |
| ~~`is_done` persisted~~ | Tapping the checkmark now saves `is_done` to the DB (fire-and-forget); was previously client-side only |
| ~~Sandbox feature parity~~ | Sandbox working sets use `target_reps=N, reps=0` to match the live model; always testable with new features |

---

## ✅ Phase 9.5 — Plate Intelligence & UX Polish (SHIPPED)

### Terminology Simplification Pass

Plain-English pairings added across 12 frontend files — jargon kept, context added inline or via tooltip.

| Location | Change |
|----------|--------|
| Volume Landmarks table headers | `MEV` / `MAV Low` / `MAV High` / `MRV` with descriptive `title=` tooltips |
| Program builder wizard | "Build Training Block" (was "Build Mesocycle"); "Training Block Name" label |
| Program page | "Build Custom Training Block"; "Recovery Week (Deload)" badge and alert |
| Program detail | Week label shows "Recovery Week" instead of "Deload" |
| Home page | Fatigue alert: "take a recovery week (deload)" |
| Planned session | `@ RIR N` label with tooltip "Reps In Reserve — stop when you have N reps left" |
| Recovery page | Subtitle: "effort (RIR — reps left in tank)"; Avg RIR header tooltip |
| Logger | RPE column header tooltip: "Rate of Perceived Exertion — how hard the set felt" |
| Progress page | Help cards: "Volume Targets (MEV → MRV)", "RIR — Reps Left in Tank", "Recovery Week (Deload)"; section title "Max Lift Trend (1RM)" |
| Exercise page | "Best est. 1-rep max (1RM)" stat label |
| Programs library | "Recovery (deload) on week N" label; `<span title="Reps In Reserve">RIR</span>` |
| Volume Gauge | Tooltip: `floor: N sets (MEV) · target: lo–hi sets (MAV) · limit: N sets (MRV)` |

### Plate Inventory System

| Feature | Description |
|---------|-------------|
| ~~Exercise loading type~~ | `loading_type` derived from `equipment_required` on every exercise API response — barbell / cable / dumbbell / other; no new DB column needed |
| ~~`plate_inventory` on UserProfile~~ | JSON field storing barbell plate counts per denomination + dumbbell pair weight list; migration-safe |
| ~~Settings → Plate Inventory section~~ | Two-tab UI: Barbell (denomination rows with ± steppers, steps of 2, shows "N per side"); Dumbbells (tap-to-toggle grid of common weights 5–60 lbs) |
| ~~Plates page persistence~~ | Loads saved barbell inventory on mount; auto-saves on every count change (1.2 s debounce); round-trips dumbbell data so saving barbell counts never wipes dumbbell list |
| ~~Logger ⊙ button — loading-type aware~~ | Hidden for cable and bodyweight exercises; shown for barbell and dumbbell; mode auto-detected from exercise loading type on open |
| ~~Barbell calc — inventory limits~~ | Plate solver respects owned plate counts (can't suggest plates you don't have); falls back to unlimited if no inventory set |
| ~~Dumbbell picker modal~~ | Grid of owned dumbbell weights; nearest to the set's current weight highlighted in gold; tap any weight to select it and pre-fill the "Use X lbs" button |

---

## ✅ Phase 10 — Intelligence & Session Experience (SHIPPED)

### Bug Fixes

| Fix | Description |
|-----|-------------|
| ~~Exercise swap silent data loss~~ | `confirmSwap()` now rolls back UI and shows error if API call fails — previously optimistic update had no error recovery |
| ~~`repeatSession` full page reload~~ | `window.location.href` replaced with `goto('/log')` + added missing import — was blowing away all SvelteKit stores |
| ~~Ollama errors masked as "offline"~~ | Unexpected exceptions now log to console and return a distinct message instead of the generic offline message |
| ~~RIR early/late trend asymmetry~~ | Single-datapoint muscles now return `null` for both early and late trend instead of asymmetric `null` / `value` |
| ~~"Build Custom Training Block" hover~~ | Removed conflicting `create-btn` class causing red text on red background (invisible on hover) |
| ~~Button style inconsistency~~ | "Build Custom Training Block" now uses `start-day-btn` to match all other primary CTAs |

### AI Coach Upgrade

Full context injection + safety guardrails replacing the minimal original implementation.

| Feature | Description |
|---------|-------------|
| ~~Rich training context~~ | Injects active mesocycle (week, goal, periodization, deload flag), fatigue score + reasons, per-muscle recovery (days since, avg RIR, red/amber/green), full last session (every set with weight/reps/RIR), Big 4 e1RMs + strength level, active injuries, weekly check-in scores |
| ~~Static RP knowledge block~~ | Curated MEV/MAV/MRV definitions, RIR scale, deload criteria, AR overload rules, and recovery timelines baked into the system prompt — eliminates hallucination on core methodology concepts without a retrieval system |
| ~~Safety guardrails~~ | Hard rules: cite logged data before any weight recommendation; redirect injury questions to a sports medicine professional; never abandon mesocycle mid-block; say "I don't know" when data is absent |
| ~~Context summary in header~~ | Chat page shows live context after first message: mesocycle week, fatigue score (color-coded), injury badge |
| ~~Safety disclaimer~~ | Shown below chat header: "AI recommendations are informational. For injury concerns, consult a professional." |
| ~~Suggestion chips~~ | Four quick-start prompts shown before first message: recovery, deload check, last session, weekly focus |

### Post-Session Recap

New finish flow: Complete → RPE → **Recap Modal** → Done → Home

| Feature | Description |
|---------|-------------|
| ~~Session recap modal~~ | Shows session name + duration, PRs hit (gold badge, previously computed and discarded), every exercise with best working set (weight × reps @ RIR), total weight moved |
| ~~PR capture~~ | `api.prs.checkSession()` result was always called but its return value was silently discarded — now captured and displayed in the recap |
| ~~"Get Coach's Take" button~~ | Lazy-loads a 1-2 sentence Ollama coaching observation — not automatic (avoids blocking the UX while model loads) |
| ~~AI recap guardrailed~~ | Model given verified PR count and names, explicitly banned from recounting them (the UI shows them accurately). AI restricted to coaching observations: RIR trend analysis, RPE calibration, one next-session adjustment |

### Remaining Phase 10

| Feature | Status | Description |
|---------|--------|-------------|
| Notifications / Reminders | — | PWA push notifications for workout reminders, rest day alerts, muscle-group nudges ("haven't trained legs in 5 days") |

---

## ✅ Phase 11 — Health Platform Integrations & UX Polish (SHIPPED)

### Google Fit OAuth2 Sync

Body weight from Google Fit → `BodyMeasurement` table. 30-day lookback on first sync, incremental after. Converts kg → lbs based on user unit preference. Token refresh handled automatically via stored refresh token.

| Feature | Description |
|---------|-------------|
| ~~`/api/google-fit/status`~~ | Returns `{connected, last_synced}` from UserProfile |
| ~~`/api/google-fit/auth-url`~~ | Builds Google OAuth2 URL (scope: `fitness.body.read`, access_type: offline) |
| ~~`/api/google-fit/callback`~~ | Handles OAuth redirect from Google; exchanges code for tokens; stores on UserProfile; redirects to `/settings?google_fit=connected` |
| ~~`/api/google-fit/sync`~~ | Aggregates daily weight buckets from Fitness API; skips dates with existing entries; updates `google_fit_last_synced` |
| ~~`/api/google-fit/disconnect`~~ | Clears all 4 token fields from UserProfile |
| ~~Token auto-refresh~~ | `_ensure_valid_token()` checks expiry before every sync; refreshes silently via `refresh_token` grant if within 5 min of expiry |
| ~~4 new UserProfile fields~~ | `google_fit_access_token`, `google_fit_refresh_token`, `google_fit_token_expiry`, `google_fit_last_synced`; migration-safe |
| ~~Settings → Connected Health Apps~~ | Google Fit block: Connect button → OAuth flow → Connected badge + Sync Now + Disconnect + last synced date + import result |
| ~~`googleFit` domain in api.js~~ | `status`, `authUrl`, `sync`, `disconnect` |

**Setup:** Requires `GOOGLE_FIT_CLIENT_ID`, `GOOGLE_FIT_CLIENT_SECRET`, and `APP_BASE_URL` in `/mnt/user/appdata/liftforge/.env`. See `.env.example`.

**Tailscale + Unraid note:** Use `tailscale serve --bg 8443` (not 443 — Unraid web UI occupies 443). Register `https://tower.tailnet.ts.net:8443/api/google-fit/callback` as the redirect URI in Google Cloud Console.

### Samsung Health Passthrough

Samsung Health has no web API. Samsung's app has a built-in "Connect to Google Fit" toggle (Settings → Connected Services → Google Fit). Enabling it auto-syncs Samsung data into Google Fit — connecting Google Fit above then brings it all into LiftForge.

| Feature | Description |
|---------|-------------|
| ~~Settings UI note~~ | Explanation in Connected Health Apps section below the Google Fit block; no backend changes needed |

### UX Bug Fix

| Fix | Description |
|-----|-------------|
| ~~More sheet scroll cutoff~~ | Bottom sheet was using `on:touchmove\|preventDefault` unconditionally, blocking native scroll even though the sheet already has `max-height: 80vh` + `overflow-y: auto`. Now only calls `e.preventDefault()` when dragging downward from `scrollTop === 0` — content scrolls freely, swipe-to-close still works from the top |

---

## Architecture Notes

```
/home/cashbux/liftforge/
  backend/         FastAPI + SQLModel + SQLite
    engine/        meso_builder.py, progression logic
    routers/       15 router files (incl. google_fit.py)
    seed_data.py   108 exercises + 13 splits + landmarks
  frontend/        SvelteKit (static adapter) + Chart.js
    src/routes/    19 pages
  docker-compose.yml
  .env.example     Google Fit + APP_BASE_URL config template
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
| Ollama model | 8B (llama3.1:8b) | Fast on home hardware |
| Nutrition | Separate app | User decision |
| Calorie tracking | Excluded | User decision |
| CSS | Custom, no framework | Apex theme (#0a0a10 bg, #e8365d accent, DM Serif Display) |
