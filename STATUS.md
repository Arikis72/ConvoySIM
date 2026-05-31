---
title: ConvoySIM — Current Status
type: status
date: 2026-05-30
description: Snapshot of current ConvoySIM implementation state, open items, and last verified test run. Update this snapshot each session — do not append history here.
tags: [convoysim, status]
related: ["[[AGENTS]]", "[[requirements_traceability]]", "[[known_issues]]", "[[TASKS]]"]
---

# ConvoySIM — Current Status

> **Snapshot only.** Replace this content each session. History lives in `progress.md`.
> Last updated: 2026-05-31

---

## Implementation state

| Stage | Status | Notes |
|-------|:------:|-------|
| Stage A — Basic simulation (CLI + output CSV + HTML charts) | ✅ | All follower logic, orange/red/FORT, TimeHeadway, SAFETY_LOCK implemented |
| Stage A — GUI (Parameters, Scenario, Output, Log tabs) | ✅ | Editable params + scenario, bulk, cost weight tabs; UI/UX review done 2026-05-31 |
| Stage B — Parameter optimization (sweep + bulk simulations) | ✅ | Single-parameter bulk runs; multi-parameter optimization is future work |
| Stage C — Visualization popup | ✅ | Full playback, gap/velocity charts, state-machine Help; UI/UX review done 2026-05-31 |

**Test suite:** Last run 2026-05-31 — 93 tests; 4 failures + 32 errors are pre-existing (missing `Inputs/stage_a_example_inputs/parameters.csv` and `braking_distance_table.csv` — path mismatch in test fixtures, not introduced by this session). No new failures. See `test_strategy.md` for module coverage.

**Requirements:** See `requirements_traceability.md` for REQ ID status. Open items: REQ-25 (leader resume after comms override — frozen; true pause/stop for real-time mode). REQ-21-07 through REQ-21-14 added and implemented this session. REQ-21-14 pending manual UI/UX review.

---

## Open blockers

- None blocking current functionality.
- REQ-25-01 (leader resume after comms override) is **frozen** by user decision — not in scope until further notice.
- REQ-25-02 (true pause/stop for real-time sim mode) open — needs user scoping.
- Pre-existing test failures: `Inputs/stage_a_example_inputs/` missing `parameters.csv` and `braking_distance_table.csv` — test fixture path mismatch, not a simulation bug.

---

## Known issues (summary)

See `known_issues.md` for full entries. Active:
- BUG-001 🔴: Leader resume behavior after communication override undefined (frozen — no action until user decides).
- BUG-002 🔴: True pause/stop controls do not interrupt in-progress Stage A simulation run.

Closed this session:
- BUG-C03 ✅: 7 UI/UX issues from manual review (2026-05-31) — all fixed (REQ-21-07 to REQ-21-13).

---

## Do not change without explicit request

- Do not ignore `SimRequirements.md` behavioral specs.
- Do not make broad architecture changes without updating `PLANNING.md`, `decisions.md`, and getting user approval.
- Do not remove or overwrite documentation files without explicit approval.

---

## Next recommended action

Consider adding more Stage B cost functions (safety violations, full stops, oscillations). Or address the pre-existing test fixture path mismatch for `Inputs/stage_a_example_inputs/`.
