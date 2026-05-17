"""
Program presets — high-level workout style shortcuts that pre-fill the mesocycle wizard.

Each preset includes everything the wizard needs:
  route        "wizard"   → pre-fill split/goal/etc and open wizard at step 4
               "install"  → route directly to library installer (e.g. 5/3/1)
  split_slug   matches a SplitTemplate.slug in the DB (None for install-routed presets)
  published_slug  used when route == "install"
"""

PROGRAM_PRESETS: list[dict] = [
    {
        "key":           "full_body_3day",
        "name":          "3-Day Full Body",
        "description":   "Hit every muscle group 3× per week — great for general fitness",
        "tags":          ["3-day", "general fitness", "balanced", "beginner-friendly"],
        "days_per_week": 3,
        "goal":          "general_fitness",
        "session_minutes": 45,
        "periodization": "standard",
        "num_variants":  3,
        "split_slug":    "full_body_3",
        "route":         "wizard",
        "icon":          "💪",
    },
    {
        "key":           "ab_split",
        "name":          "A/B Split",
        "description":   "Two alternating full-body sessions covering all patterns each week",
        "tags":          ["2-day", "efficient", "full body"],
        "days_per_week": 2,
        "goal":          "general_fitness",
        "session_minutes": 45,
        "periodization": "standard",
        "num_variants":  2,
        "split_slug":    "full_body_2",
        "route":         "wizard",
        "icon":          "🔁",
    },
    {
        "key":           "ppl",
        "name":          "Push / Pull / Legs",
        "description":   "Classic 3-day split — push, pull, and lower body in dedicated sessions",
        "tags":          ["3-day", "hypertrophy", "intermediate"],
        "days_per_week": 3,
        "goal":          "hypertrophy",
        "session_minutes": 60,
        "periodization": "standard",
        "num_variants":  1,
        "split_slug":    "ppl_3",
        "route":         "wizard",
        "icon":          "📊",
    },
    {
        "key":           "upper_lower",
        "name":          "Upper / Lower",
        "description":   "4-day split alternating upper and lower — strength and size",
        "tags":          ["4-day", "strength", "hypertrophy"],
        "days_per_week": 4,
        "goal":          "strength",
        "session_minutes": 60,
        "periodization": "standard",
        "num_variants":  2,
        "split_slug":    "upper_lower_4",
        "route":         "wizard",
        "icon":          "⬆️",
    },
    {
        "key":            "531",
        "name":           "5/3/1",
        "description":    "Jim Wendler's proven strength program — 4 main lifts with BBB volume",
        "tags":           ["4-day", "strength", "barbell", "proven"],
        "days_per_week":  4,
        "goal":           "strength",
        "session_minutes": 60,
        "periodization":  "linear",
        "num_variants":   1,
        "split_slug":     None,
        "published_slug": "531-bbb",
        "route":          "install",
        "icon":           "🏋️",
    },
]
