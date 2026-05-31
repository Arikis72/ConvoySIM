---
title: ConvoySIM — Design Decisions
type: decisions
date: 2026-05-30
description: Important design decisions and rationale for ConvoySIM. Updated whenever a non-obvious decision or tradeoff is made.
tags: [convoysim, decisions]
related: ["[[AGENTS]]", "[[PLANNING]]", "[[requirements_traceability]]"]
---

# ConvoySIM — Design Decisions

> See [[AGENTS]] §10 for when to update this file. See [[PLANNING]] for architecture context.

This file records important design decisions for ConvoySIM.

Use this format for each decision:

```md
## YYYY-MM-DD — hh:mm - Decision title

Decision:
What was decided.

Reason:
Why this decision was made.

Alternatives considered:
What other options were considered.

Consequences:
What this affects later.
```

## 2026-05-22 — Use dedicated project documentation files

Decision:
Use separate Markdown files for project overview, agent instructions, planning, tasks, status, decisions, and changelog.

Reason:
Separating responsibilities prevents Cursor and other AI tools from mixing current state, instructions, tasks, and historical decisions.

Alternatives considered:
A single large `README.md` or a single `progress.md`.

Consequences:
Agents must read the relevant files before editing code.
Documentation must be kept updated as part of the development workflow.

## 2026-05-22 — Use Cursor project rules

Decision:
Use `.cursor/rules/*.mdc` files for Cursor-specific behavior.

Reason:
Cursor rules are the proper place for persistent Cursor instructions.

Alternatives considered:
Putting all AI instructions only in `README.md`.

Consequences:
Cursor behavior is controlled by `.cursor/rules`, while shared agent behavior is controlled by `AGENTS.md`.

## 2026-05-22 — Start with dependency-free Python core

Decision:
Build the first implementation as a standard-library Python package under `src/convoysim`, with simulation logic separated from future GUI code.

Reason:
The requirements call for a GUI, but the project first needs testable simulation primitives: parameters, validation, CSV loading, leader interpolation, geometry, and physics.

Alternatives considered:
Starting directly with a GUI or adding plotting/UI dependencies immediately.

Consequences:
Core behavior can be validated with `unittest` before GUI wiring. GUI and chart dependencies should be added later only when Stage A presentation work begins.

## 2026-05-22 — Use merged scenario timeline input

Decision:
Use one `scenario_timeline.csv` file for Truck #1 leader velocity points and Truck #2 / Truck #3 image-identification loss or resume events.

Reason:
A single time-ordered file makes it easier for users to plan and review a simulation scenario.

Alternatives considered:
Keeping separate files for `leader_profile.csv`, `truck2_loss_events.csv`, and `truck3_loss_events.csv`.

Consequences:
The example input set no longer includes the separate scenario files. The Python loader must be updated to parse the merged scenario timeline format before Stage A simulation execution can use the example directly.

## 2026-05-22 — Ship a basic Stage A runner before GUI

Decision:
Create a command-line basic Stage A simulation runner that loads the example CSV files and writes an output CSV before implementing charts or GUI controls.

Reason:
The project needs an executable simulation loop that can be validated and inspected before adding presentation layers.

Alternatives considered:
Waiting to run simulations until the full GUI is available.

Consequences:
Users can now inspect `outputs/stage_a_basic_output.csv` from a repeatable CLI command. The runner is intentionally incomplete relative to the full Stage A requirements and must be expanded for communication, braking-table lookup, full image-loss timeout behavior, charts, and GUI.

## 2026-05-22 — Use deterministic communication approval in basic runner

Decision:
For the basic runner, treat communication reliability as deterministic: `0%` means communication fallback, and any value above `0%` means the communication request is approved.

Reason:
The requirements define reliability as a parameter but leave the exact transaction semantics open. Deterministic behavior keeps tests repeatable until the full communication retry model is implemented.

Alternatives considered:
Randomized message approval based on the reliability percentage.

Consequences:
The basic runner can exercise communication ON/OFF behavior reproducibly. A later Stage A pass must implement the requested retry/fallback behavior once the reliability semantics are clarified.

