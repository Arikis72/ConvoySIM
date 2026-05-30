---
title: ConvoySIM
type: readme
date: 2026-05-30
description: ConvoySIM — 3-truck convoy simulation with Stage A (basic sim + GUI), Stage B (parameter optimization + bulk), and Stage C (real-time visualization).
tags: [convoysim, readme]
related: ["[[AGENTS]]", "[[SimRequirements]]", "[[STATUS]]", "[[docs/feature_guide]]"]
---

# ConvoySIM

> Full feature reference: [[docs/feature_guide]] · Behavior spec: [[SimRequirements]] · Agent contract: [[AGENTS]] · Current state: [[STATUS]]

ConvoySIM simulates a 3-truck convoy (Truck #1 leader + Trucks #2–#3 followers) with image-identification loss/resume, communication logic, orange/red braking, FORT, SAFETY_LOCK, and Stage B parameter optimization.

---

## Quick start

```powershell
# Run from C:\dev\ConvoySIM

# Full test suite
$env:PYTHONPATH = "src"; python -m unittest discover -s tests

# CLI simulation
$env:PYTHONPATH = "src"; python -m convoysim --parameters Inputs/stage_a_example_inputs/parameters.csv --scenario Inputs/stage_a_example_inputs/scenario_timeline.csv --braking-table Inputs/stage_a_example_inputs/braking_distance_table.csv

# GUI
$env:PYTHONPATH = "src"; python -m convoysim.gui
```

---

## Project files

| File / Folder | Purpose |
|---|---|
| `SimRequirements.md` | Full specification (26 sections — source of truth for behavior) |
| `AGENTS.md` | Agent operating contract (session start, workflow, testing, completion criteria) |
| `CLAUDE.md` | Claude Code pointer stub → reads `AGENTS.md` |
| `.cursor/rules/always.mdc` | Cursor pointer → reads `AGENTS.md` |
| `requirements_traceability.md` | REQ ID → status → test evidence |
| `STATUS.md` | Current snapshot (replace each session) |
| `TASKS.md` | Open tasks and discovered issues |
| `known_issues.md` | Bugs, debug notes, regression guards |
| `test_strategy.md` | Test suite structure and REQ coverage |
| `PLANNING.md` | Architecture and data flow |
| `decisions.md` | Design decisions and rationale |
| `ConvoyLogic.md` | Living summary of current implemented convoy behavior |
| `progress.md` | Session-by-session progress diary |
| `docs/feature_guide.md` | Detailed feature reference (CLI, GUI, Stage B, Bulk, Stage C) |
| `src/convoysim/` | Main simulation + GUI package |
| `tests/` | `unittest` test suite |
| `Inputs/` | CSV input files |
| `Bulk_Scenarios/` | Scenario CSVs for bulk simulation |
| `outputs/` | Generated CSVs, log CSVs, HTML charts |

---

## Development workflow

1. Read `AGENTS.md` (or let your tool load it automatically).
2. Post the 4-point session summary (see `AGENTS.md` §1).
3. Work the closed loop: Requirement → Plan → Implement → Test → Debug → Document.
4. Before ending: suite green, `STATUS.md` updated, `progress.md` entry appended.

See `docs/feature_guide.md` for detailed CLI/GUI usage.
