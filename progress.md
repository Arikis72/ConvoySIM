---
title: ConvoySIM — Progress Log
type: progress
date: 2026-05-30
description: Chronological progress notes for ConvoySIM. Replace STATUS.md snapshot each session; append a dated entry here. Old entries archive to archive/progress_history.md.
tags: [convoysim, progress]
related: ["[[AGENTS]]", "[[STATUS]]", "[[decisions]]"]
---

# ConvoySIM — Progress Log

> See [[AGENTS]] for the session-end update rules. See [[STATUS]] for the current snapshot.
> **Archive rule:** entries older than ~3 months move to `archive/progress_history.md`. Keep only the last ~10 entries in this file.



## 2026-05-31 — Online Visualization: live leader control (REQ-21-14)

Added `Open Online Visualization` button alongside existing `Open Visualization`. Opens `OnlineVisualizationWindow` — a fully standalone new class (no changes to any existing visualization code). New file `src/convoysim/live_stepper.py` provides `LiveSimStepper` (re-simulates silently to current time, then steps 1 second at a time under user-supplied `LiveLeaderCommand`). Supports: Pause/Resume, Accelerate/Decelerate (editable rate), Orange/Red/FORT brake, undo (← keyboard), HOLD (→ keyboard), Back to Sim (discard live rows), Save As (merged scenario CSV auto-loaded into Scenario tab). Default rates from loaded parameters. Scenario saving preserves Trucks 2/3 image events from original; updated leader velocities form dense waypoints in the new file. `_undo_stack` allows arbitrary undo depth. All existing tests pass unchanged (93 run, same 4 failures + 32 errors as pre-existing).

## 2026-05-31 — BUG-003 UI/UX review + new GUI requirements (REQ-21-07 to REQ-21-13)

Reviewed the Agentic_dev_analysis_results.md Phase E gaps for ConvoySIM. Conducted manual UI/UX review of Stage C popup, Bulk Simulation tab, and Cost Weight tab (BUG-003). User ran simulation and reported 7 issues, all implemented and documented.

Changes: (1) Gap chart Y-axis capped at 120% of max gap / 40 m hard limit (`y_max_cap=40.0`). (2) "status/command/violation" label clamped within canvas bounds. (3) Open Visualization / Open Charts buttons disabled on startup — only enabled after a successful run this session. (4) Toggle Legend repacked `before=pane` so legend is always fully visible. (5) Scenario Save/Save As disabled when clean, enabled on edit/insert/delete. (6) Inline warning blocks simulation run when Parameters tab has unsaved changes. (7) Keyboard shortcuts on both Stage C and Bulk visualization windows: ← = −1s, → = +1s, Home = start, End = end.

Documentation: BUG-003 closed as BUG-C03; 7 new REQ IDs (REQ-21-07 to REQ-21-13) added to SimRequirements.md §21 and requirements_traceability.md; TASKS.md updated; STATUS.md replaced. Note: REQ-25-01 (leader resume after comms override) remains frozen by user decision.

Test suite: 93 tests run; 4 failures + 32 errors are pre-existing (missing test fixture files in `Inputs/stage_a_example_inputs/`), not introduced this session.

## 2026-05-29 - Gap arrow distance labels moved above arrow lines

Progress:
- Fixed `gap_arrow_coordinates()` and `orange_trigger_gap_arrow_coordinates()` in `visualization.py`: `label_y` was `y + 12.0` (12 px below the arrow line) but should be `y - 12.0` (12 px above). In Tkinter canvas coordinates y increases downward, so `+12` places text below. The two failing tests (`test_gap_arrow_coordinates_use_follower_front_and_leading_rear`, `test_orange_trigger_gap_arrow_uses_required_gap_from_follower_front`) both asserted `label_y < arrow.y` (above) — they had been red since the arrows were introduced.
- No other changes needed: `_draw_gap()` already uses `arrow.label_y` directly, and `_draw_orange_trigger_gap()` uses `arrow.y + 12.0` when `label_below=True` (intentional, for the Truck 2 orange trigger label) and `arrow.label_y` when `label_below=False` — both now correct.