## 2026-05-22 — Use deterministic communication retry progression

Decision:
For Stage A, communication status progresses deterministically from `Sent` to `Retried` to either `Approved` or `Failed fallback`. `0%` reliability fails after the retry window, `1-99%` retries before approval, and `100%` approves without retry.

Reason:
The requirements define retry timing but still leave the exact probability semantics open. Deterministic status progression keeps output reproducible and makes the retry/fallback paths visible in tests and logs.

Alternatives considered:
Random approval based on the reliability percentage.

Consequences:
Tests and example outputs are repeatable. If probabilistic communication is later required, this behavior should be replaced behind the same output/status interface.

## 2026-05-23 — Default image-loss recovery requires explicit resume

Decision:
Add `Resume by distance` as a simulation parameter and default it to `No`.

Reason:
Scenario files with long image-identification loss intervals should remain lost for the planned interval unless the user explicitly opts into automatic distance-based resume behavior.

Alternatives considered:
Keeping distance-based resume always enabled.

Consequences:
Existing scenarios can still use distance-based resume by setting `Resume by distance` to `Yes`; otherwise followers resume only from an explicit `Resume` event or from timeout handling.

## 2026-05-23 — Lost tracking targets frozen rear point

Decision:
When a follower is in `TRACKING_LOST_TO_LAST_POSITION`, it targets the frozen rear end of the followed truck, not the followed truck front position.

Reason:
The convoy following logic is based on the rear of the followed truck. The lost-target marker and stopping behavior must match the same physical target used by gap calculations.

Alternatives considered:
Using the frozen front bumper position as the target marker, or braking early based only on the orange gap threshold.

Consequences:
The follower now uses target-stop braking to stop at the frozen rear point. The Stage C triangle marker is drawn at that same rear target. If the follower remains stopped there without identification resume for 30 seconds, it enters `SAFETY_LOCK`.

## 2026-05-22 — Start Stage B with explicit sweep rows

Decision:
Implement the first Stage B optimizer as an explicit CSV parameter sweep. Each row defines one candidate set of orange deceleration, orange distance, green acceleration, start moving gap, optimal acceleration, and target gap.

Reason:
`SimRequirements.md` says the formal cost function will be defined later. Explicit rows let users compare scenarios immediately without inventing parameter ranges or a search algorithm.

Alternatives considered:
Generating all combinations from min/max/step ranges.

Consequences:
Stage B can produce a ranked optimization CSV now. Future work should add range generation after the user approves parameter ranges and the formal cost function.

## 2026-05-22 — Use temporary deterministic Stage B score

Decision:
Rank Stage B candidates by a deterministic temporary score: hard-constraint violations first, then full-stop count, then acceleration sign-change count.

Reason:
The requirements define priorities but not a formal cost function. This score follows the stated priorities without claiming to be final optimization math.

Alternatives considered:
Leaving candidates unranked or inventing a more complex cost model.

Consequences:
Optimization output is useful for comparison but should be revisited once the formal cost function is defined.

## 2026-05-23 — Remember Stage A run files in INI

Decision:
Use `convoysim.ini` in the project root to remember the latest Stage A parameter, scenario, braking table, output CSV, log CSV, and chart HTML paths.

Reason:
The GUI and CLI need a lightweight way to reopen or reuse the previous run files without adding external dependencies.

Alternatives considered:
Storing run history in JSON or only keeping the values in GUI memory.

Consequences:
The latest successful Stage A run updates `convoysim.ini`. The file is human-readable and can be edited manually if needed.

## 2026-05-23 — Timestamp Stage A output names from scenario input

Decision:
When an explicit output path is not provided, Stage A output uses the scenario input stem plus `_output_` and a `ddmmyy_hhmm` run timestamp. Log and chart files use the same stem and timestamp with `_log_` and `_charts_`.

Reason:
This prevents accidental overwrites and keeps generated artifacts tied to the scenario file the user selected.

