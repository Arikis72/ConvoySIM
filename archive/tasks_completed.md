---
title: ConvoySIM — Completed Tasks Archive
type: archive
date: 2026-05-30
description: Completed tasks archived from TASKS.md on 2026-05-30. Preserved for historical reference.
tags: [convoysim, archive, tasks]
related: ["[[TASKS]]"]
---

# ConvoySIM — Completed Tasks Archive

> Archived from `TASKS.md` on 2026-05-30. See [[TASKS]] for current open tasks.

## Completed tasks (archived 2026-05-31, session 2)

- [x] Fix Online Visualization back-step metric — `_steps_per_second` → `_output_rows_per_second` using `output_resolution_s` (BUG-C04, REQ-21-15).
- [x] Fix Online Visualization Save As missing pre-live truck2/truck3 events — inject event-only rows before compression (BUG-C05, REQ-21-16).
- [x] Fix leader upper rectangle colors — `leader_status_style()` with orange/red/FORT/normal states; `leader_command_kind` propagated through `_build_output_row` (BUG-C06, BUG-C10, REQ-21-17).
- [x] Implement FOLLOW_PROFILE auto-advance with `return_to_sim_velocity_s` look-ahead and gradual velocity convergence (BUG-C07, BUG-C09, REQ-21-18).
- [x] Fix Back to Sim button permanently disabled after undo-all + re-intervention (BUG-C08, REQ-21-19).
- [x] Add ID-loss triangle swatches to legend and move braking info labels into leader row (BUG-C11, REQ-21-20, REQ-21-21).
- [x] Fix `CLAUDE.md` to require reading `AGENTS.md` with NO line limit — prevents partial reads that caused documentation to be skipped mid-session.

## Completed tasks (archived 2026-05-31)

- [x] Complete manual UI/UX review: Stage C popup, Bulk Simulation tab, Cost Weight tab (BUG-003). User ran simulation 2026-05-31; 7 issues identified and fixed; tracked as REQ-21-07 through REQ-21-13; BUG-003 closed as BUG-C03 in `known_issues.md`.
- [x] Add unsaved parameters warning before running simulation (REQ-21-12). Inline status warning blocks run when `_parameters_dirty` is True.
- [x] Add keyboard shortcuts to Stage C and Bulk visualization popups: ← back 1s, → forward 1s, Home = start, End = end (REQ-21-13).

## Completed tasks (archived 2026-05-30)

