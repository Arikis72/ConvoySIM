---
title: ConvoySIM — Known Issues
type: known-issues
date: 2026-05-30
description: Open bugs, debug notes, and regression guards for ConvoySIM. Every bug gets a BUG-ID. Closed bugs stay here as regression guards — do not delete them.
tags: [convoysim, bugs, regression, debugging]
related: ["[[AGENTS]]", "[[requirements_traceability]]", "[[test_strategy]]"]
---

# ConvoySIM — Known Issues

> See [[AGENTS]] §7–§8 for the debugging and fix-validation workflow.
> **Closed bugs stay here as regression guards — never delete them.**
> Statuses: 🔴 open · 🟡 in-progress · ✅ closed (regression guard active)

---

## Open issues

| BUG-ID | Status | Symptom | Root cause | Affected area | Linked REQ |
|--------|:------:|---------|------------|--------------|-----------|
| BUG-001 | 🔴 | Leader resume behavior after communication override is undefined — not yet implemented | Behavior is still an open question in SimRequirements.md §25 | `simulation.py` — communication logic | REQ-12, REQ-25 |
| BUG-002 | 🔴 | True pause/stop controls do not interrupt an in-progress Stage A simulation run | Stage A execution is synchronous; Stage C plays back completed rows only | `gui.py`, `simulation.py` | REQ-25 |

---

## Closed issues (regression guards)

| BUG-ID | Status | Symptom | Root cause | Fix | Regression guard |
|--------|:------:|---------|------------|-----|-----------------|
| BUG-C01 | ✅ | Gap arrow distance labels appeared below arrow lines instead of above | `label_y` used `y + 12.0` (downward in Tkinter coords) instead of `y - 12.0` | Fixed `gap_arrow_coordinates()` and `orange_trigger_gap_arrow_coordinates()` in `visualization.py` | `test_gap_arrow_coordinates_use_follower_front_and_leading_rear`, `test_orange_trigger_gap_arrow_uses_required_gap_from_follower_front` in `tests/test_visualization.py` |
| BUG-C02 | ✅ | Truck #1 FORT fired once then allowed leader to resume from velocity schedule | FORT was implemented as a single-step event | Changed to permanent latch: `truck1_fort_latched` never reset after trigger; leader profile ignored after FORT | `test_truck1_fort_latches_to_full_stop_and_does_not_resume` in `tests/test_simulation.py` |
| BUG-C03 | ✅ | Stage C popup, Bulk Simulation tab, Cost Weight tab — 7 UI/UX issues found in manual review (2026-05-31) | No prior UI/UX review; layout and state-management gaps | (1) Gap chart Y-axis capped at 120%/40m — `y_max_cap=40.0` on all gap charts; (2) status/command label clamped in `_draw_origin_labels`; (3) view buttons start disabled — removed `_results_available=True` from `_load_previous_run_files`; (4) legend repacked `before=pane`; (5) scenario Save/Save As dirty-state tracking; (6) parameters dirty warning blocks run; (7) keyboard shortcuts ←/→/Home/End on both popup windows | REQ-21-07 through REQ-21-13 implemented; manual review confirmed fixes |

---

## Debugging playbook

When a test fails or unexpected behavior appears:

1. **Isolate:** run the specific failing test with `-v` to see the exact assertion.
2. **Read the traceback** in full — identify the exact line and variable values.
3. **Trace the root cause** — don't patch the symptom; find why the value is wrong.
4. **Record here** as a BUG-ID before fixing (even if you fix it immediately).
5. **Fix + re-run** the specific test and the full suite.
6. **Add regression guard** — the test that would have caught this bug must exist.
7. **Update** the BUG entry to ✅ with the fix and guard details.

Common pitfalls:
- Tkinter canvas: y increases **downward** — `y + N` moves down, `y - N` moves up.
- `PYTHONPATH` must be set to `src` for all test runs and imports.
- `convoysim.ini` state can persist between test runs — if tests act strangely, check for stale INI values.
- Braking-table fallback emits a warning to stderr — this is expected and not an error.