Alternatives considered:
Continuing to overwrite fixed files such as `stage_a_basic_output.csv`.

Consequences:
Default run commands create new timestamped files under `outputs/`; callers can still provide explicit output paths when needed.

## 2026-05-23 — Implement Stage C as row playback

Decision:
Implement Stage C visualization by replaying completed `SimulationResult.rows` in a Tk Canvas instead of running a second real-time physics loop.

Reason:
The Stage A runner already computes positions, gaps, velocities, states, commands, communication messages, and violations. Reusing those rows keeps Stage C visually consistent with the validated output table and avoids duplicate simulation logic.

Alternatives considered:
Creating a separate real-time simulation loop directly inside the GUI.

Consequences:
Stage C play, pause, stop, step, and time scrubbing control playback of generated rows. Interrupting a simulation while it is still computing remains future work.

## 2026-05-26 — Preserve CSV formats while improving GUI editing

Decision:
Parameter grouping and scenario editing are GUI presentation/editor features only. The saved parameter and scenario files preserve the CSV formats defined in `SimRequirements.md`.

Reason:
Users need easier parameter discovery, scenario planning, and row editing without creating a new file format or breaking the existing CLI/loaders/tests.

Alternatives considered:
Adding category columns to the CSV files or migrating to a richer structured format.

Consequences:
GUI-only grouping rows must be skipped during save. Scenario image-event cells use controlled dropdown values, but validation still happens through the existing scenario loader and simulation run path.

## 2026-05-26 — Use inline GUI status for routine feedback

Decision:
Routine GUI success, warning, and error feedback should use a main-window status line instead of modal message boxes where possible.

Reason:
The user repeatedly runs, edits, and saves from the GUI. Modal OK dialogs interrupt that workflow and caused unnecessary repeated clicks.

Alternatives considered:
Keeping `messagebox` dialogs for all feedback, or adding a dedicated log-only feedback mechanism.

Consequences:
Save/run/open status appears inline in the main button row. Blocking dialogs should be reserved only for future cases that require explicit user confirmation.

## 2026-05-26 — Track every new requirement in project memory

Decision:
Every new user requirement must be documented in the project memory and tracked in `TASKS.md` before or during implementation.

Reason:
Recent GUI work required repeated clarification because some details lived only in chat history. The project needs a durable requirement-intake workflow that future agents can follow without relying on memory from previous conversations.

Alternatives considered:
Relying on chat summaries or only updating completed-task notes after implementation.

Consequences:
New requirements should be added to `SimRequirements.md` or recorded as open questions, paired with concrete `TASKS.md` tracking items, then reflected in `STATUS.md`, `progress.md`, and `CHANGELOG.md` or `DECISIONS.md` when appropriate.

## 2026-05-27 — Use a persisted pane divider for Stage C chart zoom

Decision:
Use the Stage C popup's vertical paned layout to let users drag the divider between the truck visualization and chart area, and persist the divider position in `convoysim.ini`.

Reason:
Dragging the divider is a simple GUI-native way to give charts more vertical space without adding separate zoom controls or changing simulation data.

Alternatives considered:
Adding separate chart-height sliders or fixed chart-size presets.

Consequences:
The chart canvases resize vertically when the divider moves, so the y-axis is visually zoomed by available chart height. The saved divider position is clamped to a practical range when loaded from the INI file.

## 2026-05-27 — Use identity colors and status overlays in Stage C

Decision:
Use fixed truck identity colors for truck bodies and normal chart lines, and show transient state information through upper status rectangles and matching chart segment styles.

Reason:
Users need to correlate a truck in the road visualization with its gap and velocity chart lines quickly. Previously, truck body colors changed by state, which made identity harder to follow.

Alternatives considered:
Keeping state-driven truck body colors or using only text labels/bubbles for status.

Consequences:
Truck #1 remains black, Truck #2 blue, and Truck #3 orange. Image loss, orange braking, red braking, and safety violations are represented by the upper status rectangle and matching chart segment style, while text bubbles remain available for exact state/action wording.

## 2026-05-27 — Apply max velocity only to followers