Validation:
- `python -m unittest discover -s tests -p test_visualization.py -v` — 25/25 passed (2 previously failing tests now pass).

## 2026-05-29 18:10 - FORT latches to full stop and holds

Progress:
- Changed Truck #1 FORT from a single-step event to a permanent latch.
- Once `FORT activated` fires, `truck1_fort_latched` is set to True and never reset.
- Emergency deceleration is applied every simulation step until velocity reaches 0; `_emergency_deceleration()` returns 0 when stopped, holding the truck at rest.
- The leader profile velocity schedule is entirely ignored after FORT — even if the scenario specifies a non-zero velocity at a later time.
- Added `test_truck1_fort_latches_to_full_stop_and_does_not_resume` in `test_simulation.py` — self-contained, no external files required.
- Updated `ConvoyLogic.md` to document Truck #1 FORT vs Truck #2/3 FORT separately, including the latch-to-stop and no-resume behaviour.
- Log message updated to say "Emergency braking until stopped." to match the new semantics.

Validation:
- New test passes: `python -m unittest tests.test_simulation.SimulationTest.test_truck1_fort_latches_to_full_stop_and_does_not_resume -v`
- Scenario file `4_3T_hB_bG_idL2fv_1ES.csv` simulation output verified: FORT at 110s → velocity 0 at 111s → held stopped through 120s.

## 2026-05-29 17:42 - Fixed FORT event activation for Truck #1

Progress:
- Fixed bug where FORT (emergency deceleration) events specified in the Truck1_Event column of scenario CSV files were not being applied during simulation.
- Issue: `scenario_timeline.py` correctly parsed FORT events from the CSV, but `simulation.py` never queried the `truck1_events` dictionary.
- Solution: Added extraction of `truck1_events` from timeline and FORT detection logic in the acceleration calculation loop.
- Modified `_build_output_row()` function to accept `truck1_in_fort` parameter and set appropriate truck1_state and truck1_command values when FORT is active.
- FORT activation now correctly applies emergency deceleration (-8.0 mps2 in test scenario) and logs the event.
- Verified with the scenario file `4_3T_hB_bG_idL2fv_1ES.csv` which has FORT event at 115s.
- Truck #1 velocity correctly drops from 17 kph to ~3 kph during FORT, then resumes following the leader profile after the emergency event.

Validation:
- Manual simulation test with real scenario file passed: FORT event logged, correct acceleration applied, state/command set correctly.
- Simulation output shows truck1_state="FORT_EMERGENCY_DECEL" and truck1_command="FORT emergency deceleration" at 115s.

Next focus:
- Run full test suite to ensure no regressions were introduced.
- Verify FORT events work correctly with other scenario configurations (2-truck, different parameters).

## 2026-05-27 17:58 - Project memory refresh after Bulk Simulation updates

Progress:
- Refreshed project memory after the Phase B Bulk Simulation implementation and usability pass.
- Current Bulk Simulation behavior is documented in `SimRequirements.md`, `README.md`, `STATUS.md`, `TASKS.md`, `CHANGELOG.md`, and this file.
- Added decision records for the `Accidents` cost function and independent per-run bulk visualization windows.
- No extra scripts, research, analytics, or voice-guide files were needed for this work.

Validation:
- Latest full validation remains: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (80 tests passed).
- Latest focused GUI/optimization validation remains: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_optimization -v"` (15 tests passed).

Next focus:
- Manually click through the Bulk Simulation GUI, especially progress/cancel, chart selection, red row highlighting, and multiple independent visualization windows.
- Add future Stage B cost functions or multi-parameter optimization only after the single-parameter workflow is reviewed.

## 2026-05-27 16:56 - Stage B Bulk simulations v1

