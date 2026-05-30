"""Command-line entry point for ConvoySIM."""

from __future__ import annotations

from pathlib import Path
import argparse

from convoysim.charts import write_stage_a_charts_html
from convoysim.parameters import load_parameters_csv
from convoysim.run_config import (
    StageARunConfig,
    save_stage_a_run_config,
    timestamped_stage_a_paths,
)
from convoysim.simulation import run_basic_simulation_from_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a basic ConvoySIM Stage A simulation.")
    parser.add_argument(
        "--parameters",
        default="Inputs/stage_a_example_inputs/parameters.csv",
        help="Path to parameters CSV.",
    )
    parser.add_argument(
        "--scenario",
        default="Inputs/stage_a_example_inputs/scenario_timeline.csv",
        help="Path to scenario timeline CSV.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write the simulation output CSV. Defaults to <scenario>_output_<ddmmyy_hhmm>.csv.",
    )
    parser.add_argument(
        "--braking-table",
        default="Inputs/stage_a_example_inputs/braking_distance_table.csv",
        help="Optional path to braking-distance CSV.",
    )
    parser.add_argument(
        "--log-output",
        default=None,
        help="Path to write the simulation log CSV.",
    )
    parser.add_argument(
        "--charts-output",
        default=None,
        help="Path to write the Stage A chart HTML report.",
    )
    args = parser.parse_args()
    generated_paths = timestamped_stage_a_paths(args.scenario)
    output_path = Path(args.output) if args.output is not None else generated_paths.output_path
    log_output_path = Path(args.log_output) if args.log_output is not None else generated_paths.log_path
    charts_output_path = Path(args.charts_output) if args.charts_output is not None else generated_paths.charts_path

    result = run_basic_simulation_from_files(
        args.parameters,
        args.scenario,
        output_path,
        args.braking_table,
        log_output_path,
    )
    parameters = load_parameters_csv(args.parameters).simulation_parameters
    write_stage_a_charts_html(result, parameters, charts_output_path)
    save_stage_a_run_config(
        StageARunConfig(
            parameters_path=args.parameters,
            scenario_path=args.scenario,
            braking_table_path=args.braking_table,
            output_path=str(output_path),
            log_path=str(log_output_path),
            charts_path=str(charts_output_path),
        )
    )
    print(f"Wrote {len(result.rows)} output rows to {output_path}")
    print(f"Wrote {len(result.logs)} log rows to {log_output_path}")
    print(f"Wrote chart report to {charts_output_path}")


if __name__ == "__main__":
    main()
