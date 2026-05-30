# Stage A Example Inputs

This folder contains a small example input set for the first ConvoySIM Stage A scenario.

Files:

- `parameters.csv` - simulation and truck parameters.
- `scenario_timeline.csv` - merged scenario format for leader velocity and follower image-identification events.
- `braking_distance_table.csv` - braking distance lookup table by road type, braking type, and velocity.

Notes:

- The CSV formats follow `SimRequirements.md` where the format is defined.
- `parameters.csv` uses a simple `Parameter,Value,Unit,Description` structure until the GUI/import format is finalized.
- `scenario_timeline.csv` replaces the separate leader-profile and loss-event files. Blank cells mean no new value or event at that time.
- This example is intended for development and validation, not as a tuned or optimized convoy scenario.

Run the basic simulation from the repository root:

```powershell
$env:PYTHONPATH = "src"; python -m convoysim --parameters examples/stage_a_example_inputs/parameters.csv --scenario examples/stage_a_example_inputs/scenario_timeline.csv --braking-table examples/stage_a_example_inputs/braking_distance_table.csv --output outputs/stage_a_basic_output.csv --log-output outputs/stage_a_basic_log.csv --charts-output outputs/stage_a_charts.html
```