Progress:
- Added approved Stage B Bulk simulations requirements to project memory.
- Added reusable bulk-run logic for inclusive min/max/step parameter ranges, selected scenario CSVs, per-run output CSV files, and `Bulk_Results.csv`.
- Added `Red braking count` as the first formal cost function, counted per follower truck and totaled for charting.
- Added a GUI `Bulk simulations` button and Bulk Simulation tab with scenario selection, cost-function selection, progress, cancel, cost chart, and contributor table.
- Added starter predefined scenarios under `Bulk_Scenarios`.

Validation:
- Targeted optimization validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_optimization -v"` (4 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (78 tests passed).
- Syntax validation passed: `python -m py_compile src\convoysim\optimization.py src\convoysim\gui.py tests\test_optimization.py`.
- Bulk smoke check passed with `Bulk_Scenarios/Nominal.csv` and `Bulk_Scenarios/Truck2_Loss.csv`.

Next focus:
- Manually review the Bulk Simulation GUI workflow.
- Add additional Stage B cost functions after the red-braking workflow is approved.

## 2026-05-27 17:13 - Bulk Simulation usability refinements

Progress:
- Added `Select all` and `Unselect all` controls next to the Bulk Simulation scenario list.
- Added a chart legend showing the active cost function.
- Renamed failed bulk-run output detail to `Failure_Reason` in `Bulk_Results.csv` and the GUI result table.
- Added double-click visualization opening for completed bulk-run output rows, with a header showing scenario, parameter value, and cost function.
- Remembered the last selected Bulk Simulation scenarios folder in `convoysim.ini`.
- Refined Bulk Simulation controls so min/max/step sit beside the parameter selector, the progress bar is to their right, and Start/Cancel are centered.
- Added a read-only Bulk Simulation Default field showing the selected parameter's current value from the loaded parameters CSV.
- Added `Accidents` as a selectable Bulk Simulation cost function, counted as accident intervals per follower truck.
- Updated Bulk chart clicks to show all scenarios for the clicked parameter value and highlight cost-triggering rows in red text.
- Changed completed Bulk result double-clicks to open a new independent visualization window each time for side-by-side comparison.
- Restored missing Stage A scenario fixture CSV files referenced by the existing test suite.

Validation:
- Targeted optimization validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_optimization -v"` (5 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (79 tests passed).
- Syntax validation passed: `python -m py_compile src\convoysim\optimization.py src\convoysim\gui.py tests\test_optimization.py`.
- Focused GUI-related validation passed after double-click visualization wiring: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_optimization tests.test_gui_helpers -v"` (14 tests passed).
- Full validation passed after double-click visualization wiring: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (79 tests passed).
- Focused config/GUI validation passed after bulk layout and INI persistence updates: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_run_config tests.test_gui_helpers -v"` (13 tests passed).
- Full validation passed after bulk layout and INI persistence updates: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (79 tests passed).
- Focused GUI validation passed after adding the selected-parameter default field: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers -v"` (9 tests passed).
- Full validation passed after adding the selected-parameter default field: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (79 tests passed).
- Targeted optimization validation passed after adding the accident cost function: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_optimization -v"` (6 tests passed).
- Full validation passed after adding the accident cost function: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (80 tests passed).
- Focused validation passed after changing Bulk chart-click table behavior: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_optimization -v"` (15 tests passed).
- Full validation passed after changing Bulk chart-click table behavior: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (80 tests passed).
- Focused validation passed after adding independent bulk visualization windows: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_optimization -v"` (15 tests passed).
- Full validation passed after adding independent bulk visualization windows: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (80 tests passed).

## 2026-05-23 21:37 - Stage A/B/C baseline and Stage C loss behavior refinement