Decision:
`Max velocity` limits follower truck motion only. Truck #1 leader velocity is driven by the scenario timeline and is not capped by this parameter.

Reason:
The leader represents the external scenario input. The user needs scenarios where Truck #1 can drive at any planned velocity while the convoy follower trucks remain limited by the configured follower capability.

Alternatives considered:
Continuing to cap all three trucks with the same parameter.

Consequences:
Follower trucks cannot exceed `Max velocity`; Truck #1 can exceed it if the scenario profile does. Leader acceleration/deceleration validation remains unchanged.

## 2026-05-27 — Track image-loss source in output rows

Decision:
Add follower loss-source fields to simulation rows and output CSV files so Stage C can distinguish scenario-driven image loss from distance-threshold image loss.

Reason:
The visualization needs to draw empty lost-target triangles for scenario events and filled triangles for automatic distance-threshold losses. That distinction is not reliably inferable from tracking status alone during playback.

Alternatives considered:
Inferring the source from log rows or scenario files during visualization.

Consequences:
New output CSV files include `Truck2_Loss_Source` and `Truck3_Loss_Source`. Older output CSV files without these fields still load, but their lost-target markers default to scenario-style empty triangles.

## 2026-05-27 — Use scenario name for GUI run identity

Decision:
Use the editable Scenario name field as the GUI run identity for displayed headers and timestamped output/log/chart filenames, while the scenario path remains the actual CSV file loaded and simulated.

Reason:
The user needs a friendly scenario name that is visible in the GUI and visualization and can be used to call/load the scenario without relying only on the full file path.

Alternatives considered:
Using only the scenario CSV filename stem.

Consequences:
The Scenario name is persisted in `convoysim.ini`. The Load scenario button resolves the entered name to a CSV in the current scenario directory unless the user enters a path.

Superseded:
This decision was superseded on 2026-05-27 by using the Scenario Browse button as the only scenario loader while still displaying the selected scenario file name.

## 2026-05-27 — Use thresholded braking for image-loss targets

Decision:
Replace exact lost-target stop acceleration with thresholded braking against the followed-truck rear target or frozen last-position target: hold current velocity while outside orange distance, use orange braking once orange distance is reached, and use red braking if the target is already inside orange distance.

Reason:
The user requested behavior that follows the existing orange/red threshold model instead of computing a custom exact-stop acceleration for lost-target stopping.

Alternatives considered:
Keeping the exact target-stop acceleration that stopped precisely at the frozen rear point.

Consequences:
Followers may stop before the frozen target when configured orange/red deceleration is stronger than needed for an exact stop. Safety Lock timing now starts when the follower is stopped under image-identification loss rather than only when positioned exactly at the frozen target.

Superseded:
This decision was superseded on 2026-05-27 by restoring target-stop braking for loss targets and adding live resume-distance recovery for distance-caused losses.

## 2026-05-27 — Use Scenario Browse as the scenario loader

Decision:
Keep the Scenario Browse button as the only scenario-loading control and derive the displayed scenario name from the selected scenario file path.

Reason:
The user requested reversing the separate Scenario name field and Load scenario button. The only needed scenario-name behavior is presentation of the selected scenario name.

Alternatives considered:
Keeping a separate editable scenario-name field and Load scenario button.

Consequences:
`convoysim.ini` stores the scenario path but no separate scenario name. Timestamped output/log/chart names are again based on the selected scenario file stem, and the main GUI plus Stage C popup display that selected scenario name.

## 2026-05-27 — Resume distance-caused loss during target approach

Decision:
For distance-caused image-identification loss, use target-stop braking toward the frozen loss target but resume tracking immediately if the live gap reaches the configured resume distance before the target is reached.

Reason:
The user clarified that distance-loss recovery should be able to stop decelerating and resume tracking during the approach when identification becomes valid again.

Alternatives considered:
Waiting until the follower reaches the frozen target before checking resume distance.

Consequences:
Distance-caused loss triangles disappear as soon as tracking resumes. If the follower reaches the frozen target and the live gap is still greater than resume distance, the follower remains stopped under loss behavior.