- [x] Created base Markdown documentation files.
- [x] Created base Cursor rules files.
- [x] Defined the initial Python project structure.
- [x] Defined initial simulation entities for parameters, initial conditions, leader profile, validation messages, and motion state.
- [x] Defined the first validation strategy for parameters, initial conditions, and leader profile feasibility.
- [x] Created the first minimal runnable simulation skeleton.
- [x] Added basic syntax/import validation path.
- [x] Added initial test cases based on unambiguous requirements.
- [x] Aligned requirements filename references to `SimRequirements.md`.
- [x] Prepared Stage A example input CSV files.
- [x] Drafted merged scenario timeline CSV format for user approval.
- [x] Defined current Stage A input/output CSV formats.
- [x] Removed superseded separate leader-profile and image-loss event example CSV files.
- [x] Implemented `scenario_timeline.csv` loader.
- [x] Implemented example `parameters.csv` loader.
- [x] Created first runnable basic Stage A simulation command.
- [x] Generated first basic Stage A output CSV.
- [x] Implemented braking-distance table loading and interpolation.
- [x] Integrated braking-table deceleration into basic orange/red follower braking.
- [x] Added image resume timeout stop reason reporting.
- [x] Added Stage A stop-reason columns to basic output CSV.
- [x] Implemented basic communication ON/OFF loss stop requests.
- [x] Added Stage A communication message/status columns to basic output CSV.
- [x] Added actual/measured gap and relative velocity columns to output CSV.
- [x] Added simulation log CSV output.
- [x] Added dependency-free Stage A HTML chart report.
- [x] Improved Stage A chart axis labels and tick values.
- [x] Added Stage A chart dotted loss segments and expanded legends.
- [x] Added Stage A chart bold orange-braking and double-bold red-braking segments.
- [x] Moved Stage A chart legends to the right of charts.
- [x] Added Stage A INI file remembering previous run files.
- [x] Added GUI startup loading for remembered previous run output/log files.
- [x] Added scenario-name and timestamp based Stage A output filenames.
- [x] Added basic Tk Stage A GUI for file selection, run, output table, logs, and chart opening.
- [x] Added Stage C straight-line convoy visualization tab.
- [x] Added Stage C play, pause, stop, step, and horizontal time scrubber controls.
- [x] Added Stage C status styling for tracking loss, braking, communication, and violations.
- [x] Reduced Stage C label overlap with separate vertical label lanes.
- [x] Moved Stage C velocity labels inside truck rectangles and simplified gap labels.
- [x] Added Stage C status/command text bubbles.
- [x] Added Stage C playback speed slider from `x0.6` to `x2.0`.
- [x] Added Stage C visualization legend toggle.
- [x] Moved Stage C playback buttons into the Visualization tab.
- [x] Refreshed Stage A output filenames when the scenario input file changes.
- [x] Added deterministic communication sent/retried/approved/failed fallback status progression.
- [x] Added warning/log output for braking-table fallback cases.
- [x] Added first Stage B parameter sweep optimizer.
- [x] Added Stage B example sweep CSV and ranked optimization output.
- [x] Moved Stage C visualization into a popup window launched from the GUI.
- [x] Moved Stage C gap arrows and values between the truck rectangles.
- [x] Added Stage C bottom legend panel with toggle behavior.
- [x] Added Stage C embedded gap chart with synchronized vertical playback marker.
- [x] Added Stage C lost-identification target triangle markers.
- [x] Refined Stage C target markers to sit on the road line without text labels.
- [x] Refined Stage C gap arrows to sit at the truck rectangle top edge.
- [x] Replaced Stage C playback button text with compact playback symbols.
- [x] Added `Resume by distance` parameter with default `No`.
- [x] Gated distance-based image-identification resume behind `Resume by distance`.
- [x] Added Stage C popup velocity chart below the gap chart.
- [x] Added numeric y-axis ticks to Stage C popup charts.
- [x] Added Stage C popup chart visibility checkboxes persisted in `convoysim.ini`.
- [x] Matched Stage C popup chart dotted loss and braking-width line styles to the HTML charts.
- [x] Updated Stage C bottom legend samples to match chart colors, dotted lines, and line widths.
- [x] Rotated Stage C popup chart y-axis labels.
- [x] Aligned the Stage C time scrubber with the popup chart plot width.
- [x] Changed Stage C playback speed range to start at `x0.3` and persisted the selected speed in `convoysim.ini`.
- [x] Added rotated Stage C road-view labels explaining upper status bubbles and lower command/violation bubbles.
- [x] Updated lost-identification behavior to target the frozen leading-truck rear point.
- [x] Added `SAFETY_LOCK` after 30 seconds stopped at the frozen target without identification resume.
- [x] Added Truck #1 state and command columns to the output CSV for complete truck review.
- [x] Moved Stage C lost-target triangle to the frozen leading-truck rear point.
- [x] Refreshed project memory with `progress.md`, updated status, decisions, and README notes.
- [x] Added Stage C state-machine Help popup with merged state/command table and transitions table from `SimRequirements.md`.
- [x] Added editable main GUI `Parameters` tab with Save and Save As.
- [x] Added read-only main GUI `Scenario` tab.
- [x] Sorted and styled GUI log rows by time and truck order with truck colors and compact state-style icons.
- [x] Added colored header strips to differentiate main GUI tabs.
- [x] Colored Stage C lost-target triangles by affected truck and displayed orange/red braking distances in the visualization.
- [x] Refined GUI tab selectors, table sizing/alignment, stale-results clearing, and result-button availability.
- [x] Refined output/log presentation with truck-grouped output columns, one-decimal numeric display, and bold Truck #1 log rows.
- [x] Added truck-colored wheels, stacked colored distance labels, centered chart x-axis labels, and removed the redundant leader status label in Stage C visualization.
- [x] Made the main GUI `Scenario` tab editable with Save, Save As, Insert Row, and Delete Row controls.
- [x] Added dropdown editing for Truck #2 / Truck #3 scenario image events.
- [x] Added Parameters tab text filtering with a clear-filter button.
- [x] Grouped Parameters tab rows by sub-category without changing the saved CSV format.
- [x] Replaced GUI success/warning/error message boxes with a main-button-row status line.
- [x] Audited and documented recent GUI requirements in `SimRequirements.md` and project memory files.
- [x] Added a requirement-tracking workflow so each new requirement is documented and tracked.
- [x] Added draggable Stage C visualization/chart divider with INI persistence.
- [x] Fixed Stage C divider regression so the truck visualization cannot collapse or be clipped out.
- [x] Aligned State Machine Help with Stage C visualization tracking/status and command/action/violation labels.
- [x] Aligned visualization Help search, truck/status colors, split gap charts, and legends.
- [x] Added time tick marks and numeric labels along Stage C popup chart x axes.
- [x] Applied `Max velocity` only to follower trucks, leaving leader velocity uncapped by that parameter.
- [x] Colored GUI action buttons for visibility while leaving Browse buttons uncolored/default.
- [x] Added Scenario name field, Load scenario button, and loaded-scenario headers in the main GUI and Stage C popup.
- [x] Changed Stage C chart x-axis ticks to 1-second marks with numeric labels every 10 seconds.
- [x] Distinguished scenario-driven and distance-threshold image-identification loss target triangles in Stage C and legends.
- [x] Added image-identification loss/resume distance values to the Stage C upper-right distance labels.
- [x] Changed lost-target braking to hold velocity until orange distance, use orange braking after reaching orange distance, and use red braking when already inside orange distance.
- [x] Formatted Stage C popup chart y-axis tick numbers with zero decimal places.
- [x] Positioned Stage C gap arrows and values at the top of the upper truck status rectangles.
- [x] Reverted separate Scenario name / Load scenario controls and kept Scenario Browse as the scenario loader while displaying the selected scenario name.
- [x] Restored target-stop braking for loss targets and added live resume-distance recovery for distance-caused losses.
- [x] Added explicit frozen loss-target rear output columns and used them for exact Stage C triangle placement.
- [x] Added 10 m distance ticks below the Stage C road line.
- [x] Reduced Stage C main truck rectangle height by 25% to reduce label overlap.
- [x] Defined Stage B v1 `Red braking count` cost function.
- [x] Added Bulk simulations generated parameter ranges with inclusive min/max/step values.
- [x] Added `Bulk_Scenarios` predefined scenario folder.
- [x] Added Bulk Simulation GUI tab with scenario selection, cost function selection, progress, cancel, cost chart, and contributor table.
- [x] Added per-run bulk output CSV files and `Bulk_Results.csv` summary output.
- [x] Added Bulk Simulation scenario Select all / Unselect all controls.
- [x] Added Bulk Simulation cost-function chart legend.
- [x] Added explicit `Failure_Reason` output for failed bulk simulation rows.
- [x] Added double-click visualization opening for completed Bulk Simulation run output rows.
- [x] Remembered the last selected Bulk Simulation scenarios folder in `convoysim.ini`.
- [x] Refined Bulk Simulation tab layout with closer range fields, progress bar, and centered Start/Cancel controls.
- [x] Added a Bulk Simulation selected-parameter default value field.
- [x] Added `Accidents` as a Bulk Simulation cost function.
- [x] Show all scenarios for clicked Bulk chart parameter values and highlight cost-triggering rows in red.
- [x] Open a new independent visualization window for each completed Bulk Simulation result double-click.
- [x] Added multi-select Bulk Simulation cost functions with Select all / Unselect all controls.
- [x] Moved Bulk Simulation results chart and table into a separate popup window.
- [x] Added multi-line Bulk Simulation result charting for all selected cost functions.
- [x] Added all cost-function result columns to the Bulk Simulation results table and summary CSV.
- [x] Added browseable Bulk Simulation cost-function weights CSV selection.
- [x] Added `Total_Weighted_Cost` calculation and output for selected Bulk cost functions.
- [x] Added a `Total weighted cost` line to the Bulk Simulation results chart.
- [x] Split the main Input and Output Files GUI section into two columns.
- [x] Added new Stage A parameters for orange mode, TimeHeadway, emergency deceleration, and default `Start moving gap = 8`.
- [x] Added `FORT activated` scenario event parsing and GUI dropdown support.
- [x] Implemented revised orange braking, TimeHeadway target gap, red-to-zero, FORT emergency deceleration, and initial-start rules.
- [x] Added orange-trigger-gap output columns and Stage C required-gap arrows.
- [x] Added the Cost Weight tab and split Bulk results into per-cost and weighted-cost charts with result reopening.
- [x] Added `ConvoyLogic.md` as a user-facing living summary of current convoy behavior.
- [x] Refined Bulk result chart layout with titles, top-right legends, JPG save buttons, integer weighted labels, and auto-width table columns.
- [x] Repositioned Stage C orange-trigger arrows and labels to reduce overlap.
- [x] Highlight selected Bulk chart points after click.
- [x] Wired Truck #1 FORT events from scenario timeline into simulation acceleration and output-row logic.
- [x] Changed Truck #1 FORT from single-step to permanent latch: emergency brake to 0, hold stopped, leader profile ignored after trigger.
- [x] Added agentic-dev remediation: canonical AGENTS.md, CLAUDE.md stub, collapsed .cursor/rules, requirements_traceability.md, STATUS.md trimmed, README split, docs/feature_guide.md, known_issues.md, test_strategy.md, TASKS.md open-only.