Progress:
- Stage A baseline simulation is runnable from CLI and GUI with timestamped output/log/chart files.
- Stage A output CSV now includes complete truck review data: positions, velocities, accelerations, Truck #1 state/command, follower gaps, follower states/commands, tracking status, communication, violations, and stop reasons.
- Stage B has a first explicit CSV sweep optimizer with temporary deterministic scoring.
- Stage C visualization is a popup replay driven by simulation rows, with truck rectangles, gap arrows, status/command bubbles, synchronized gap/velocity charts, chart visibility checkboxes, playback speed memory, and target markers.
- Image-identification loss behavior now targets the frozen rear end of the followed truck. The follower uses target-stop braking to stop there.
- If identification does not resume within 30 seconds after stopping at the frozen target, the follower enters `SAFETY_LOCK`.
- Stage C lost-target triangle now marks the same frozen rear point used by the controller.

Validation:
- Latest full validation before this documentation refresh: `set PYTHONPATH=src&& python -m unittest discover -s tests -v`, 54 tests passed.
- This entry is documentation-only; no additional code validation was required.

Next focus:
- Manually review the Stage C popup layout and marker placement in the GUI.
- Define the formal Stage B cost function.
- Expand Stage B optimization from explicit sweep rows to generated parameter ranges.
- Resolve remaining communication, leader-resume, and detailed safety-lock behavior questions in `SimRequirements.md`.

## 2026-05-26 17:09 - GUI Help and Tabs implementation

Progress:
- Added a Stage C visualization Help button that opens state-machine tables generated from section 17 of `SimRequirements.md`.
- Merged state meanings and commands into one Help table and kept transitions as a separate Help table.
- Added editable `Parameters`, read-only `Scenario`, `Output Table`, and sorted/styled `Log` tabs to the main GUI.
- Added colored header strips inside tabs for clear visual differentiation.
- Updated the Stage C visualization so lost-target triangles use the affected truck color and orange/red braking distances are displayed at the top right.

Validation:
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_visualization -v"`.
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (58 tests passed).
- Syntax validation passed: `cmd /c "python -m py_compile src\convoysim\gui_helpers.py src\convoysim\gui.py src\convoysim\visualization.py tests\test_gui_helpers.py tests\test_visualization.py"`.

Next focus:
- Manually click through the Tk GUI tabs and visualization popup layout.

## 2026-05-26 17:59 - GUI visual refinement pass

Progress:
- Added color swatches to the notebook tab selectors and kept colored page headers as a reliable platform fallback.
- Improved table presentation with content-based column widths, centered parameter value/unit fields, centered scenario data columns except notes, and alternating row backgrounds.
- Grouped output table columns by truck, wrapped long headers, and formatted numeric display values to one decimal.
- Disabled `Open Visualization` and `Open Charts` until results exist, and cleared stale output/log views when input files change.
- Updated Stage C visualization with truck-colored wheels, stacked orange/red distance labels, centered chart x-axis labels, and no redundant leader status bubble.

Validation:
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_visualization -v"` (23 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (61 tests passed).
- Syntax validation passed: `cmd /c "python -m py_compile src\convoysim\gui_helpers.py src\convoysim\gui.py src\convoysim\visualization.py tests\test_gui_helpers.py tests\test_visualization.py"`.

Next focus:
- Manually review the Tk layout in the GUI.

## 2026-05-26 18:46 - Scenario tab editor

Progress:
- Converted the Scenario tab from read-only viewing to editable CSV review.
- Added Scenario tab Save, Save As, Insert Row, and Delete Row controls.
- Added inline cell editing and controlled dropdowns for `Truck2_Image_Event` and `Truck3_Image_Event` values.
- Scenario edits and row changes clear stale simulation result views until the user runs the simulation again.

Validation:
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers -v"` (7 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (62 tests passed).
- Syntax validation passed: `cmd /c "python -m py_compile src\convoysim\gui_helpers.py src\convoysim\gui.py tests\test_gui_helpers.py tests\test_scenario_timeline.py"`.
- Updated `tests/test_scenario_timeline.py` to match the current example scenario row count.

Next focus:
- Manually review Scenario tab editing, insert/delete, save, and save-as in the Tk GUI.

## 2026-05-26 18:57 - Parameter filter and grouping

