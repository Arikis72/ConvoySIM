---
title: ConvoySIM — Test Strategy
type: test-strategy
date: 2026-05-30
description: How the ConvoySIM test suite is structured, what it covers, how to run it, and how tests map to requirements.
tags: [convoysim, testing, test-strategy]
related: ["[[AGENTS]]", "[[requirements_traceability]]", "[[known_issues]]"]
---

# ConvoySIM — Test Strategy

> See [[AGENTS]] §6 for the testing rules (suite must be green before ending a session).
> See [[requirements_traceability]] for REQ ID → test evidence mapping.

---

## How to run

```powershell
# Full suite (run from C:\dev\ConvoySIM)
$env:PYTHONPATH = "src"; python -m unittest discover -s tests

# Full suite with verbose output
$env:PYTHONPATH = "src"; python -m unittest discover -s tests -v

# Single test module
$env:PYTHONPATH = "src"; python -m unittest tests.test_simulation -v

# Specific test
$env:PYTHONPATH = "src"; python -m unittest tests.test_simulation.SimulationTest.test_truck1_fort_latches_to_full_stop_and_does_not_resume -v

# Quick syntax check (no runtime needed)
python -m py_compile src/convoysim/<file>.py
```

**Last confirmed full run:** 2026-05-28 — ~91 tests passing.

---

## Test modules and REQ coverage

| Test module | Tests (approx.) | Requirements covered |
|-------------|:--------------:|---------------------|
| `test_braking.py` | ~5 | REQ-14 (braking-distance table load + interpolation) |
| `test_charts.py` | ~5 | REQ-20 (Stage A HTML chart output) |
| `test_gui_helpers.py` | ~15 | REQ-21 (GUI helpers: parameter grouping, filtering, log sorting, state-machine help, scenario dropdowns) |
| `test_leader_profile.py` | ~5 | REQ-08 (leader velocity profile loading + interpolation) |
| `test_optimization.py` | ~10 | REQ-22 (Stage B sweep, bulk simulations, cost functions) |
| `test_parameters.py` | ~5 | REQ-06 (parameter loading + validation) |
| `test_physics.py` | ~5 | REQ-15 (motion physics, velocity clamp) |
| `test_run_config.py` | ~8 | REQ-21-06 (INI persistence, scenario-name, file memory) |
| `test_scenario_timeline.py` | ~8 | REQ-08, REQ-18 (scenario-timeline CSV loading + event parsing) |
| `test_simulation.py` | ~15 | REQ-09–REQ-13, REQ-16–REQ-17 (follower control, image-id loss, FORT, SAFETY_LOCK, state machine) |
| `test_validation_and_geometry.py` | ~5 | REQ-02–REQ-03, REQ-24 (convoy geometry, validation helpers) |
| `test_visualization.py` | ~25 | REQ-23 (Stage C visualization helpers: gap arrows, orange-trigger arrows, chart segments, legend, label lanes, playback math) |

---

## Coverage gaps

| Area | Gap | Priority |
|------|-----|:--------:|
| GUI end-to-end (Bulk Simulation tab, Cost Weight tab, Stage C popup layout) | No automated test — requires manual UI/UX review | 🔴 human checkpoint |
| Stage A HTML chart visual rendering | Automated test checks data; visual layout requires manual review | 🟡 |
| Communication probabilistic behavior | Deterministic runner only; §25 open questions must be resolved first | ⏳ |
| Multi-parameter Stage B optimization | Not yet implemented | ⏳ |

---

## Rules for adding new tests

1. Every new behavior must have a test mapped to its REQ ID.
2. Test name must be descriptive: `test_<what>_<condition>_<expected>`.
3. Add the REQ → test mapping to `requirements_traceability.md` in the same commit.
4. Tests must not depend on external files that may not exist — use minimal in-memory fixtures.
5. If a bug is fixed, add a regression guard test and record it in `known_issues.md`.