## 2026-05-27 — Persist loss targets for visualization

Decision:
Store frozen loss-target rear positions in the simulation output and use those explicit values for Stage C lost-target triangle placement.

Reason:
Reconstructing the target from sampled output rows can offset the triangle when loss occurs between output samples. The simulation already knows the exact frozen target at the loss time.

Alternatives considered:
Increasing output resolution or continuing to infer the target from the first sampled `Lost` row.

Consequences:
New output CSV files include `Truck2_Loss_Target_Rear_m` and `Truck3_Loss_Target_Rear_m`. Stage C triangle placement matches the control target instead of the nearest replay sample.

## 2026-05-27 — Start Bulk simulations with red braking count

Decision:
Use `Red braking count` as the first formal Stage B bulk cost function. The count is measured as red-braking state-entry events per follower truck, with Truck #2 and Truck #3 stored separately and total cost shown across both trucks.

Reason:
The user requested a simple first success criterion focused on reducing red braking events before adding parallel safety and comfort cost functions.

Alternatives considered:
Counting every output row spent in red braking, or immediately combining red braking with collision, minimum-gap violation, full stops, and oscillation costs.

Consequences:
Bulk Simulation v1 optimizes one parameter at a time over an inclusive min/max/step range and treats all selected scenarios equally. Later cost functions can be added beside this one without changing the per-run output structure.

## 2026-05-27 — Add accidents as a Bulk Simulation cost function

Decision:
Add `Accidents` as a selectable Bulk Simulation cost function. An accident is counted as one interval while a following truck front position is greater than or equal to the rear position of the truck ahead. Counts are stored per follower truck and totaled as the selected cost value.

Reason:
The user requested accident counting as the next success criterion after red braking count, with continuous accident conditions counted once until the condition clears.

Alternatives considered:
Counting every output row where the accident condition is true, or treating accident/collision rows only as a hard failure outside the cost-function system.

Consequences:
`Bulk_Results.csv` includes accident count columns and a generic `Cost_Value`. The Bulk chart and red-row highlighting use the selected cost function, so future cost functions can reuse the same display path.

## 2026-05-27 — Use independent windows for Bulk run visualization

Decision:
Double-clicking a completed Bulk Simulation result row opens a new independent visualization window every time. Each bulk visualization owns its own playback state, time slider, charts, header, and playback timer.

Reason:
The user wants to compare more than one simulation at the same time. Reusing the existing single Stage C popup would cause shared state conflicts between windows.

Alternatives considered:
Reusing the existing Stage C visualization popup, replacing the currently displayed run on each double-click, or opening multiple windows backed by shared GUI state.

Consequences:
Main `Open Visualization` behavior remains unchanged for the latest Stage A run. Bulk result visualization has a separate self-contained window path so multiple simulation replays can remain open side by side.

## 2026-05-28 — Compute selected Bulk cost functions together

Decision:
Bulk Simulation accepts multiple selected cost functions, computes their metrics from the same simulation output rows, and shows results in a separate popup with one chart line per selected cost function.

Reason:
The user wants to compare cost functions side by side without rerunning the same scenario/parameter simulation separately for each cost function.

Alternatives considered:
Running a separate full bulk pass for each cost function.

Consequences:
`Bulk_Results.csv` keeps one row per scenario/parameter run and includes all current cost-function columns. The generic `Cost_Value` column initially remained the first selected cost value for compatibility, then was superseded by `Total_Weighted_Cost`.

## 2026-05-28 — Use weighted Bulk cost score

Decision:
Replace the generic selected `Cost_Value` with `Total_Weighted_Cost`, calculated from the selected cost functions and user-selected cost weights CSV. Keep individual cost totals as separate columns and add `Total weighted cost` as an additional chart line.

Reason:
The generic selected-cost column became ambiguous once multiple cost functions could be selected. Weighted scoring gives one comparable grade while preserving the individual cost-function evidence.

Alternatives considered:
Removing the generic score entirely and charting only individual cost-function totals.