Progress:
- Added a Parameters tab substring filter and clear-filter button.
- Added visual parameter grouping by sub-category.
- Kept group rows visual-only so parameter Save and Save As still write the original CSV shape.

Validation:
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers -v"` (8 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (63 tests passed).
- Syntax validation passed: `cmd /c "python -m py_compile src\convoysim\gui_helpers.py src\convoysim\gui.py tests\test_gui_helpers.py tests\test_scenario_timeline.py tests\test_charts.py"`.
- Updated brittle example-scenario and chart assertions so full validation remains stable when editable example scenarios change.

Next focus:
- Manually review Parameters tab filtering and grouping in the Tk GUI.

## 2026-05-26 20:20 - GUI inline status line

Progress:
- Added a status line to the main button row.
- Replaced routine GUI success, warning, and error message boxes with inline status messages.
- Save/run/open-chart/help feedback no longer requires clicking OK.

Validation:
- Targeted GUI helper validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers -v"` (8 tests passed).
- Syntax validation passed: `cmd /c "python -m py_compile src\convoysim\gui.py"`.

Next focus:
- Manually review status-line behavior in the Tk GUI.

## 2026-05-26 21:53 - Project memory audit

Progress:
- Verified recent GUI requirements against project memory after repeated requirement clarifications.
- Expanded `SimRequirements.md` Stage A GUI requirements to include parameter filtering/grouping, editable scenario save/save-as/insert/delete behavior, image-event dropdowns, stale-result clearing, result-button availability, output/log review behavior, and inline status feedback.
- Marked the documentation audit complete in `TASKS.md`.
- Added decisions documenting GUI-only CSV-preserving table enhancements and non-modal inline status feedback.

Validation:
- Documentation-only update; no code validation required.

Next focus:
- Manually review the Tk GUI workflows for Parameters filtering/grouping, Scenario editing, inline status feedback, and Stage C popup layout.

## 2026-05-26 21:58 - Requirement tracking workflow

Progress:
- Added an explicit project rule that every new user requirement must be documented and tracked.
- Updated `AGENTS.md` and `TASKS.md` so future work must pair new requirements with source-of-truth documentation and task tracking.
- Added a README note describing which project-memory file owns each requirement-tracking role.
- Added a decision documenting the requirement-intake workflow.

Validation:
- Documentation-only update; no code validation required.

Next focus:
- Use the requirement-tracking workflow for every future change request before implementation is considered complete.

## 2026-05-27 13:56 - Draggable Stage C chart divider

Progress:
- Documented and tracked the new requirement for a draggable horizontal divider between the Stage C truck visualization and chart area.
- Added a vertical paned layout to the Stage C popup so dragging the divider changes chart area height and visually zooms charts along the y axis.
- Persisted the divider position in `convoysim.ini` through the existing run configuration.
- Added a decision documenting the persisted pane-divider approach.
- Updated README, status, task, changelog, and focused run-config tests.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\run_config.py src\convoysim\gui.py src\convoysim\visualization.py tests\test_run_config.py tests\test_visualization.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_run_config tests.test_visualization -v"` (20 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (64 tests passed).

Next focus:
- Manually verify the Stage C popup divider drag behavior in Tk on Windows.

## 2026-05-27 14:03 - Stage C divider visibility fix

Progress:
- Fixed the divider layout regression that could hide the truck visualization.
- Replaced the fragile themed pane with a non-collapsible paned layout and minimum truck/chart pane sizes.
- Made the truck canvas redraw using the actual pane height so trucks remain visible when the divider is moved.
- Tightened INI loading so very small saved divider positions are clamped to a visible truck-pane height.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\run_config.py src\convoysim\gui.py src\convoysim\visualization.py tests\test_run_config.py tests\test_visualization.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_run_config tests.test_visualization -v"` (21 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (65 tests passed).

Next focus:
- Manually confirm the Stage C popup shows the truck visualization immediately and the divider still resizes the charts on Windows.

## 2026-05-27 14:12 - State Machine Help label alignment

