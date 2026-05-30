---
title: ConvoySIM — Feature Guide
type: docs
date: 2026-05-30
description: Detailed feature reference for ConvoySIM — CLI usage, GUI walkthrough, Stage B optimization, Bulk Simulations, Stage C visualization, and output file formats.
tags: [convoysim, feature-guide, docs]
related: ["[[README]]", "[[SimRequirements]]", "[[ConvoyLogic]]"]
---

# ConvoySIM — Feature Guide

> Quick reference: see [[README]] for project overview and dev workflow.
> Behavior spec: see [[SimRequirements]] for the full 26-section specification.
> Implemented logic summary: see [[ConvoyLogic]].

---

## Running commands

All commands must be run from the **project root** `C:\dev\ConvoySIM`.

---

## Stage A — Basic Simulation (CLI)

```powershell
$env:PYTHONPATH = "src"; python -m convoysim `
  --parameters Inputs/stage_a_example_inputs/parameters.csv `
  --scenario   Inputs/stage_a_example_inputs/scenario_timeline.csv `
  --braking-table Inputs/stage_a_example_inputs/braking_distance_table.csv
```

Default output naming (based on selected scenario file name + timestamp):

```
outputs/<scenario_name>_output_<ddmmyy_hhmm>.csv
outputs/<scenario_name>_log_<ddmmyy_hhmm>.csv
outputs/<scenario_name>_charts_<ddmmyy_hhmm>.html
```

Latest paths are remembered in `convoysim.ini`.

**Output CSV columns:** truck positions, velocities, accelerations, Truck #1 state/command, follower gaps, actual gaps, delayed measured gaps, relative velocities, orange trigger gaps, frozen loss-target rear positions, follower states/commands, tracking status, communication status, violations, and stop reasons.

`Max velocity` caps Truck #2 and Truck #3 follower motion only. Truck #1 follows the scenario timeline velocity and may exceed that parameter.

---

## Stage A — GUI

```powershell
$env:PYTHONPATH = "src"; python -m convoysim.gui
```

### Tabs

| Tab | Purpose |
|-----|---------|
| **Parameters** | Edit loaded parameters CSV; filter by substring; view grouped by sub-category; Save / Save As |
| **Scenario** | Edit selected scenario timeline; Save / Save As; Insert Row / Delete Row; dropdown editing for Truck #2 / #3 image events and `Truck1_Event` (incl. `FORT activated`) |
| **Bulk Simulation** | Configure and run bulk parameter sweeps — see Bulk Simulations section |
| **Cost Weight** | Edit and save the selected cost-function weights CSV |
| **Output Table** | Review simulation output; truck-grouped columns; one-decimal numeric format |
| **Log** | Time-sorted, truck-colored event log with compact state icons; bold Truck #1 rows |

### General GUI behaviour
- Status messages appear in the main button row (no modal message boxes for routine feedback).
- Action buttons use role-based colors; Browse buttons keep default style.
- Selecting new input files clears stale output/log views.
- `Open Visualization` and `Open Charts` become available after a successful simulation run.
- The selected scenario name is shown in the main GUI header and the Stage C popup.

---

## Stage C — Visualization Popup

Launched via `Open Visualization` after a run.

**Road view:**
- Straight-line convoy; trucks move left-to-right.
- Truck identity colors: Truck #1 black, Truck #2 blue, Truck #3 orange.
- Upper status rectangles: normal (truck color), dotted border = image-id loss, orange fill = orange braking, red fill = red braking / safety violation.
- Gap arrows + values at the top of status rectangles; actual gap + orange trigger gap arrows shown.
- Lost-target triangles at the frozen leading-truck rear point: empty = scenario-driven loss, filled = distance-threshold loss; colored by affected follower.
- 10 m distance ticks below the road line.
- Rotated origin-side labels explaining upper (tracking/status) and lower (command/action/violation) label areas.

**Charts (embedded below road view):**
- Separate `Gap1-2` and `Gap2-3` charts with matching truck/status line styles.
- Velocity chart.
- Synchronized vertical playback marker.
- 1-second time ticks; numeric labels every 10 seconds.
- Dotted segments during image-id loss; bold/double-bold during orange/red braking.
- Chart visibility checkboxes (persisted in `convoysim.ini`).

**Controls:**
- Play / Pause / Stop / Step / Playback speed (`x0.3`–`x2.0`, persisted).
- Horizontal time scrubber.
- Legend toggle (bottom panel).
- Draggable horizontal divider between road view and charts (persisted).
- **Help** — searchable state-machine help built from `SimRequirements.md` §17.

---

## Stage B — Parameter Sweep Optimization

```powershell
$env:PYTHONPATH = "src"; python -m convoysim.optimization `
  --parameters Inputs/stage_a_example_inputs/parameters.csv `
  --scenario   Inputs/stage_a_example_inputs/scenario_timeline.csv `
  --braking-table Inputs/stage_a_example_inputs/braking_distance_table.csv `
  --sweep Inputs/stage_b_parameter_sweep.csv `
  --output outputs/stage_b_optimization.csv
```

Ranked optimization output written to the specified `--output` path.

---

## Bulk Simulations

Access via the `Bulk simulations` button → **Bulk Simulation** tab.

Bulk scenarios are CSV scenario timelines stored in:
```
Bulk_Scenarios/
```

**Setup:**
1. Select one or more scenarios (use Select all / Unselect all).
2. Select one parameter and set an inclusive min/max/step range.
3. Select one or more cost functions (use Select all / Unselect all).
4. Browse and select a cost weights CSV.

**Supported cost functions:** `Red braking count`, `Accidents` — each counted per follower truck, totalled across Truck #2 and Truck #3.

**Cost weights CSV format:**
```csv
Cost_Function,Weight
Red braking count,1.0
Accidents,1000.0
```

Only selected cost functions contribute to `Total_Weighted_Cost`.

**Outputs:**
```
outputs/<cost_functions>_<ddmmyy_hhmm>/Bulk_Results.csv
outputs/<cost_functions>_<ddmmyy_hhmm>/<per-run CSVs>
```

Failed rows include a `Failure_Reason` column in `Bulk_Results.csv`.

**Results popup** (opens automatically; reopen with `Show Bulk Results`):
- Per-cost-function chart + `Total weighted cost` chart.
- Results table with all cost-function columns.
- Click a chart point → show all scenarios for that parameter value; cost-triggering rows highlighted red.
- Double-click a result row → open that run in a new independent visualization window.
- JPG save button per chart.
