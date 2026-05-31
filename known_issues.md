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
| BUG-C04 | ✅ | Online Visualization: pressing back arrow once after N accelerate clicks undoes all N steps instead of 1 | `_steps_per_second` was computed from `simulation_time_step_s` (physics sub-step, e.g. 10) but used to slice `_live_rows` which holds output rows (1 per second). `_live_rows[:-10]` on a 3-element list = `[]` | Renamed to `_output_rows_per_second`; changed divisor to `output_resolution_s` in all 3 assignment sites (`gui.py` lines 615, 645, 906) and usage site (line 860) | Manual regression: accelerate 3× → back once → 2 live seconds remain |
| BUG-C05 | ✅ | Online Visualization: truck2/truck3 image events before the live-entry time were missing from saved scenario CSV | `_save_online_scenario` built `original_rows` from `timeline.rows` (velocity rows only); event-only rows live in `truck2_image_events()` / `truck3_image_events()` and were never injected into the pre-live `all_rows` list | Added injection loop: for each t2/t3 event at `t <= live_entry_time_s` not already in `all_rows`, inject a dict row with carry-forward leader velocity; sort merged list before `_compress_scenario_rows` (`gui.py`, `_save_online_scenario`) | Manual regression: run scenario with truck events, enter live mode after all events, Save As → confirm events appear in saved CSV |
| BUG-C06 | ✅ | Online Visualization: leader upper status rectangle used blue truck color instead of white/black; no red or black fill for brake states | `_draw_truck` used `status_indicator_style(label_lane, ...)` for all trucks; for leader (label_lane=2) this returns blue-tone fill | Added `leader_status_style(state, command)` in `visualization.py`: white/black (normal), red (red brake), black (FORT/emergency); applied in `_draw_truck` for `label_lane == 2` | Manual regression: verify leader upper rectangle colors in normal, red-brake, and FORT states |
| BUG-C07 | ✅ | Online Visualization: auto-advance used HOLD (zero acceleration) instead of following the original scenario velocity profile | `_schedule_next_frame` always passed `HOLD` to `advance_one_second` | Added `FOLLOW_PROFILE` `LiveLeaderCommand` kind; `advance_one_second` resolves look-ahead target at `current_time + return_to_sim_velocity_s` from `timeline.leader_profile()`; `_leader_acceleration` computes `(target_vel - current_vel) / params.return_to_sim_velocity_s` clamped to `max_acceleration_mps2` / `max_red_deceleration_mps2`; `_schedule_next_frame` now passes `FOLLOW_PROFILE`; `return_to_sim_velocity_s: float = 3.0` added to `SimulationParameters` in `models.py` | Manual regression: start auto-advance from a velocity that differs from the profile — leader should converge gradually, not jump |
| BUG-C08 | ✅ | Online Visualization: Back to Sim button permanently disabled after pressing ← until all live rows gone, then adding new interventions | `_keyboard_back` disables `_back_to_sim_btn` when `_live_rows` becomes empty, but leaves `_live_mode = True`; next call to `_apply_leader_command` hits the `if self._live_mode: return True` short-circuit in `_ensure_live_mode` without re-enabling the button | Added `self._back_to_sim_btn.configure(state=tk.NORMAL)` to the short-circuit path in `_ensure_live_mode` (`gui.py`) | Manual regression: accelerate → back (undo all) → accelerate again → Back to Sim button must be enabled |
| BUG-C09 | ✅ | Online Visualization: FOLLOW_PROFILE velocity convergence was instantaneous (jumped to target in one physics step) instead of gradual | `_leader_acceleration` for `follow_profile` divided by `step_s` (0.1 s) instead of `params.return_to_sim_velocity_s` (3 s), producing `(Δv / 0.1)` — effectively infinite acceleration | Changed divisor to `params.return_to_sim_velocity_s` and added clamp to `±max_acceleration_mps2` / `max_red_deceleration_mps2` in `live_stepper.py` | Manual regression: with velocity mismatch, leader should take ~3 s to converge, not teleport |
| BUG-C10 | ✅ | Online Visualization: leader upper rectangle showed no color change for orange or red brake clicks | `_leader_state` / `_leader_command` only examined final acceleration magnitude, not command kind; both orange and red brake produced `LEADER_DECELERATING` / `"Follow leader profile deceleration"` — neither contains "orange" or "red" | Added `leader_command_kind: str = ""` param to `_leader_state`, `_leader_command`, `_build_output_row` in `simulation.py`; `_step_n` passes `command.kind`; `leader_status_style` updated to use `is_red_status` / `is_orange_status` helpers; FORT checked first for black fill | Manual regression: click Orange Brake → leader rect turns orange; click Red Brake → red; FORT → black; normal → white/black |
| BUG-C11 | ✅ | Online Visualization: legend row missing ID-loss triangle markers; braking info labels on separate row instead of leader control row | No triangle swatches in `_build_legend`; `_build_braking_info_bar` created a standalone frame below the leader row | Added 4 triangle swatch entries to `_build_legend` (Truck2/Truck3 × distance/scenario loss); removed `_build_braking_info_bar` and inlined 4 info labels directly into `leader_row` after a separator (`gui.py`) | Manual regression: legend shows triangles on same row as line swatches; orange/red/loss/resume labels appear to the right of Save As button |

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