Progress:
- Verified that the State Machine Help window covered section 17 states and transitions but did not explain visualization tracking/status and command/action/violation labels.
- Added `SimRequirements.md` section 17.4 for visualization help labels, including `Image identification loss`.
- Updated the State Machine Help parser and GUI window to show visualization labels in a dedicated table.
- Updated README, status, task, changelog, and focused helper tests.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\gui_helpers.py src\convoysim\gui.py src\convoysim\visualization.py tests\test_gui_helpers.py tests\test_visualization.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_visualization -v"` (25 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (65 tests passed).
- Direct requirements-help check confirmed `Image identification loss` is loaded from `SimRequirements.md` into visualization Help labels.

Next focus:
- Manually verify the State Machine Help popup shows the new `Visualization Labels` table in the Tk GUI.

## 2026-05-27 14:41 - Visual Help Sync

Progress:
- Documented and tracked the requirement to correlate Stage C visualization colors, chart formats, legends, and State Machine Help wording.
- Added searchable Help tables and ensured Help labels include exact visualization wording such as `Hold stopped` and `Image identification loss`.
- Updated Stage C truck bodies to use fixed identity colors: Truck #1 black, Truck #2 blue, and Truck #3 orange.
- Added upper status rectangles above trucks for normal, image-lost, orange-braking, and red-braking/violation states.
- Split the combined gap chart into `Gap1-2` and `Gap2-3`, with chart segment styling matched to the truck/status visualization rules.
- Updated the Stage C legend and README/changelog/status/decisions documentation.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\gui_helpers.py src\convoysim\gui.py src\convoysim\visualization.py tests\test_gui_helpers.py tests\test_visualization.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_visualization -v"` (28 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (68 tests passed).
- Direct requirements-help check confirmed `Hold stopped` and `Image identification loss` are loaded from `SimRequirements.md` into visualization Help labels.

Next focus:
- Manually verify the Stage C popup layout, Help search field, split gap charts, status rectangles, and legend readability.

## 2026-05-27 14:52 - Stage C chart x-axis time ticks

Progress:
- Documented and tracked the requirement for time tick marks and numeric labels along Stage C popup chart x axes.
- Added clean time tick helpers for popup charts.
- Updated Stage C charts to draw x-axis tick marks, vertical grid lines, and numeric time labels.
- Updated README, status, task, and changelog documentation.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\visualization.py tests\test_visualization.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_visualization -v"` (20 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (69 tests passed).

Next focus:
- Manually verify x-axis time tick readability in the Stage C popup charts.

## 2026-05-27 14:58 - Follower-only max velocity