Consequences:
Bulk runs require a valid weights CSV for selected cost functions. The selected weights are copied into the bulk output folder, and the GUI can compare both individual event totals and the weighted combined grade.

## 2026-05-29 — FORT on Truck #1 latches permanently to full stop

Decision:
Once a `FORT activated` event fires in the `Truck1_Event` column, the leader permanently applies maximum emergency deceleration until velocity reaches 0, then holds stopped for the rest of the scenario. The leader profile velocity schedule is entirely ignored after FORT.

Reason:
FORT represents a physical emergency stop system that cannot be reversed by the scenario script once triggered. Any subsequent leader profile velocity target would be physically meaningless after an irreversible emergency brake engagement.

Alternatives considered:
- **Single-step**: Apply emergency deceleration only at the event timestep, then resume profile-following (rejected — truck would immediately accelerate again).
- **Time-limited**: Apply emergency deceleration for a fixed duration, then resume (rejected — arbitrary; the physical system does not have a timed release).
- **Resettable by another event**: Allow a future scenario event to cancel FORT (rejected — not in scope; requirements do not define a FORT release event).

Consequences:
`truck1_fort_latched` is a boolean that is set to `True` when FORT fires and never reset within a simulation run. `_emergency_deceleration()` naturally returns 0 when velocity is 0, holding the truck stopped. The leader profile is bypassed for the rest of the run.

## 2026-05-28 — Use continuous orange trigger target

Decision:
Compute `orange_trigger_gap` continuously and store it in simulation output. Fixed mode uses `Orange distance`; TimeHeadway mode uses `follower_velocity_mps * TimeHeadway + Minimum allowed gap distance`. Orange entry stores a 75% target velocity, red braking overrides orange and continues to zero, and `FORT activated` applies the configured emergency deceleration.

Reason:
The orange target gap and TimeHeadway mode need to be visible and consistent between simulation behavior, output data, and replay visualization.

Consequences:
Stage A output includes orange-trigger-gap columns, Stage C shows required-gap arrows above actual gaps, and scenario timelines can trigger per-truck FORT emergency deceleration.

## 2026-05-31 — FOLLOW_PROFILE: look-ahead over return_to_sim_velocity_s, not current time

Decision:
When auto-advancing in live mode, the leader targets the profile's velocity at `current_time + return_to_sim_velocity_s` (default 3 s ahead), not at `current_time`.

Reason:
Targeting the current-time velocity causes over-correction: if the profile drops in 2 s, the leader accelerates to the current target and then must immediately brake. Looking ahead by `return_to_sim_velocity_s` seconds pre-adjusts the leader so it arrives at the right velocity when the profile change occurs.

Alternatives considered:
Targeting `current_time` velocity (simpler, but causes oscillation at velocity transitions). PID controller (more robust but complex and adds a tunable parameter set).

Consequences:
`return_to_sim_velocity_s` must be added to `SimulationParameters` (user-tunable, default 3 s). Larger values = smoother but slower convergence. The acceleration is clamped to vehicle limits so unreachable targets degrade gracefully.

## 2026-05-31 — leader_command_kind propagated through _build_output_row

Decision:
Added optional `leader_command_kind: str = ""` to `_leader_state`, `_leader_command`, and `_build_output_row` in `simulation.py`; `_step_n` in `live_stepper.py` passes `command.kind`.

Reason:
`_leader_state` / `_leader_command` only had access to the resulting acceleration magnitude, not the originating command type. Orange brake and normal deceleration both produce the same negative acceleration, making them indistinguishable in the output row — and therefore in the visualization's color logic.

Alternatives considered:
Storing the live command kind separately in `_StepperState` (more invasive). Computing color from acceleration thresholds (unreliable — a hard deceleration from Accelerate → HOLD could exceed orange threshold). 

Consequences:
Pre-calculated simulation (non-live) always passes `""` (default), so existing behavior is unchanged. Live mode rows now carry the exact command kind in `truck1_state` / `truck1_command`, enabling correct color coding and future log analysis.
