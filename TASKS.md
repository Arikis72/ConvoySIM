---
title: ConvoySIM — Tasks
type: tasks
date: 2026-05-30
description: Open tasks and discovered issues for ConvoySIM. Completed tasks are in archive/tasks_completed.md. Keep this file open-only.
tags: [convoysim, tasks]
related: ["[[AGENTS]]", "[[requirements_traceability]]", "[[known_issues]]", "[[archive/tasks_completed]]"]
---

# ConvoySIM — Tasks

> Open tasks only. See [[archive/tasks_completed]] for history.
> When a task is complete: move it to `archive/tasks_completed.md` and update [[requirements_traceability]].

---

## Active tasks

- [ ] Review `SimRequirements.md` §25 and extract the open questions to the `requirements_traceability.md` Open Questions block.
- [ ] Define exact leader resume behavior after communication override (REQ-25-01 — needs user input).
- [ ] Implement true pause/stop controls for long-running/real-time simulation mode (REQ-25-02 — needs user scoping).
- [ ] Manual UI/UX review of Online Visualization popup: test all leader control buttons, undo/scrub, Resume from scrubbed position (gradual velocity convergence), Save As (with truck events), Back to Sim re-enable, leader rectangle colors (orange/red/FORT/normal), legend triangles, braking info placement (REQ-21-14 through REQ-21-21).
- [ ] Add additional Stage B cost functions for safety violations, full stops, and oscillations.
- [ ] Consider multi-parameter Stage B optimization after single-parameter bulk simulation performance is reviewed.

---

## Discovered issues

> Newly found bugs, gaps, and risks. Add a BUG-ID to `known_issues.md` for anything that needs a fix.

- [ ] `SimRequirements.md` §25 open questions still need answers before detailed communication and loss-timeout behavior is implemented (→ REQ-25).

---

## Requirement tracking workflow

Each new requirement must be tracked before or during implementation:

1. Add the requirement to `SimRequirements.md` (or record as open question if it needs clarification).
2. Add a REQ ID row to `requirements_traceability.md`.
3. Add a matching actionable item to this file.
4. When implemented, move the task to `archive/tasks_completed.md`.
5. Update `requirements_traceability.md` status to ✅ with test evidence.
6. Update `STATUS.md` snapshot and append a `progress.md` entry.
7. Record design decisions in `decisions.md`.

---

## Task update rules

- Move completed items to `archive/tasks_completed.md` (never delete).
- Add new issues under Discovered issues + create a BUG-ID in `known_issues.md`.
- Keep each task concrete and testable.
