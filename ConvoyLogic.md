---
title: ConvoySIM — Convoy Behavior Logic
type: guide
date: 2026-05-22
description: Plain-language summary of current three-truck convoy behavior for users and maintainers. SimRequirements.md is the formal source of truth.
tags: [convoysim, logic, guide]
related: ["[[SimRequirements]]", "[[AGENTS]]", "[[STATUS]]"]
---

# ConvoyLogic.md

This file summarizes the current convoy behavior in plain language. Keep it updated whenever follower logic, scenario events, or logic-related output fields change.

`SimRequirements.md` remains the formal source of truth. This file is a readable guide for users and future maintainers.

## Convoy Structure

- Truck #1 is the leader.
- Truck #2 follows Truck #1.
- Truck #3 follows Truck #2.
- Truck #1 follows the scenario velocity profile.
- Follower trucks react to the truck directly ahead using perceived gap, perceived leading-truck velocity, tracking state, and configured thresholds.

## Main Inputs

Key parameters used by the follower logic:

- `Minimum allowed gap distance`: safety minimum.
- `Maximum allowed gap distance`: upper valid gap.
- `Red distance`: gap threshold for red braking.
- `Orange distance`: fixed orange trigger gap when orange mode is fixed.
- `Orange braking mode`: `0` = fixed, `1` = TimeHeadway.
- `TimeHeadway`: seconds used in TimeHeadway orange mode.
- `Orange deceleration`: fallback orange braking deceleration.
- `Max red deceleration`: fallback red braking deceleration.
- `Emergency deceleration`: deceleration used by `FORT activated`.
- `Start moving gap`: initial-start gap threshold; default is `8 m`.
- `Start moving identification delay`: delay used only when tracking resumes while the follower is still moving.
- `Distance identification delay`: continuous perception delay for follower decisions.

## Perception Delay

Followers do not react to perfect live data. They use delayed perceived values from:

```text
current_time - Distance identification delay
```

This affects measured gap, perceived leading position, perceived leading velocity, and decision making.

## Orange Trigger Gap

The simulator continuously computes `orange_trigger_gap` for each follower.

Fixed mode:

```text
orange_trigger_gap = Orange distance
```

TimeHeadway mode:

```text
orange_trigger_gap = follower_velocity_mps * TimeHeadway + Minimum allowed gap distance
```

In TimeHeadway mode, this is the continuous target gap throughout the simulation, starting from the initial gaps.

## Normal Following

When tracking is available and no higher-priority condition is active:

- If the gap is greater than `orange_trigger_gap`, the follower accelerates or resumes normal following.
- If the gap is acceptable, the follower tries to match the truck-ahead speed.
- Follower velocity is capped by `Max velocity`; Truck #1 is not capped by this parameter.

## Orange Braking

Orange braking starts when:

```text
gap <= orange_trigger_gap
```

On orange entry:

- The follower stores an orange target velocity equal to `75%` of its current velocity.
- The follower decelerates using the orange braking-table value when available.
- If the braking table has no matching value, it uses `Orange deceleration`.

While in orange behavior:

- If follower speed is above the stored 75% target, it continues orange deceleration.
- If the 75% target is reached and `gap <= orange_trigger_gap`, it holds current speed.
- If `gap > orange_trigger_gap`, orange behavior ends and the follower accelerates or follows normally.
- If `gap <= Red distance`, red braking overrides orange behavior.

## Red Braking

Red braking starts when:

```text
gap <= Red distance
```

Once red braking starts:

- It continues until follower velocity reaches `0`.
- It uses the red braking-table value when available.
- If the braking table has no matching value, it uses `Max red deceleration`.

## FORT Activated

Scenario timelines may include `FORT activated` in `Truck1_Event`, `Truck2_Image_Event`, or `Truck3_Image_Event`.

### Truck #1 (Leader)

When a `FORT activated` event appears in `Truck1_Event`:

- The trigger **latches permanently** — once activated, it cannot be cancelled.
- Truck #1 applies `Emergency deceleration` continuously until it reaches 0 velocity.
- After stopping, Truck #1 holds at 0 velocity for the remainder of the scenario.
- The leader profile velocity schedule is **completely ignored** after FORT — even if the scenario specifies a non-zero velocity at a later time.
- Truck #1 state and command are set to `FORT_EMERGENCY_DECEL` / "FORT emergency deceleration" from the trigger point onwards.

### Truck #2 and Truck #3 (Followers)

When a `FORT activated` event appears in `Truck2_Image_Event` or `Truck3_Image_Event`:

- The event applies only to the truck whose column contains it.
- The follower applies `Emergency deceleration`.
- This has higher priority than red and orange behavior for that command step.

## Start Movement

Initial first movement at simulation start is special.

A stopped follower starts its first movement only when:

- `gap > Start moving gap`, and
- followed-truck velocity is greater than `1 m/s`, and
- visual tracking is available.

This first-start rule applies only before the follower has moved for the first time.

After tracking resume:

- `Start moving identification delay` applies only if tracking resumes while the follower is still moving.
- If the follower fully stopped, identification resume alone does not automatically restart it.

## Image Identification Loss

Image identification can be lost by:

- a scenario `Loss` event, or
- distance-threshold logic when the gap exceeds the image-identification loss distance.

When tracking is lost:

- The follower freezes the followed truck's front position at the moment of loss.
- The follower targets the frozen rear position of the truck ahead.
- The follower decelerates to reach that frozen target at `0` velocity.
- It does not predict where the followed truck will continue moving.

For distance-caused loss:

- Tracking can resume when the live gap is less than or equal to the resume distance.
- If tracking resumes before the frozen target is reached, loss-target braking stops.
- If the follower reaches the frozen target and the live gap is still above resume distance, it remains stopped.

If the follower is stopped under image-identification loss for 30 seconds without resume, it enters `SAFETY_LOCK`.

## Communication

Communication is controlled by `Trucks communicating`.

When communication is off:

- Each follower reacts only to its own local tracking and follower logic.

When communication is on:

- A follower with tracking loss can request trucks ahead to slow down or stop.
- Communication reliability is deterministic in the current simulator:
  - `0%` progresses to failed fallback.
  - `1-99%` retries before approval.
  - `100%` approves after the initial send period.

Leader resume after communication override remains an open detailed behavior.

## Command Priority

Follower command selection uses this priority order:

1. Lost tracking and safety-lock behavior.
2. `FORT activated` emergency deceleration.
3. Red braking to full stop.
4. Orange braking or orange hold at the 75% target speed.
5. Start, accelerate, or match-speed behavior.

## Output Fields

The output CSV includes logic review fields such as:

- actual and measured gaps,
- follower states and commands,
- tracking status,
- loss source,
- frozen loss target rear positions,
- `Truck2_Orange_Trigger_Gap_m`,
- `Truck3_Orange_Trigger_Gap_m`,
- `Orange_Braking_Mode`,
- communication status,
- violation type,
- stop reason.

## Visualization

Stage C visualization shows:

- truck positions and velocities,
- actual gap arrows,
- orange trigger gap arrows above the actual gap arrows,
- tracking/loss/braking status,
- red and orange status styling,
- lost-target markers during image-identification loss.

In TimeHeadway mode, the fixed `Orange distance` label is replaced with TimeHeadway/target-gap context because the required gap changes continuously.

## Maintenance Rule

When convoy behavior changes:

1. Update `SimRequirements.md` first.
2. Update this file with the user-facing explanation.
3. Update tests for the changed behavior.
4. Update `STATUS.md`, `TASKS.md`, `CHANGELOG.md`, and `progress.md`.
