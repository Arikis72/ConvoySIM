---
title: ConvoySIM — Agent Operating Contract
type: instructions
date: 2026-05-30
description: Canonical agent operating contract for ConvoySIM. Loaded by Cursor natively. Claude Code must be pointed here by CLAUDE.md. Single source of truth — no rules are restated elsewhere.
tags: [convoysim, agent-instructions, closed-loop, cursor, claude-code]
related: ["[[SimRequirements]]", "[[requirements_traceability]]", "[[ConvoyLogic]]", "[[STATUS]]", "[[known_issues]]"]
---

# ConvoySIM — Agent Operating Contract

> Single source of truth for how AI agents work in this project. Loaded by Cursor natively.
> Claude Code: see `CLAUDE.md` — it points here as its first action.
> No rules are duplicated in any other file.

---

## 0. Role

You develop ConvoySIM in a **closed loop**:

**Requirement → Clarify → Plan → Implement → Test → Debug → Fix → Regress → Validate → Document → Update memory → Verify completion**

Operate autonomously through this loop. The **one human checkpoint** is **UI/UX correctness during testing** — pause and ask the user at that point only.

---

## 1. Session start (do this first, every session)

Read in this order:

1. This file (you are here)
2. `STATUS.md` — current snapshot
3. `requirements_traceability.md` — open requirements and their status
4. `TASKS.md` — open tasks and discovered issues
5. `known_issues.md` — open bugs and regression guards

Then post a **4-point session summary**:
- (a) Current implementation state
- (b) Open requirements (⏳ / ⚠️)
- (c) Open blockers
- (d) What you intend to do this session

---

## 2. Context-loading tiers

| Tier | Files | When to load |
|------|-------|-------------|
| **Always (Tier 1)** | This file, `STATUS.md`, `requirements_traceability.md`, `TASKS.md` | Every session |
| **On demand (Tier 2–3)** | `SimRequirements.md` (full spec), `PLANNING.md`, `test_strategy.md`, `known_issues.md`, `decisions.md`, `ConvoyLogic.md` | When relevant to the task |
| **Rarely (Tier 4)** | `progress.md`, `archive/*`, `CHANGELOG.md` | Only when specifically needed |

Never bulk-load Tier 4. `SimRequirements.md` is the spec bible — load the relevant section(s), not the whole 26-section doc unless necessary.

---

## 3. Requirement handling

Every requirement has a **REQ ID** (e.g. `REQ-09-01`) and a status:

| Status | Meaning |
|--------|---------|
| ⏳ | Open — not yet implemented |
| ✅ | Done — implemented + test evidence |
| ⚠️ | Partial — started or blocked |
| ❌ | Failing — regression detected |

**When you act on a requirement, update its status row in `requirements_traceability.md` in the same response.**

Ambiguity → add to the **Open Questions** block and batch-ask once. Do not silently guess at requirement intent.

Every new user requirement must be:
1. Added to `SimRequirements.md` (or recorded as open question if not yet clear)
2. Added to `requirements_traceability.md` with a REQ ID
3. Tracked in `TASKS.md` until complete

---

## 4. Planning

Before coding:
- Restate the REQ ID(s) and acceptance criteria you are satisfying
- List the minimal file changes needed
- Note any risks or behavioral side-effects

Do **not** rename public functions, classes, files, or data structures unless the task explicitly requires it. Do **not** change simulation behavior unless requirements clearly support the change.

---

## 5. Implementation

- Smallest change that satisfies the acceptance criteria
- Keep simulation/physics logic separate from GUI, file I/O, and reporting
- Validate inputs before running simulation logic
- Prefer simple, readable code over clever code
- Add comments only where the logic is non-obvious
- Do not add heavy dependencies without explicit approval (project uses pure stdlib + tkinter)

---

## 6. Testing

Run the full suite before ending any session:

```powershell
# From C:\dev\ConvoySIM
$env:PYTHONPATH = "src"; python -m unittest discover -s tests
```

Quick syntax check for a single changed file:

```powershell
python -m py_compile <changed_file.py>
```

Rules:
- The **full suite must be green** before you end a session
- Any new behavior needs a **test mapped to its REQ ID** (document the mapping in `test_strategy.md`)
- **Never skip or disable tests** to make the bar green
- If tests cannot run, state exactly what was not run, why, and the risk

---

## 7. Debugging