Progress:
- Documented and tracked the requirement that `Max velocity` applies only to follower trucks.
- Removed the `Max velocity` cap from Truck #1 leader motion while preserving it for Truck #2 and Truck #3.
- Added a regression test proving the leader can exceed `Max velocity` while followers stay capped.
- Updated README, status, decisions, changelog, and task documentation.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\simulation.py tests\test_simulation.py`.
- Focused simulation validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_simulation -v"` (12 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (70 tests passed).

Next focus:
- Manually review a scenario where Truck #1 exceeds `Max velocity` and follower trucks remain capped.

## 2026-05-27 15:06 - Colored GUI action buttons

Progress:
- Documented and tracked the requirement for colored GUI buttons.
- Added role-based colored action buttons in the main GUI, Parameters tab, Scenario tab, visualization popup, and Help popup.
- Left all file Browse buttons on the default style.
- Updated README, status, task, and changelog documentation.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\gui.py`.
- Focused GUI helper validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers -v"` (9 tests passed).
- Full test suite passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (70 tests passed).

Next focus:
- Manually verify button colors and contrast in the Tk GUI on Windows.

## 2026-05-27 15:14 - Scenario name and loss marker refinements

Progress:
- Documented and tracked the new scenario-name, Load scenario, loaded-header, x-axis tick, triangle-source, and distance-label requirements.
- Added a persisted Scenario name field and Load scenario button, and displayed the loaded scenario in the main GUI and Stage C popup.
- Changed Stage C chart x axes to draw 1-second tick marks with numeric labels every 10 seconds.
- Added image-identification loss source tracking to output rows so Stage C can show scenario-driven loss with an empty triangle and distance-threshold loss with a filled triangle.
- Added image-identification loss and resume distance values below orange/red distances in the Stage C upper-right labels.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\simulation.py src\convoysim\visualization.py src\convoysim\gui.py src\convoysim\run_config.py src\convoysim\gui_helpers.py tests\test_simulation.py tests\test_visualization.py tests\test_run_config.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_run_config tests.test_simulation tests.test_visualization -v"` (38 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (72 tests passed).

Next focus:
- Manually review the Scenario name / Load scenario workflow and Stage C marker appearance in the Tk GUI.

## 2026-05-27 15:40 - Lost-target braking and chart placement refinements

Progress:
- Documented and tracked the updated lost-target braking rule.
- Replaced exact lost-target stop acceleration with thresholded loss braking: hold current velocity outside orange distance, orange brake at orange distance, and red brake if the stop target is already inside orange distance.
- Changed Stage C popup chart y-axis tick labels to use zero decimal places.
- Moved Stage C gap arrows and values to the top of the upper truck status rectangles.
- Added focused regression coverage for thresholded loss braking, integer y-axis labels, and upper-status gap-arrow placement.

Validation:
- Focused validation passed: `python -m py_compile src\convoysim\simulation.py src\convoysim\visualization.py tests\test_simulation.py tests\test_visualization.py`; `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_simulation tests.test_visualization -v"` (35 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (74 tests passed).

Next focus:
- Manually review Stage C arrow placement and loss-braking behavior in the Tk visualization.

## 2026-05-27 15:50 - Scenario loader reversal

Progress:
- Reverted the separate Scenario name field and Load scenario button.
- Restored Scenario Browse as the only scenario-loading control.
- Kept selected-scenario presentation by deriving the displayed name from the selected scenario file path in the main GUI and Stage C popup.
- Removed separate scenario-name persistence and returned timestamped output/log/chart filenames to the selected scenario file stem.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\gui.py src\convoysim\run_config.py tests\test_run_config.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_run_config -v"` (4 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (73 tests passed).

Next focus:
- Manually verify the Scenario Browse workflow and selected-scenario header in the Tk GUI.

## 2026-05-27 16:02 - Distance-loss resume during target approach

Progress:
- Documented and tracked the clarified distance-loss recovery behavior.
- Restored target-stop braking so loss targets are approached with deceleration intended to arrive at 0 velocity.
- Distance-caused image loss now resumes tracking when the live gap reaches resume distance during the approach, even when the `Resume by distance` option is off.
- If the follower stops at the frozen target while the live gap is still greater than resume distance, it remains stopped under loss behavior.
- Existing Stage C triangle behavior clears naturally when tracking resumes because output rows no longer report `Lost`.

Validation:
- Focused simulation validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_simulation -v"` (14 tests passed).
- Syntax validation passed: `python -m py_compile src\convoysim\simulation.py src\convoysim\visualization.py tests\test_simulation.py tests\test_visualization.py`.
- Focused simulation/visualization validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_simulation tests.test_visualization -v"` (36 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (74 tests passed).

Next focus:
- Manually review a distance-loss scenario in the Tk visualization to confirm the filled triangle disappears when live tracking resumes.

## 2026-05-27 16:22 - Exact loss target visualization

Progress:
- Documented and tracked the requirement to show exact loss-target triangles and reduce Stage C road-view overlap.
- Added frozen loss-target rear columns to simulation output for Truck #2 and Truck #3.
- Updated Stage C lost-target markers to use the explicit output target when available instead of reconstructing the target from sampled replay rows.
- Added 10 m distance ticks below the Stage C road line.
- Reduced the Stage C main truck rectangle height by 25%.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\simulation.py src\convoysim\visualization.py src\convoysim\gui_helpers.py tests\test_simulation.py tests\test_visualization.py tests\test_gui_helpers.py`.
- Focused simulation/visualization/GUI-helper validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_simulation tests.test_visualization tests.test_gui_helpers -v"` (47 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (76 tests passed).

## 2026-05-28 08:58 - Bulk multi-cost results

Progress:
- Documented and tracked multi-cost Bulk Simulation selection.
- Replaced the Bulk cost-function dropdown with a selectable list and Select all / Unselect all controls.
- Bulk runs now compute all selected cost functions from the same simulation outputs.
- Bulk results now open in a separate popup with all cost columns in the table and one chart line per selected cost function.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\optimization.py src\convoysim\gui.py tests\test_optimization.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_optimization -v"` (7 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (81 tests passed).

## 2026-05-28 11:12 - Bulk weighted cost scoring

Progress:
- Added `CostFunctionWeights.csv` with default weights for current Bulk cost functions.
- Added cost-function weights loading and validation.
- Replaced the generic `Cost_Value` output with `Total_Weighted_Cost`.
- Added a browseable GUI path for selecting a cost weights CSV.
- Added a `Total weighted cost` line to the Bulk Simulation results chart.
- Split the main GUI Input and Output Files area into two columns.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\optimization.py src\convoysim\gui.py src\convoysim\run_config.py tests\test_optimization.py tests\test_run_config.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_optimization tests.test_run_config -v"` (14 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (84 tests passed).

## 2026-05-28 12:14 - Convoy logic and chart update

Progress:
- Added orange mode, TimeHeadway, emergency deceleration, default 8 m start gap, and `FORT activated` scenario support.
- Implemented orange braking to a 75% entry-speed target, continuous orange trigger gaps, red braking to zero, FORT emergency deceleration, and revised first-start/resume rules.
- Added orange-trigger-gap output columns and Stage C required-gap arrows.
- Added the Cost Weight tab, separate Bulk weighted-cost chart, and Bulk results reopen button.
- Updated example/default input paths to `Inputs/...`.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\models.py src\convoysim\parameters.py src\convoysim\scenario_timeline.py src\convoysim\simulation.py src\convoysim\visualization.py src\convoysim\gui_helpers.py src\convoysim\gui.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_simulation tests.test_visualization tests.test_gui_helpers -v"` (52 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (90 tests passed).

## 2026-05-28 12:29 - Convoy logic summary document

Progress:
- Added `ConvoyLogic.md` as a living, user-facing summary of current convoy behavior.
- Documented orange/red/FORT/start/loss/communication priority logic and relevant output/visualization fields.

Validation:
- Documentation-only update; no code validation was required.

## 2026-05-28 13:03 - Bulk chart and orange-arrow refinements

Progress:
- Moved Bulk chart legends to reserved top-right space outside the plotted data area.
- Added chart titles, larger chart spacing, and JPG save buttons for the per-cost and weighted charts.
- Formatted whole-number chart labels as plain integers, including weighted totals.
- Auto-resized Bulk result table columns to match popup width and wrapped long headers.
- Separated Stage C orange-trigger arrows, moved the Truck #1-to-Truck #2 required-gap label below its arrow, and removed the `Req` prefix.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\gui.py src\convoysim\visualization.py tests\test_gui_helpers.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers tests.test_visualization -v"` (35 tests passed).
- Full validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest discover -s tests -v"` (91 tests passed).

## 2026-05-28 13:10 - Bulk chart point selection

Progress:
- Added persistent highlight rings for the selected point on Bulk per-cost and weighted charts.
- Preserved table filtering and red-row highlighting after chart point selection.

Validation:
- Syntax validation passed: `python -m py_compile src\convoysim\gui.py tests\test_gui_helpers.py`.
- Focused validation passed: `cmd /c "set PYTHONPATH=src&& python -m unittest tests.test_gui_helpers -v"` (10 tests passed).
