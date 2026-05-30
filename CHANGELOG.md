# CHANGELOG.md

This file records user-visible project changes.

## 2026-05-29

### Fixed

- Stage C gap distance labels (e.g. `16.2 m`, `19.7 m`) now appear above the gap arrow lines instead of below them. (`visualization.py` — `gap_arrow_coordinates` and `orange_trigger_gap_arrow_coordinates` `label_y` changed from `y + 12` to `y - 12`.)

## 2026-05-22

### Added

- Added TimeHeadway orange braking mode, `FORT activated` scenario events, and `Emergency deceleration`.
- Added `ConvoyLogic.md` as a living user-facing summary of convoy behavior.
- Improved Bulk result charts with titles, top-right legends, JPG save buttons, plain integer weighted labels, and auto-width table columns.
- Highlighted the selected Bulk chart dot after clicking a chart point.
- Repositioned Stage C orange-trigger arrows and labels to reduce overlap.
- Added orange-trigger-gap output columns and Stage C required-gap arrows above the actual gap arrows.
- Added a `Cost Weight` GUI tab for editing/saving the selected cost weights CSV.
- Added separate Bulk result charts for per-cost-function totals and `Total weighted cost`, plus a `Show Bulk Results` reopen button.
- Added browseable Bulk Simulation cost-function weights CSV selection and `Total_Weighted_Cost` output.
- Added a `Total weighted cost` line to the Bulk Simulation results chart.
- Split the main GUI input/output file selectors into two columns to save vertical space.
- Bulk Simulation can now select multiple cost functions with `Select all` / `Unselect all`, run them from the same simulation outputs, and chart each selected cost function as a separate line in a results popup.
- Bulk Simulation result tables and `Bulk_Results.csv` include all current cost-function result columns.
- Bulk result double-clicks now open a new independent visualization window each time, allowing side-by-side simulation comparison.
- Bulk chart clicks now show all scenarios for the selected parameter value and highlight cost-triggering rows in red.
- Added `Accidents` as a Bulk Simulation cost function, counted as accident intervals per follower truck and totaled for the selected cost value.
- Added a Bulk Simulation parameter default-value field that updates from the loaded parameters CSV.
- Remembered the last selected Bulk Simulation scenarios folder in `convoysim.ini`.
- Added a Bulk Simulation progress bar next to the parameter range fields and centered Start/Cancel controls.
- Added double-click visualization opening for completed Bulk Simulation run output rows, with a bulk-specific visualization header.
- Added Bulk Simulation scenario `Select all` / `Unselect all` controls.
- Added a Bulk Simulation chart legend for the selected cost function.
- Added explicit `Failure_Reason` output for failed bulk simulation rows.
- Added a Bulk Simulation GUI workflow for Stage B with scenario selection from `Bulk_Scenarios`, inclusive parameter ranges, cost-function selection, progress, cancel, a cost chart, and contributor table.
- Added the first formal Stage B cost function: `Red braking count`, counted per follower truck and totaled for charting.
- Added per-run bulk simulation CSV output plus `Bulk_Results.csv` in `outputs/<cost_function>_<ddmmyy_hhmm>`.
- Added starter predefined bulk scenarios under `Bulk_Scenarios`.
- Added initial dependency-free Python package foundation under `src/convoysim`.
- Added leader profile CSV loading, interpolation, validation helpers, initial convoy geometry, and constant-acceleration physics helpers.
- Added initial unit tests for leader profile behavior, validation, geometry, and physics.
- Added Stage A example input CSV files under `examples/stage_a_example_inputs`.
- Added an additional image-identification loss event to the Stage A example.
- Added a proposed merged `scenario_timeline.csv` example format for leader velocity and follower image-identification events.
- Documented `scenario_timeline.csv` as the merged scenario input format.
- Added `scenario_timeline.csv` parsing with leader profile and follower image-event extraction.
- Added example `parameters.csv` loading.
- Added a basic Stage A simulation runner and CLI command.
- Added basic Stage A output CSV generation under `outputs/stage_a_basic_output.csv`.
- Added braking-distance table loading, interpolation, and integration into basic orange/red follower braking.
- Added image-resume timeout stop reason reporting and stop-reason output columns.
- Added basic communication ON/OFF loss stop requests and communication output columns.
- Added actual/measured gap and relative velocity output columns.
- Added simulation log CSV output.
- Added dependency-free Stage A HTML chart report.
- Added basic Tk Stage A GUI for selecting files, running simulation, reviewing output, viewing logs, and opening charts.
- Added deterministic communication `Sent` / `Retried` / `Approved` / `Failed fallback` status progression.
- Added first Stage B parameter sweep optimizer with ranked CSV output.
- Added `examples/stage_b_parameter_sweep.csv`.
- Improved Stage A chart axes with axis labels, tick marks, grid lines, and more numeric axis values.
- Improved Stage A chart legends and dotted data-line segments during image-identification loss.
- Improved Stage A chart data-line thickness to show orange braking as bold and red braking as double-bold.
- Moved Stage A chart legends to right-side panels next to each chart.
- Added `convoysim.ini` to remember the latest Stage A run files.
- Added GUI startup loading for remembered previous output/log files when available.
- Changed default Stage A output naming to `<scenario_name>_output_<ddmmyy_hhmm>.csv`.
- Added Stage C straight-line Tk Canvas convoy visualization.
- Added Stage C playback controls: play, pause, stop, step forward/back, and horizontal time scrubber.
- Added Stage C visualization styling for tracking loss, braking, communication, and violations.
- Reduced Stage C label overlap by placing each truck's labels on separate vertical lanes.
- Moved Stage C velocity labels inside truck rectangles and simplified gap labels.
- Added Stage C status/command text bubbles above and below trucks.
- Added Stage C playback speed slider from `x0.6` to `x2.0`.
- Added Stage C visualization legend toggle for colors and line styles.
- Moved Stage C playback controls into the Visualization tab.
- Updated GUI output/log/chart filenames when the scenario input file changes.
- Moved Stage C visualization into a popup window launched from the GUI.
- Moved Stage C gap arrows and labels between truck rectangles.
- Moved Stage C legend display to a bottom two-row panel.
- Added Stage C embedded gap chart with a synchronized vertical playback marker.
- Added Stage C temporary target triangle markers during image-identification loss.
- Refined Stage C target triangles to sit on the road line without a text label.
- Refined Stage C gap arrows so labels sit above the truck rectangle top edge.
- Replaced Stage C playback button words with compact playback symbols.
- Added `Resume by distance` parameter, defaulting to `No`, to control automatic distance-based image-identification resume.
- Added a Stage C popup velocity chart below the gap chart, sharing the same synchronized time marker.
- Added numeric y-axis tick values to Stage C popup charts.
- Added Stage C popup chart visibility checkboxes and remembered their state in `convoysim.ini`.
- Matched Stage C popup chart dotted loss and braking-width line styles to the HTML charts.
- Updated Stage C bottom legend samples to match chart colors, dotted lines, and line widths.
- Rotated Stage C popup chart y-axis labels.
- Aligned the Stage C time scrubber with the popup chart plot width.
- Changed Stage C playback speed range to `x0.3` through `x2.0` and remembered the selected speed in `convoysim.ini`.
- Added rotated Stage C road-view labels explaining upper status bubbles and lower command/violation bubbles.
- Updated image-identification loss behavior so followers brake to the frozen leading-truck rear target instead of braking early from the orange gap threshold.
- Added `SAFETY_LOCK` after a follower waits 30 seconds stopped at the frozen target without identification resume.
- Added Truck #1 state and command columns to output CSV files for fuller run analysis.
- Moved the Stage C lost-target triangle to the frozen leading-truck rear point so it matches the state-machine target.
- Added `progress.md` and refreshed project-memory documentation for the current Stage A/B/C working state.
- Added a Stage C visualization Help button with state-machine help generated from `SimRequirements.md`.
- Added editable `Parameters` and read-only `Scenario` tabs to the main GUI.
- Improved the main GUI log tab with time/truck sorting, truck-colored rows, and compact state-style icons.
- Added colored header strips to differentiate main GUI tabs.
- Colored Stage C lost-target triangles by affected follower truck and showed orange/red braking distances in the visualization.
- Refined main GUI tab selectors, table column sizing/alignment, stale-result clearing, and result-button availability.
- Grouped output table columns by truck and formatted displayed numbers to one decimal.
- Improved Stage C visualization with truck-colored wheels, stacked colored braking-distance labels, centered chart x-axis labels, and no redundant leader status label.
- Made the main GUI `Scenario` tab editable with Save, Save As, Insert Row, and Delete Row controls.
- Added dropdown editing for Truck #2 / Truck #3 scenario image event fields.
- Added Parameters tab substring filtering with a clear-filter button.
- Grouped Parameters tab rows by sub-category while preserving the CSV save format.
- Replaced routine GUI message boxes with an inline status line in the main button row.
- Added a draggable Stage C popup divider between the truck visualization and charts, with divider position persisted in `convoysim.ini`.
- Fixed the Stage C popup divider so the truck visualization remains visible while resizing the chart area.
- Aligned the Stage C State Machine Help window with visualization tracking/status, command/action, and violation labels.
- Added searchable Stage C State Machine Help tables.
- Updated Stage C visualization so truck bodies use fixed identity colors and upper status rectangles show image loss, orange braking, and red braking or violation states.
- Split the Stage C gap chart into separate `Gap1-2` and `Gap2-3` charts with chart segment styling matched to truck/status visualization rules.
- Updated Stage C legend entries to explain truck colors, status rectangles, and chart segment formats.
- Added time tick marks and numeric labels along Stage C popup chart x axes.
- Changed simulation behavior so `Max velocity` caps follower trucks only; Truck #1 follows the scenario velocity profile without that cap.
- Colored GUI action buttons for better visibility while keeping Browse buttons in the default style.
- Added a Scenario name field, Load scenario button, and loaded-scenario headers in the main GUI and Stage C popup.
- Updated Stage C popup chart x axes to use 1-second tick marks with numeric labels every 10 seconds.
- Distinguished Stage C lost-target triangles: empty for scenario-driven image-identification loss and filled for distance-threshold loss.
- Added image-identification loss and resume distance values to the Stage C upper-right distance labels.
- Changed lost-target braking to keep current velocity until orange distance, use orange braking at orange distance, and use red braking when the stop target is already inside orange distance.
- Changed Stage C popup chart y-axis tick labels to show zero decimal places.
- Moved Stage C gap arrows and values to the top of the upper truck status rectangles.
- Removed the separate Scenario name field and Load scenario button; the Scenario Browse button is again the only scenario loader, while the selected scenario name is still displayed in the GUI and Stage C popup.
- Restored loss-target braking to decelerate toward the frozen target at 0 velocity and allowed distance-caused losses to resume tracking mid-approach when the live gap reaches resume distance.
- Added explicit frozen loss-target rear columns to output CSV files and used them for exact Stage C triangle placement.
- Added 10 m distance ticks below the Stage C road line.
- Reduced Stage C main truck rectangle height by 25% to reduce label overlap.

### Removed

- Removed superseded example files `leader_profile.csv`, `truck2_loss_events.csv`, and `truck3_loss_events.csv`.

- Added base documentation structure:
  - `README.md`
  - `AGENTS.md`
  - `PLANNING.md`
  - `TASKS.md`
  - `STATUS.md`
  - `DECISIONS.md`
  - `CHANGELOG.md`

- Added base Cursor rules:
  - `.cursor/rules/always.mdc`
  - `.cursor/rules/project-context.mdc`
  - `.cursor/rules/python-development.mdc`
  - `.cursor/rules/validation.mdc`
  - `.cursor/rules/documentation-workflow.mdc`
