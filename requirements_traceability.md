---
title: ConvoySIM — Requirements Traceability
type: traceability
date: 2026-05-30
description: REQ ID to status to test evidence mapping for ConvoySIM. Derived from SimRequirements.md sections 1–26. Update this file (not SimRequirements.md) when requirement status changes.
tags: [convoysim, requirements, traceability]
related: ["[[SimRequirements]]", "[[AGENTS]]", "[[test_strategy]]", "[[known_issues]]"]
---

# ConvoySIM — Requirements Traceability

> **Source of truth for behavior:** `SimRequirements.md` (26 sections)
> **Update here (not in SimRequirements.md) when status changes.**
> Statuses: ⏳ open · ✅ done (with test evidence) · ⚠️ partial · ❌ failing

---

## REQ ID scheme

`REQ-{section}-{item}` — e.g. `REQ-09-01` = SimRequirements.md §9, item 1.
Section-level entries cover the whole section when items are not yet individually numbered.

---

## Traceability table

| REQ ID | Section | Description | Status | Test evidence | Open questions |
|--------|---------|-------------|:------:|--------------|----------------|
| REQ-02 | §2 Convoy structure | 3-truck convoy (Truck 1 leader, Trucks 2–3 followers), truck dimensions, initial gaps | ✅ | `tests/` — basic structure tests | — |
| REQ-03 | §3 Coordinate system | Position/gap definitions, Truck #3 front bumper as origin | ✅ | `tests/` | — |
| REQ-04 | §4 Units | All units defined (m, m/s, s, m/s²) | ✅ | Implicit in all tests | — |
| REQ-05 | §5 Simulation timing | Fixed time step, duration | ✅ | `tests/` | — |
| REQ-06 | §6 Truck dynamic parameters | Max velocity, acceleration limits, truck length, braking params | ✅ | `tests/` — parameter validation | — |
| REQ-07 | §7 Optimization parameters | Tunable logic params for Stage B | ✅ | `tests/` — Stage B tests | — |
| REQ-08 | §8 Leader driving profile | Scenario-timeline CSV loading, velocity interpolation | ✅ | `tests/` — scenario loader tests | — |
| REQ-09-01 | §9 Follower control — start delay | Start delay before follower begins moving | ✅ | `tests/` | — |
| REQ-09-02 | §9 Follower control — orange braking | Orange trigger gap, TimeHeadway mode, decel to 75% speed | ✅ | `tests/` — orange braking tests | — |
| REQ-09-03 | §9 Follower control — red braking | Red threshold, braking to 0, FORT emergency decel | ✅ | `tests/` | — |
| REQ-09-04 | §9 Follower control — max velocity cap | `Max velocity` applies to followers only; Truck #1 uncapped | ✅ | `tests/` | — |
| REQ-10 | §10 Start-moving logic | Initial-start rules (gap check before moving) | ✅ | `tests/` | — |
| REQ-11-01 | §11 Image-id loss — scenario-driven | Loss/resume events from `scenario_timeline.csv` | ✅ | `tests/` | — |
| REQ-11-02 | §11 Image-id loss — distance-based | Optional `Resume by distance` parameter | ✅ | `tests/` | — |
| REQ-11-03 | §11 Image-id loss — frozen target | Target frozen rear point; decelerate to 0 at target | ✅ | `tests/` — frozen target tests | — |
| REQ-11-04 | §11 Image-id loss — SAFETY_LOCK | 30 s timeout → SAFETY_LOCK state | ✅ | `tests/` | — |
| REQ-12 | §12 Communication logic | ON/OFF comm, sent/retried/approved/failed fallback, stop requests | ✅ | `tests/` | REQ-12 open questions in §25 |
| REQ-13 | §13 Under-loss velocity | Velocity behavior during image-id loss state | ✅ | `tests/` | — |
| REQ-14 | §14 Braking-distance table | CSV table load, interpolation, fallback with warning | ✅ | `tests/` — braking table tests | — |
| REQ-15 | §15 Motion physics | Constant-acceleration stepping, velocity clamp at 0 | ✅ | `tests/` | — |
| REQ-16 | §16 Violations | Violation detection and output column | ✅ | `tests/` | — |
| REQ-17 | §17 State machine | State transitions matching state-machine spec | ✅ | `tests/` — state machine tests | — |
| REQ-18 | §18 Input files | `scenario_timeline.csv`, `parameters.csv`, `braking_distance_table.csv` formats | ✅ | `tests/` — loader tests | — |
| REQ-19 | §19 Stage A output | All output columns present, correct types and naming | ✅ | `tests/` — output column tests | — |
| REQ-20 | §20 Stage A charts | HTML chart with labeled axes, legend, bold/dotted segments | ✅ | Manual review (chart rendering) | — |
| REQ-21-01 | §21 GUI — Parameters tab | Editable params table, sub-category grouping, filter, save/save-as | ✅ | `tests/` — GUI helper tests | UI/UX review needed |
| REQ-21-02 | §21 GUI — Scenario tab | Editable scenario, insert/delete row, dropdown image events, save/save-as | ✅ | `tests/` — GUI helper tests | UI/UX review needed |
| REQ-21-03 | §21 GUI — Output Table tab | Truck-grouped columns, one-decimal formatting | ✅ | `tests/` | — |
| REQ-21-04 | §21 GUI — Log tab | Time-sorted, truck-colored rows, compact state icons | ✅ | `tests/` — log sorting tests | — |
| REQ-21-05 | §21 GUI — status line | Inline status (no modal message boxes) | ✅ | `tests/` | — |
| REQ-21-06 | §21 GUI — file memory | `convoysim.ini` remembers last paths, scenario name | ✅ | `tests/` | — |
| REQ-22 | §22 Stage B optimization | Parameter sweep, cost functions, bulk scenarios, results output | ✅ | `tests/` — Stage B/bulk tests | |
| REQ-23 | §23 Stage C visualization | Straight-line replay, playback controls, gap charts, velocity chart, Help | ✅ | `tests/` — Stage C helper tests | UI/UX review needed |
| REQ-24 | §24 Validation requirements | Validation steps before any release | ✅ | See `test_strategy.md` | — |
| REQ-25 | §25 Open questions | Leader resume behavior; true pause/stop for real-time mode | ⏳ | — | See §25 + TASKS.md active items |
| REQ-26 | §26 Development approach | Minimal changes, no silent behavior changes, req tracking | ✅ | Process — enforced via AGENTS.md | — |

---

## Open Questions (batch-ask list)

> Items needing user clarification before implementation. Agent: add here instead of guessing.

- REQ-25-01: What should leader behavior be after a communication override ends? (resume from position? speed? immediate?)
- REQ-25-02: Should true pause/stop controls for real-time simulation mode be a Stage A or Stage D item?

---

## Notes

- Status was initially assigned based on the TASKS.md completed-items list and STATUS.md working-behavior section as of 2026-05-30.
- Items marked ✅ without specific test citation → general suite coverage; see `test_strategy.md` for REQ-to-test mapping.
- UI/UX rows marked "UI/UX review needed" require the sanctioned human checkpoint (§0 of AGENTS.md) before being finalized ✅.
- `> ASSUMPTION:` Individual REQ IDs within sections have not been enumerated for §21–§23 GUI requirements — only section-level IDs assigned. Enumerate sub-items as new GUI requirements are added.