On any failure:
1. Find the **root cause** (not a symptom patch)
2. Record it in `known_issues.md` as a `BUG-NNN` entry with:
   - Symptom
   - Root cause
   - Fix applied
   - Regression guard (test or explicit check) added

---

## 8. Fix validation

A fix is **not done** until:
- The specific failing test(s) pass
- The full suite is green
- The requirement row in `requirements_traceability.md` is updated to ✅
- A regression guard exists in `known_issues.md`

---

## 9. Regression

Before declaring a session complete:
- Full suite green ✅
- All `known_issues.md` regression guards pass ✅
- No previously-✅ requirement has regressed ✅

If `ConvoyLogic.md` behavior was changed, update it to match the new behavior.

---

## 10. Documentation & memory (session end)

| File | What to update |
|------|---------------|
| `STATUS.md` | Current snapshot only — replace the snapshot, don't append history |
| `progress.md` | Append a dated entry (one paragraph per session) |
| `decisions.md` | Record any non-obvious design decision or tradeoff |
| `TASKS.md` | Move completed items to `archive/tasks_completed.md`; add new discovered issues |
| `requirements_traceability.md` | Mark satisfied REQs ✅ with test evidence |
| `ConvoyLogic.md` | Update if convoy behavior logic changed |

---

## 11. Completion criteria

Do **NOT** say "done" unless all of the following are true:
- Every in-scope REQ is ✅ in `requirements_traceability.md` with test evidence
- Full suite is green
- No open blocker in `known_issues.md`
- `STATUS.md` snapshot is updated
- `progress.md` entry appended

---

## 12. Ask vs. continue

**ASK the user for:**
- UI/UX correctness during testing (the sanctioned human checkpoint)
- Ambiguous or conflicting requirements
- Destructive actions (deleting files, renaming public APIs, changing established behavior)
- Scope changes
- Security-relevant decisions

**CONTINUE independently for:**
- Work with a clear acceptance criterion
- Refactoring within established patterns
- Fixing a failing test with a known root cause
- Documenting assumptions as you go

---

## 13. Hard rules

- **Never guess** at requirement intent — ask or record as open question
- **Never skip or disable tests** to make the suite pass
- **Never delete files** without listing them and getting explicit confirmation — archive instead
- **Never lose a requirement** — every user requirement gets a REQ ID and traceability row
- **Never duplicate rules** across files — this file is the single source of truth
- **Never commit secrets** — check `.gitignore` before any commit

---

## 14. Stack, module map & commands

### Stack
- Language: Python (pure stdlib + tkinter — no heavy dependencies without approval)
- Tests: `unittest` (discover pattern)
- GUI: `tkinter` (stdlib)
- Data: CSV files for inputs/outputs

### Module map
| Path | Purpose |
|------|---------|
| `src/convoysim/` | Main simulation + GUI package |
| `tests/` | `unittest` test suite |
| `Inputs/` | CSV input files (parameters, scenario, braking table, bulk scenarios) |
| `Bulk_Scenarios/` | Scenario CSVs for bulk simulation runs |
| `outputs/` | Generated output CSVs, log CSVs, HTML charts |
| `SimRequirements.md` | Full specification (26 sections — source of truth for behavior) |
| `ConvoyLogic.md` | Living summary of current implemented convoy behavior |
| `requirements_traceability.md` | REQ ID → status → test evidence mapping |
| `known_issues.md` | Open bugs, debug notes, regression guards |
| `test_strategy.md` | Test suite structure, coverage → REQ mapping |

### Key commands (run from `C:\dev\ConvoySIM`)
```powershell
# Run full test suite
$env:PYTHONPATH = "src"; python -m unittest discover -s tests

# Run simulation (CLI)
$env:PYTHONPATH = "src"; python -m convoysim --parameters Inputs/stage_a_example_inputs/parameters.csv --scenario Inputs/stage_a_example_inputs/scenario_timeline.csv --braking-table Inputs/stage_a_example_inputs/braking_distance_table.csv

# Launch GUI
$env:PYTHONPATH = "src"; python -m convoysim.gui

# Syntax check a single file
python -m py_compile src/convoysim/<file>.py
```

### Requirements reference
- `SimRequirements.md` §1–§26 — full specification
- `requirements_traceability.md` — REQ ID status + test evidence (update this, not SimRequirements.md, for status)
- `ConvoyLogic.md` — update whenever convoy behavior changes
