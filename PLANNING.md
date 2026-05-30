---
title: ConvoySIM — Planning & Architecture
type: planning
date: 2026-05-30
description: Architecture, design direction, and data flow for ConvoySIM. Load on demand when making architectural decisions.
tags: [convoysim, planning, architecture]
related: ["[[AGENTS]]", "[[SimRequirements]]", "[[decisions]]"]
---

# ConvoySIM — Planning & Architecture

> Load this file when making architectural decisions. See [[SimRequirements]] for the behavioral spec, [[decisions]] for past choices.

This file describes the intended architecture and development direction for ConvoySIM.

## Project goal

ConvoySIM should implement the simulation behavior defined in `SimRequirements.md`.

## Architecture overview

```text
src/
  convoysim/
    __init__.py
    braking.py
    charts.py
    gui.py
    __main__.py
    leader_profile.py
    models.py
    optimization.py
    parameters.py
    physics.py
    run_config.py
    scenario.py
    scenario_timeline.py
    simulation.py
    units.py
    validation.py
    visualization.py
tests/
outputs/
```

## Main components

| Component | Responsibility | Status |
|---|---|---|
| Simulation core | Runs the main simulation logic | Stage A runner with revised orange/red/FORT follower behavior implemented |
| Scenario/config loader | Loads simulation inputs and settings | Example parameter, braking table, and merged scenario timeline loaders implemented |
| Output/reporting layer | Saves or displays simulation results | Output CSV, log CSV, and HTML chart report implemented |
| UI/CLI layer | Allows the user to run or configure the simulation | CLI and basic Tk GUI implemented |
| Run configuration | Remembers latest Stage A run files and output naming | INI-backed run config implemented |
| Optimization layer | Compares parameter candidates using the current simulation logic | Explicit Stage B sweep and first Bulk simulations workflow implemented |
| Visualization layer | Replays simulation rows as a straight-line convoy animation | Stage C Tk Canvas playback with actual/required gap display implemented |
| Validation/tests | Verifies expected behavior | Initial validation helpers and unit tests started |

## Data flow

Document the intended data flow here.

Example placeholder:

```text
Input configuration
    -> validation
    -> simulation engine
    -> result aggregation
    -> output/export/reporting
```

Current first-step data flow:

```text
Scenario timeline CSV / typed parameters / braking-distance CSV
    -> validation helpers
    -> leader interpolation, Loss/Resume/FORT event handling, braking lookup, and physics helpers
    -> Stage A simulation runner
    -> output CSV with orange trigger gaps / log CSV / chart HTML / GUI review
```

Current Stage B data flow:

```text
Parameter CSV / scenario timeline CSV / braking-distance CSV / sweep CSV
    -> Stage A runner per sweep candidate
    -> hard-constraint and comfort metrics
    -> ranked optimization CSV
```

Current Bulk simulations data flow:

```text
Parameter CSV / Bulk_Scenarios/*.csv / braking-distance CSV / cost weights CSV / selected parameter range / cost functions
    -> inclusive parameter value generation
    -> Stage A runner per scenario and parameter value
    -> selected cost-function totals and total weighted cost
    -> per-run output CSV files
    -> Bulk_Results.csv and GUI popup with per-cost and weighted-cost charts
```

Current Stage C data flow:

```text
Stage A simulation result rows / previous output CSV
    -> position scaling and status styling
    -> Tk Canvas straight-line convoy playback with actual and orange-trigger gap arrows
    -> play / pause / stop / step / time scrubber controls
```

## Design principles

- Requirements-first development.
- Deterministic behavior where possible.
- Clear separation between simulation logic and user interface.
- Clear validation of inputs before simulation starts.
- Logs and outputs should make failures easy to diagnose.
- Avoid global state unless there is a clear reason.

## Open architecture questions

Add unresolved questions here.

- [x] What is the primary execution mode: CLI, GUI, notebook, or service? GUI.
- [x] What input file formats are required? CSV files as defined in `SimRequirements.md`.
- [x] What outputs are required? Stage A table and charts as defined in `SimRequirements.md`.
- [x] What simulation entities and state variables are required? Defined initially in `src/convoysim/models.py`, with follower state-machine entities still pending.
- [ ] What validation rules must be enforced before running a simulation?
- [ ] What performance constraints exist?

## Future improvements

Add future ideas here only after the base behavior is stable.
