---
title: Three-Truck Convoy Simulation Requirements
type: requirements
date: 2026-05-22
description: Formal requirements for the three-truck convoy simulator covering convoy structure, physics, follower state machine, communication, GUI, Stage B optimization, and Stage C visualization.
tags: [convoysim, requirements]
related: ["[[ConvoyLogic]]", "[[AGENTS]]", "[[STATUS]]", "[[TASKS]]"]
---

# Three-Truck Convoy Simulation Requirements

## 1. Document purpose

This document defines the requirements for a simulator that models the current behavior of a three-truck convoy.

The simulator shall represent the current convoy logic, not a future optimized controller. The purpose is to expose where the current logic causes unsafe gaps, unnecessary stops, excessive braking, poor recovery after image-identification loss, communication-related behavior changes, or physically impossible follower behavior.

The simulator shall be parameter-driven so that dynamic parameters, control thresholds, communication settings, road type, timing resolution, and input scenarios can be changed easily through the GUI.

---

## 2. Convoy structure

The convoy contains three trucks:

```text
Truck #1 -> Truck #2 -> Truck #3
```

Truck #1 is the leader and is tele-operated based on cellular communication.

Truck #2 follows Truck #1 autonomously using camera-based image processing.

Truck #3 follows Truck #2 autonomously using camera-based image processing.

Each follower reacts only to the truck directly ahead of it for start/stop following behavior:

```text
Truck #2 follows Truck #1.
Truck #3 follows Truck #2.
```

Truck #3 shall not start based directly on Truck #1 movement. Truck #3 starts based on Truck #2 movement only.

---

## 3. Coordinate system, positions, and gap definitions

### 3.1 Origin

The simulation origin is defined as:

```text
Truck #3 front bumper position at t = 0 equals 0 m.
```

All truck positions in the output shall be relative to this origin.

### 3.2 Reported position

The reported position of each truck shall be the front bumper position.

### 3.3 Truck length

All trucks shall initially use the same truck length parameter:

```text
Truck length [m]
```

Future versions may support different truck lengths per truck, but the first version shall assume one shared truck length.

### 3.4 Gap definition

The gap between two trucks is measured from:

```text
rear bumper of leading truck -> front bumper of following truck
```

Therefore:

```text
Gap #2 = Truck #1 rear bumper position - Truck #2 front bumper position
Gap #3 = Truck #2 rear bumper position - Truck #3 front bumper position
```

Using front bumper positions and common truck length:

```text
Gap #2 = Truck #1 front position - Truck length - Truck #2 front position
Gap #3 = Truck #2 front position - Truck length - Truck #3 front position
```

### 3.5 Initial conditions

The initial conditions do not require explicit initial positions for all trucks if the following are provided:

- Truck length.
- Initial gap between Truck #1 and Truck #2.
- Initial gap between Truck #2 and Truck #3.
- Initial velocity of each truck.

Because the origin is Truck #3 front bumper at `t = 0`, positions can be derived:

```text
Truck #3 front position = 0
Truck #2 front position = Truck length + Initial gap #3
Truck #1 front position = Truck #2 front position + Truck length + Initial gap #2
```

The simulator shall validate that the supplied initial gaps and truck length produce physically valid initial positions.

---

## 4. Units

The simulator shall use the following units:

| Quantity | Unit |
|---|---|
| Time | seconds |
| Delay | milliseconds in input, converted to seconds internally |
| Velocity | kph in input/output, converted to m/s internally |
| Acceleration | m/s^2 |
| Deceleration | m/s^2, represented internally as negative acceleration |
| Distance | meters |
| Position | meters |
| Communication reliability | percent |

---

## 5. Simulation timing

The simulation shall support configurable timing parameters:

| Parameter | Examples | Description |
|---|---:|---|
| Simulation time step | 1.0 s, 0.5 s, 0.1 s | Internal calculation step |
| Output table resolution | 1.0 s, 0.5 s, 0.1 s | Time interval for table output |

The output table resolution may be equal to or larger than the internal simulation time step.

When the simulation ends, the final truck states shall be frozen. Frozen state includes at least:

- position,
- velocity,
- acceleration command,
- state-machine state,
- tracking status,
- communication status,
- latest measured gaps,
- violation flags.

---

## 6. Truck dynamic parameters

The first version shall use the same dynamic parameters for all trucks. Future versions may allow truck-specific parameters.

| Parameter | Unit | Description |
|---|---:|---|
| Max velocity | kph | Maximum allowed follower truck velocity; Truck #1 leader velocity is defined by the scenario profile and is not capped by this parameter |
| Max acceleration | m/s^2 | Maximum allowed positive acceleration |
| Max red deceleration | m/s^2 | Emergency deceleration limit, used only if table-based braking is not active |
| Minimum allowed gap distance | m | Gap below this value is a minimum-gap violation |
| Maximum allowed gap distance | m | Gap above this value is a maximum-gap violation |
| Red distance | m | Gap below this value triggers red braking |
| Orange distance | m | Gap below this value triggers orange deceleration |
| Start moving identification delay | ms | Delay before follower detects that the truck ahead has started moving |
| Distance identification delay | ms | Continuous delay applied to perceived distance, position, velocity, and classification |
| Truck image identification loss distance | m | If gap exceeds this value, visual tracking is lost |
| Truck image identification resume distance | m | If gap is reduced to this value or below, visual tracking can resume |
| Under-loss following truck velocity | kph | Safe velocity used by a follower after image-identification loss |
| Under-loss leading truck velocity | kph | Safe velocity used by trucks ahead when communication is active |
| Trucks communicating | Yes/No | Enables or disables inter-truck communication behavior |
| Communication latency | ms | Current value: 200 ms |
| Communication reliability | % | Probability that a communication message/approval succeeds |
| Convoy target speed | kph | Default value: 10 kph |
| Target gap | m | Default value: 10 m |
| Road type | text | Gravel, Asphalt, or Dust road |

---

## 7. Optimization and tunable logic parameters

The following parameters are used by the current simulation logic and shall be easily editable. They may later be used by the Stage B optimizer.

| Parameter | Unit | Description |
|---|---:|---|
| Orange deceleration | m/s^2 | Controlled deceleration used when gap is below orange distance, unless table-based braking overrides it |
| Orange distance | m | Gap threshold for controlled deceleration |
| Orange braking mode | 0/1 | `0` = fixed Orange distance; `1` = TimeHeadway mode |
| TimeHeadway | s | Time headway used when Orange braking mode is `1` |
| Emergency deceleration | m/s^2 | Emergency deceleration applied when `FORT activated` is triggered |
| Green acceleration | m/s^2 | Acceleration used when the follower resumes movement |
| Start moving gap | m | Minimum measured gap required before a stopped follower starts moving |
| Optimal acceleration | m/s^2 | Future tuning parameter used for closing gaps and leader behavior |
| Target gap | m | Desired nominal convoy gap; default 10 m |

The formal cost function for optimization is not yet defined.

When optimization is later implemented, the priority order shall be:

1. Never violate the minimum gap.
2. Avoid unnecessary full stops.
3. Reduce acceleration/deceleration oscillations.

Any parameter set that causes collision or minimum-gap violation shall be considered invalid for optimization purposes.

---

## 8. Leader driving profile

Truck #1 shall receive a velocity profile input table in CSV format:

```csv
Time_s,Velocity_kph
0,0
1,5
2,10
```

Between profile points, Truck #1 velocity shall be linearly interpolated.

Before starting the simulation, the simulator shall validate the leader profile. If the input profile demands acceleration or deceleration beyond the defined physical limits, the simulator shall alert the user during validation.

For follower trucks, impossible behavior shall not block the simulation. Instead, physically impossible follower behavior shall be reported as a violation flag in the simulation output.

---

## 9. Current follower control logic

The follower logic shall represent the current system behavior.

Each follower shall use the following perceived values:

- delayed measured gap,
- delayed measured leading-truck position,
- delayed visual classification,
- delayed leading-truck velocity,
- calculated relative velocity.

The distance identification delay shall be applied continuously. The follower uses the perceived situation from:

```text
t - distance_identification_delay
```

The follower shall calculate relative velocity:

```text
Relative velocity = follower velocity - leading truck velocity
```

Relative velocity may be used by the current logic, but braking decisions are based on red distance and the configured orange trigger gap, not predicted stopping distance.

### 9.1 Current threshold rules

| Condition | Behavior |
|---|---|
| Gap > orange trigger gap | Accelerate / resume normal following |
| Gap <= orange trigger gap | Enter or continue orange behavior |
| Gap <= red distance | Trigger red braking |
| Red braking triggered | Continue braking until full stop |
| Gaps are acceptable | Try to match truck-ahead speed for continuous convoy drive |
| Convoy target speed | Default 10 kph |
| Target gap | Default 10 m, editable parameter |

Orange trigger gap behavior:

- In fixed mode, `orange_trigger_gap = Orange distance`.
- In TimeHeadway mode, `orange_trigger_gap = follower velocity [m/s] * TimeHeadway + Minimum allowed gap distance`.
- In TimeHeadway mode, `orange_trigger_gap` is continuously recalculated and acts as the target gap throughout the simulation, starting from the initial gaps.
- When orange braking starts, the follower stores a target velocity equal to 75% of the follower velocity at orange entry.
- The follower decelerates with the orange braking-table deceleration, or the configured orange fallback deceleration, until reaching the 75% target velocity.
- If the follower reaches the 75% target velocity while the gap is still less than or equal to `orange_trigger_gap`, it holds its current speed.
- If the gap becomes greater than `orange_trigger_gap`, orange behavior ends and normal acceleration/following resumes.
- If the gap reaches red distance, red braking overrides orange behavior and continues to 0 velocity.

---

## 10. Start-moving logic

A stopped follower shall not start immediately when the truck ahead moves.

The follower starts only when all the following conditions are true:

1. During initial simulation start only, the truck ahead velocity is greater than 1 m/s.
2. During initial simulation start only, the measured gap is greater than the configured start moving gap.
3. For later resume while the follower is still moving, the start-moving identification delay has passed.
4. Visual tracking is available.
5. The motion is physically possible within the defined acceleration limits.

If tracking resumes while the follower has fully stopped, identification resume alone shall not automatically restart it.

The start moving gap shall be selected so that the follower does not violate:

- minimum allowed gap,
- maximum allowed gap,
- truck image identification loss distance.

The default `Start moving gap` is 8 m.

---

## 11. Image-identification loss logic

Image-identification loss can occur in two ways:

1. From the Truck #2 or Truck #3 image-identification loss input table.
2. Automatically when the gap exceeds the truck image identification loss distance.

When identification is lost, the current required logic is:

```text
The following truck continues autonomously toward the leading truck location at the moment identification was lost.
```

This means:

- the follower freezes the last known target position,
- the follower does not estimate or predict the continuing motion of the leading truck,
- the follower remembers the last measured gap,
- the follower continues driving toward the frozen target position,
- the follower decelerates to reach the frozen target position at 0 velocity,
- for distance-caused loss, if live image identification resumes because the live gap is less than or equal to the resume distance while driving to the target, the follower stops loss-target braking and resumes tracking,
- for distance-caused loss, if the follower reaches the frozen target and the live gap to the truck ahead is still greater than the resume distance, the follower remains stopped,
- the follower does not stop due to timeout alone except for the 30-second resume rule.

### 11.1 Image-identification resume logic

Tracking shall resume according to the logic conditions, even if the loss event table does not explicitly contain a resume event.

Resume behavior:

- If tracking is lost because the gap exceeded the identification loss distance, tracking can resume when the live gap is less than or equal to the truck image identification resume distance, including while the follower is still driving toward the loss target.
- If a forced loss event occurs while the truck is closer than the truck image identification loss distance, then tracking shall resume within 2 seconds, unless other loss conditions still apply.
- If tracking does not resume within 30 seconds after the follower has stopped under image-identification loss, the follower shall enter Safety Lock.
- The input loss table may include a resume image-tracking event, but this is optional. The convoy behavior shall still follow the logic conditions.

The 30-second stop shall be logged as a specific stop reason.

---

## 12. Communication logic

Communication is an optional mode controlled by:

```text
Trucks communicating = Yes/No
```

### 12.1 Communication OFF

When communication is OFF:

- Truck #1 follows the scenario velocity profile.
- Truck #2 and Truck #3 react only through their local visual tracking and current follower logic.
- A follower cannot request the leader or any truck ahead to slow down or stop.

### 12.2 Communication ON

When communication is ON:

- communication is all-to-all,
- trucks can update each other with gap and velocity data,
- a follower can request the leading truck or trucks ahead to reduce speed or stop and wait,
- communication can override the leader profile.

Messages include:

| Message | Meaning |
|---|---|
| lost | Image identification was lost |
| resume | Image tracking resumed |
| gap | Current gap update |
| velocity | Current velocity update |

### 12.3 Communication latency and reliability

Communication latency is currently:

```text
200 ms
```

Communication latency queue behavior shall be ignored for now.

Communication reliability behavior:

1. When a message is sent, the sender waits for approval.
2. If approval is not received within 400 ms, the message is resent.
3. If approval is not received within an additional 400 ms, the truck follows the logic as if communication is disabled.

### 12.4 Communication behavior during tracking loss

If Truck #2 loses tracking of Truck #1 and communication is ON:

- Truck #2 sends a loss message.
- Truck #1 is requested to stop using orange deceleration.
- If Truck #1 is already slower than the under-loss leading truck velocity, it maintains the current lower speed.

If Truck #3 loses tracking of Truck #2 and communication is ON:

- Truck #3 sends a loss message.
- Truck #2 is requested to stop using orange deceleration.
- Truck #1 is also notified and requested to stop using orange deceleration.
- This means Truck #2 stopping due to Truck #3 loss counts as a leader override for Truck #1 as well.

When tracking resumes:

- a resume message is sent,
- the leader resumes the scenario velocity profile using linear acceleration if needed,
- because communication may have changed the actual leader position, the rest of the leader behavior shall be linked to the original position according to the original simulation table.

### 12.5 Leader resume after communication override

The intended behavior is:

- The original leader scenario table defines the desired leader motion.
- If communication override slows or stops the leader, the leader's actual position no longer matches the original scenario position.
- After resume, the leader shall return to the scenario behavior using linear acceleration if needed.
- The continuation shall be linked to the original position according to the original simulation table.

This rule may require a precise implementation definition before coding.

---

## 13. Under-loss velocity behavior

### 13.1 Follower under-loss velocity

When a follower loses detection, the follower drives at the predefined under-loss following truck velocity, while still respecting the frozen target position and orange/red distance logic.

### 13.2 Leader under-loss velocity

When a follower loses detection and communication is ON, the trucks ahead use the under-loss leading truck behavior.

If the truck ahead is already moving slower than the under-loss leading truck velocity, it shall maintain the current lower speed and shall not accelerate to the under-loss velocity.

---

## 14. Braking-distance CSV table

The simulator shall support a braking-distance table in CSV format.

Required structure:

```csv
RoadType,BrakingType,Velocity,Distance_m
Gravel,Orange,5,2
Gravel,Orange,10,4
Gravel,Orange,15,9
Gravel,Red,5,0.5
Gravel,Red,10,3
Gravel,Red,15,7
```

### 14.1 Fields

| Field | Description |
|---|---|
| RoadType | Gravel, Asphalt, or Dust road |
| BrakingType | Orange or Red |
| Velocity | Initial velocity in kph |
| Distance_m | Physical braking distance in meters |

The braking-distance table is global, not per truck.

Interpolation between table values is allowed.

The table includes physical braking distance only. It does not include reaction delay.

The road type is constant during one simulation run but may be changed between simulation runs.

### 14.2 Deceleration calculation

The simulator shall calculate deceleration from braking distance using:

```text
a = -V0^2 / (2S)
```

Where:

- `a` is acceleration in m/s^2, negative for braking.
- `V0` is the initial speed in m/s.
- `S` is the braking distance in meters.

The `Velocity` column is stored in kph and shall be converted to m/s before calculating deceleration.

### 14.3 Red braking

Currently, if the red trigger occurs:

```text
gap < red distance
```

then red braking applies until full stop.

The red braking deceleration shall be calculated according to the braking-distance table for the selected road type and current velocity. If the table cannot provide a valid value, the simulator may fall back to the configured max red deceleration and must log a warning.

### 14.4 Orange braking

Orange braking uses the same CSV table structure with:

```text
BrakingType = Orange
```

The orange braking deceleration shall be calculated from the table using the current velocity and selected road type. If the table cannot provide a valid value, the simulator may fall back to the configured orange deceleration and must log a warning.

---

## 15. Motion physics

The simulator shall assume linear acceleration and deceleration over each simulation step.

The physics update shall respect:

- velocity cannot become negative,
- velocity cannot exceed max velocity,
- acceleration cannot exceed max acceleration,
- braking cannot exceed the selected braking/deceleration capability unless the scenario explicitly exposes it as impossible behavior,
- position is updated by integrating velocity over time,
- truck behavior must remain physical.

A standard constant-acceleration update may be used:

```text
position_next = position_current + velocity_current * dt + 0.5 * acceleration * dt^2
velocity_next = velocity_current + acceleration * dt
```

If `velocity_next` would become negative, it shall be clamped to zero and the position update shall account for the actual stopping time within the time step.

---

## 16. Violation definitions

The simulator shall separate violation types rather than using only one generic violation flag.

Required violation flags:

| Violation | Definition |
|---|---|
| Minimum gap violation | Gap < minimum allowed gap |
| Maximum gap violation | Gap > maximum allowed gap |
| Collision | Gap <= 0 |
| Image identification loss | Tracking lost due to event or distance |
| Image resume timeout | Tracking did not resume within 30 seconds |
| Impossible follower behavior | Current logic demands physically impossible follower behavior |
| Communication failure fallback | Communication approval failed twice and the truck reverted to non-communication logic |

The table may also include combined fields:

```text
Gap #2 violation = Yes/No
Gap #3 violation = Yes/No
Violation type #2
Violation type #3
```

---

## 17. Current-logic state machine

The simulator shall use a state machine that represents the current logic of the system, not an optimized future logic.

Each follower shall run its own state machine.

Truck #2 state machine follows Truck #1.

Truck #3 state machine follows Truck #2.

### 17.1 Required states

| State | Meaning |
|---|---|
| STOPPED_WAITING | Follower is stopped and waiting for valid start conditions |
| START_DELAY_COUNTING | Truck ahead moved and start delay timer is running |
| FOLLOWING_ACCELERATING | Gap is larger than acceleration threshold, so follower accelerates |
| FOLLOWING_MATCHING_SPEED | Gap is acceptable, so follower tries to match truck-ahead speed |
| FOLLOWING_ORANGE_DECEL | Gap is below orange distance, so follower decelerates |
| FOLLOWING_RED_BRAKING_TO_STOP | Gap is below red distance; braking continues until full stop |
| FORT_EMERGENCY_DECEL | FORT activated event applies emergency deceleration for the affected follower |
| TRACKING_LOST_TO_LAST_POSITION | Identification lost; follower drives toward the frozen last known rear end of the leading truck |
| TRACKING_RESUME_PENDING | Resume conditions are valid or forced resume timing is active |
| COMMUNICATION_REQUEST_STOP | Follower requests truck or trucks ahead to stop or reduce speed |
| IMMEDIATE_STOP_AFTER_LOSS_TIMEOUT | Tracking did not resume within 30 seconds |
| SAFETY_LOCK | Follower is stopped at the frozen target and identification did not resume within 30 seconds |
| VIOLATION_STATE | Collision, minimum-gap violation, or other invalid safety condition occurred |
| SIMULATION_FROZEN | Simulation ended and truck state is frozen |

### 17.2 State transitions

| From state | Condition | To state |
|---|---|---|
| STOPPED_WAITING | Truck ahead velocity > 0 | START_DELAY_COUNTING |
| START_DELAY_COUNTING | Delay passed + gap >= start moving gap + tracking valid | FOLLOWING_ACCELERATING |
| START_DELAY_COUNTING | Truck ahead stops before delay passed | STOPPED_WAITING |
| FOLLOWING_ACCELERATING | Gap enters acceptable range | FOLLOWING_MATCHING_SPEED |
| FOLLOWING_ACCELERATING | Gap < orange distance | FOLLOWING_ORANGE_DECEL |
| FOLLOWING_ACCELERATING | Gap < red distance | FOLLOWING_RED_BRAKING_TO_STOP |
| FOLLOWING_MATCHING_SPEED | Gap > 1.2 x orange distance | FOLLOWING_ACCELERATING |
| FOLLOWING_MATCHING_SPEED | Gap < orange distance | FOLLOWING_ORANGE_DECEL |
| FOLLOWING_MATCHING_SPEED | Gap < red distance | FOLLOWING_RED_BRAKING_TO_STOP |
| FOLLOWING_ORANGE_DECEL | Gap < red distance | FOLLOWING_RED_BRAKING_TO_STOP |
| FOLLOWING_ORANGE_DECEL | Gap returns to acceptable range | FOLLOWING_MATCHING_SPEED |
| Any following state | Tracking lost | TRACKING_LOST_TO_LAST_POSITION |
| TRACKING_LOST_TO_LAST_POSITION | Tracking resume conditions met | TRACKING_RESUME_PENDING |
| TRACKING_LOST_TO_LAST_POSITION | Loss braking stops the follower and identification is still lost | Remain in state, hold stopped |
| TRACKING_LOST_TO_LAST_POSITION | Stopped under image-identification loss for 30 s without identification resume | SAFETY_LOCK |
| TRACKING_RESUME_PENDING | Tracking confirmed | FOLLOWING_MATCHING_SPEED or FOLLOWING_ACCELERATING based on gap |
| FOLLOWING_RED_BRAKING_TO_STOP | Velocity = 0 | STOPPED_WAITING |
| IMMEDIATE_STOP_AFTER_LOSS_TIMEOUT | Velocity = 0 | STOPPED_WAITING |
| Any state | Collision or minimum-gap violation | VIOLATION_STATE |
| Any state | Simulation end | SIMULATION_FROZEN |

### 17.3 State-to-command mapping

| State | Command |
|---|---|
| STOPPED_WAITING | Hold velocity at 0 |
| START_DELAY_COUNTING | Hold velocity at 0 |
| FOLLOWING_ACCELERATING | Accelerate using green acceleration or optimal acceleration, limited by max acceleration |
| FOLLOWING_MATCHING_SPEED | Match truck-ahead speed, limited by acceleration constraints |
| FOLLOWING_ORANGE_DECEL | Decelerate using orange braking table or orange deceleration |
| FOLLOWING_RED_BRAKING_TO_STOP | Red brake until full stop using red braking table or red deceleration fallback |
| TRACKING_LOST_TO_LAST_POSITION | Drive toward the followed-truck rear point or frozen leading-truck rear point and decelerate to reach that target at 0 velocity |
| TRACKING_RESUME_PENDING | Continue controlled behavior until resume is confirmed |
| COMMUNICATION_REQUEST_STOP | Send stop/reduce-speed request and wait for approval logic |
| IMMEDIATE_STOP_AFTER_LOSS_TIMEOUT | Stop immediately |
| SAFETY_LOCK | Apply parking brakes |
| VIOLATION_STATE | Freeze violation state and continue or stop according to simulation setting |
| SIMULATION_FROZEN | Hold final state |

### 17.4 Visualization help labels

The Stage C visualization and State Machine Help window shall explain the same tracking/status, command/action, and violation labels.

| Label group | Label | Meaning |
|---|---|---|
| Tracking/status state | Tracking | Image identification is valid and live following logic can use current measurements |
| Tracking/status state | Lost | Image identification is lost; visualization may show this as image identification loss |
| Tracking/status state | Resume pending | Image identification resume conditions are active but normal following has not fully resumed |
| Tracking/status state | Stopped waiting | Follower is stopped and waiting for valid start conditions |
| Tracking/status state | Start delay | Truck ahead moved and start delay timer is running |
| Tracking/status state | Tracking: Accelerate | Follower is tracking and accelerating to close an excessive gap |
| Tracking/status state | Tracking: Match speed | Follower is tracking and matching truck-ahead speed |
| Tracking/status state | Tracking: Orange braking | Follower is tracking and applying orange braking |
| Tracking/status state | Tracking: Red braking | Follower is tracking and applying red braking |
| Tracking/status state | Image identification loss | User-facing description of `Lost` tracking status and `TRACKING_LOST_TO_LAST_POSITION` behavior |
| Tracking/status state | Safety Lock | Follower is stopped at the frozen target and parking brakes are applied after the no-resume timeout |
| Tracking/status state | Leader stopped | Leader truck is stopped |
| Tracking/status state | Leader accelerating | Leader truck is accelerating according to the leader profile |
| Tracking/status state | Leader decelerating | Leader truck is decelerating according to the leader profile |
| Tracking/status state | Leader cruising | Leader truck is following the leader profile speed |
| Command/action or violation | Hold stopped | Follower or leader is stopped and command is to remain stopped |
| Command/action or violation | Match speed | Follower tries to match truck-ahead speed |
| Command/action or violation | Accelerate | Follower accelerates to close an excessive gap |
| Command/action or violation | Orange braking | Follower applies orange deceleration |
| Command/action or violation | Red braking | Follower applies red braking until full stop |
| Command/action or violation | Comm stop | Follower requests stop/reduce-speed action through communication logic |
| Command/action or violation | Lost: target stop | Follower is under image loss and decelerates to reach the frozen loss target at 0 velocity |
| Command/action or violation | Lost: hold velocity | Follower is under image loss and holds current velocity because no deceleration is required yet |
| Command/action or violation | Lost: safe velocity | Follower continues under image loss using the configured safe-loss behavior |
| Command/action or violation | Leader accelerating | Leader applies leader-profile acceleration |
| Command/action or violation | Leader decelerating | Leader applies leader-profile deceleration |
| Command/action or violation | Leader cruising | Leader follows leader-profile speed |
| Command/action or violation | Apply parking brakes | Safety lock command applies parking brakes |
| Command/action or violation | Minimum gap violation | Gap is below the minimum allowed distance |
| Command/action or violation | Maximum gap violation | Gap is above the maximum allowed distance |
| Command/action or violation | Collision | Gap is zero or negative |
| Command/action or violation | Communication failure fallback | Communication approval failed and fallback logic is used |
| Command/action or violation | Impossible follower behavior | Current logic demands physically impossible follower behavior |

---

## 18. Simulation input files

All input files shall be CSV.

### 18.1 Scenario timeline

The scenario timeline file shall combine the leader velocity profile and follower image-identification loss/resume events so users can plan one simulation scenario in a single table.

Required structure:

```csv
Time_s,Truck1_Velocity_kph,Truck2_Image_Event,Truck3_Image_Event,Notes
0.0,0.0,,,Leader starts stopped
2.0,5.0,,,Leader accelerates
12.0,,Loss,,Truck #2 loses image identification of Truck #1
18.0,,Resume,,Truck #2 image identification resumes
30.0,,,Loss,Truck #3 loses image identification of Truck #2
35.0,,FORT activated,,Truck #2 applies emergency deceleration
```

Rules:

- `Time_s` is required and must be strictly increasing.
- `Truck1_Velocity_kph` is optional per row. Non-empty values define leader velocity profile points and are linearly interpolated between points.
- `Truck2_Image_Event` and `Truck3_Image_Event` are optional per row. Valid values are blank, `Loss`, `Resume`, or `FORT activated`.
- Blank event cells mean no new image-identification event at that time.
- `Notes` is optional and ignored by the simulation logic.
- A `Resume` event is optional because the simulator shall also resume tracking based on logic conditions.
- A `FORT activated` event applies the configured emergency deceleration to the truck whose event column contains it.

### 18.2 Braking-distance table

```csv
RoadType,BrakingType,Velocity,Distance_m
Gravel,Orange,5,2
Gravel,Orange,10,4
Gravel,Orange,15,9
Gravel,Red,5,0.5
Gravel,Red,10,3
Gravel,Red,15,7
```

---

## 19. Stage A output table

Stage A shall generate a simulation table.

The minimum required output columns are:

| Column | Description |
|---|---|
| Time_s | Simulation time |
| Truck1_Position_m | Truck #1 front bumper position relative to origin |
| Truck2_Position_m | Truck #2 front bumper position relative to origin |
| Truck3_Position_m | Truck #3 front bumper position relative to origin |
| Truck2_Gap_m | Gap between Truck #1 rear bumper and Truck #2 front bumper |
| Truck3_Gap_m | Gap between Truck #2 rear bumper and Truck #3 front bumper |
| Gap2_Violation | Yes/No |
| Gap3_Violation | Yes/No |

Recommended additional output columns:

| Column | Description |
|---|---|
| Truck1_Velocity_kph | Truck #1 velocity |
| Truck2_Velocity_kph | Truck #2 velocity |
| Truck3_Velocity_kph | Truck #3 velocity |
| Truck1_Acceleration_mps2 | Truck #1 acceleration |
| Truck2_Acceleration_mps2 | Truck #2 acceleration |
| Truck3_Acceleration_mps2 | Truck #3 acceleration |
| Truck1_State | Truck #1 leader state |
| Truck2_State | Truck #2 state-machine state |
| Truck3_State | Truck #3 state-machine state |
| Truck1_Command | Truck #1 leader command |
| Truck2_Command | Truck #2 current command |
| Truck3_Command | Truck #3 current command |
| Truck2_Loss_Source | Scenario or Distance source for Truck #2 image-identification loss |
| Truck3_Loss_Source | Scenario or Distance source for Truck #3 image-identification loss |
| Truck2_Loss_Target_Rear_m | Frozen rear target position used by Truck #2 during image-identification loss |
| Truck3_Loss_Target_Rear_m | Frozen rear target position used by Truck #3 during image-identification loss |
| Truck2_Orange_Trigger_Gap_m | Orange trigger/target gap used by Truck #2 |
| Truck3_Orange_Trigger_Gap_m | Orange trigger/target gap used by Truck #3 |
| Orange_Braking_Mode | Orange braking mode used for the row |
| Truck2_Actual_Gap_m | Truck #2 true physical gap |
| Truck2_Measured_Gap_m | Truck #2 delayed perceived gap |
| Truck3_Actual_Gap_m | Truck #3 true physical gap |
| Truck3_Measured_Gap_m | Truck #3 delayed perceived gap |
| Truck2_Tracking_Status | Tracking / Lost / Resume pending |
| Truck3_Tracking_Status | Tracking / Lost / Resume pending |
| Truck2_Relative_Velocity_kph | Truck #2 velocity minus Truck #1 velocity |
| Truck3_Relative_Velocity_kph | Truck #3 velocity minus Truck #2 velocity |
| Communication_Message | None / Lost / Resume / Stop request |
| Communication_Status | Disabled / Sent / Approved / Retried / Failed fallback |
| Violation_Type_Truck2 | Specific violation type |
| Violation_Type_Truck3 | Specific violation type |
| Stop_Reason_Truck2 | Reason for stop |
| Stop_Reason_Truck3 | Reason for stop |

---

## 20. Stage A charts

Stage A shall include chart review in pop-up windows. The chart windows shall support at least:

- save as,
- zoom,
- pan.

Required charts:

### 20.1 Gap vs time

Show:

- Gap #2,
- Gap #3,
- minimum allowed gap,
- red distance,
- orange distance,
- maximum allowed gap,
- truck image identification loss distance,
- truck image identification resume distance.

### 20.2 Velocity, detection, and command vs time

Show for all trucks:

- velocity,
- detection/tracking status,
- acceleration/braking command.

Recommended additional charts:

- position vs time,
- truck state timeline,
- communication event timeline,
- actual gap vs measured delayed gap.

---

## 21. Stage A GUI requirements

Stage A shall include a GUI.

The GUI shall support:

### 21.1 Parameter handling

- Upload parameter CSV files.
- Edit simulation parameters directly in the GUI.
- Save edited parameters to the current parameter CSV.
- Save edited parameters as a new parameter CSV.
- Filter parameters by substring so users can find a parameter by partial text.
- Clear the active parameter filter.
- Group parameters visually by sub-category while preserving the parameter CSV format.
- Validate parameters before running the simulation.
- Show validation errors, warnings, and routine feedback in a non-modal status line when possible.
- If the Parameters tab has unsaved changes when Start Simulation is clicked, display an inline warning and block execution. The user must save the Parameters tab before running.

### 21.2 Input file handling

- Upload scenario timeline CSV containing leader velocity and follower image-identification events.
- Load scenario timeline CSV files through the Scenario file Browse button.
- Display the selected scenario name as a header in the main GUI and Stage C visualization window.
- View and edit the selected scenario timeline directly in the GUI.
- Save edited scenarios to the current scenario CSV.
- Save edited scenarios as a new scenario CSV.
- Insert scenario rows.
- Delete selected scenario rows.
- Use controlled dropdown values for `Truck2_Image_Event` and `Truck3_Image_Event`: blank, `Loss`, `Resume`, or `FORT activated`.
- Scenario Save and Save As buttons shall be disabled when no unsaved changes exist in the scenario editor. They become enabled only after a cell edit, row insert, or row delete.
- Upload braking-distance CSV table.
- Clear stale output and log views when a new parameter, scenario, or braking table input is selected.

### 21.3 Simulation execution controls

The GUI shall include:

- Start simulation button.
- Pause simulation button.
- Stop simulation button.

When Stop is used or when the simulation naturally ends, truck states shall be frozen.

### 21.4 Output review

The GUI shall include:

- simulation output table,
- chart pop-up windows,
- log window.

Output review behavior:

- Output table columns should be grouped by truck where practical.
- Numeric output table values should be presented in compact review format.
- Chart and visualization controls should be available only when simulation results exist from the current session. On GUI startup, Open Visualization and Open Charts buttons shall be disabled even if a previous output file exists on disk; they become enabled only after a successful Start Simulation run in the current session.
- Stage C visualization popup should allow dragging the horizontal divider between the truck visualization and chart area to zoom the charts vertically.
- Stage C visualization popup should remember the truck/chart divider position in `convoysim.ini` for future uses.
- State Machine Help should include a search field that filters all help tables by substring.
- State Machine Help wording should match the Stage C visualization tracking/status and command/action/violation wording so users can correlate labels directly.
- GUI action buttons should be colored for better visibility; file Browse buttons should remain uncolored/default.
- Stage C truck body colors should use identity colors: Truck #1 black, Truck #2 blue, and Truck #3 orange.
- Stage C should draw an upper status rectangle above each truck: same as truck color for normal status, dotted border for image identification loss, orange fill for orange braking, and red fill for red braking or safety violation.
- Stage C gap review should use separate `Gap1-2` and `Gap2-3` charts.
- Stage C gap chart Y-axis shall be capped at 120% of the maximum gap value in the simulation, with a hard upper limit of 40 m. This prevents unnecessarily large scales during image-identification loss events.
- Stage C gap chart segment styling should match the truck/status visual rules: normal truck color, dotted for image identification loss, orange for orange braking, and red for red braking or safety violation.
- Stage C popup charts should show time tick marks every 1 second and numeric time labels every 10 seconds along their x axes.
- Stage C popup chart y-axis tick numbers should be displayed with zero decimal places.
- Stage C gap arrows and values should be positioned at the top of the upper truck status rectangles.
- Stage C road view should show distance tick marks below the road line every 10 m.
- Stage C main truck rectangles should be 25% shorter than the previous main rectangle height so gap labels do not overlap status labels.
- Stage C lost-target markers should distinguish the source of image-identification loss: scenario-driven loss uses an empty triangle, and distance-threshold loss uses a filled triangle.
- Stage C lost-target markers should use explicit frozen loss-target output columns when available instead of reconstructing targets from sampled replay rows.
- Stage C legends should explain empty and filled lost-target triangles.
- Stage C visualization should display configured image-identification loss and resume distances below the orange/red distance labels.
- Routine save/run/open feedback should use a main-window status line instead of requiring modal OK dialogs.
- Stage C popup and Bulk visualization popup legend (Toggle Legend) shall always be fully visible when shown. It shall be packed above the visualization pane so that it takes space from the pane rather than being obscured by it on small screens.
- The Stage C "status / command / violation" rotated Y-axis label shall remain within the visible canvas area at all supported canvas heights.
- Stage C popup and Bulk visualization popup shall support keyboard shortcuts: left arrow = jump back 1 second, right arrow = jump forward 1 second, Home = jump to simulation start, End = jump to simulation end.

The log window shall report:

- validation warnings,
- communication messages,
- image loss and resume events,
- braking events,
- stop reasons,
- violation events,
- physically impossible follower behavior,
- fallback events due to communication failure.

Log review behavior:

- Log rows should be sorted by time and truck order where practical.
- Log rows should visually distinguish Truck #1, Truck #2, Truck #3, and general messages.

---

## 22. Stage B optimization

Stage B shall perform convoy optimization by testing parameter values and comparing results.

The optimization shall use the current-logic state machine unless a new future-control logic is explicitly defined.

Initial optimization parameters may include:

- orange deceleration,
- orange distance,
- green acceleration,
- start moving gap,
- optimal acceleration,
- target gap.

Stage B shall support a Bulk simulations workflow.

Bulk simulations v1 behavior:

- The GUI shall include a `Bulk simulations` button that opens/selects a Bulk Simulation tab.
- Predefined bulk scenarios shall live in a `Bulk_Scenarios` folder.
- The last selected bulk scenarios folder shall be remembered in `convoysim.ini` and used as the next default.
- The Bulk Simulation tab shall allow selecting one or more scenario CSV files from that folder.
- The scenario list shall include `Select all` and `Unselect all` controls.
- The user shall select one optimization parameter at a time.
- When an optimization parameter is selected, the Bulk Simulation tab shall show that parameter's current default value from the loaded parameters CSV next to the parameter dropdown.
- The user shall define an inclusive parameter range using minimum value, maximum value, and step.
- The min, max, and step fields shall be positioned close to the parameter dropdown.
- A progress bar shall appear to the right of the parameter range fields.
- The `Start bulk simulation` and `Cancel` buttons shall be centered in the Bulk Simulation tab controls area.
- The user shall select one or more cost functions from a list next to the bulk scenarios list.
- The cost-function list shall include `Select all` and `Unselect all` controls.
- The GUI shall include a browseable Cost Function Weights CSV path so the user can select one of several weight sets.
- The main Input and Output Files section shall use two columns to reduce vertical space.
- The `Start bulk simulation` button shall be enabled only when enough valid inputs are selected.
- The bulk runner shall execute every selected scenario once per generated parameter value.
- The GUI shall show bulk-run progress and support cancelling a long bulk run.

Bulk simulations v1 cost function:

- The first cost function shall be `Red braking count`.
- Red braking count shall count red-braking event transitions per follower truck.
- Truck #2 and Truck #3 counts shall be stored separately.
- The displayed cost value shall be the total red-braking count across Truck #2 and Truck #3.
- A second cost function shall be `Accidents`.
- An accident starts when a following truck front position is greater than or equal to the rear position of the truck ahead.
- For Truck #2, the accident condition is Truck #2 front position >= Truck #1 rear position.
- For Truck #3, the accident condition is Truck #3 front position >= Truck #2 rear position.
- While the accident condition remains true across multiple output rows, it shall count as one accident.
- The accident finishes when the following truck front position becomes lower than the rear position of the truck ahead.
- Accident counts shall be stored separately for Truck #2 and Truck #3, and the displayed cost value shall be the total accident count across both follower trucks.
- All selected scenarios shall have equal weight.
- The best parameter value for an individual selected cost function is the value with the lowest total event count for that cost function.
- A parameter value with event count `0` is considered successful for that individual cost function.
- When multiple cost functions are selected, the bulk run shall compute all selected cost functions for the same simulation output rows.
- Cost-function weights shall be loaded from `CostFunctionWeights.csv` or the user-selected weights file.
- The cost-function weights file shall include `Cost_Function` and `Weight` columns.
- `Total_Weighted_Cost` shall be the sum of each selected cost-function total multiplied by its configured weight.
- Only cost functions selected for the bulk run shall contribute to `Total_Weighted_Cost`.
- A missing selected cost-function weight shall fail the bulk run with a clear error.
- Later versions may add more cost functions, including safety violations and other comfort metrics.

Bulk simulations v1 output:

- Each individual simulation run shall save its own output CSV.
- One bulk run shall create one output subfolder under `outputs` named:

```text
<cost functions>_<ddmmyy_hhmm>
```

- The bulk summary shall be saved as `Bulk_Results.csv` in the same folder.
- `Bulk_Results.csv` shall include at least scenario name, parameter name, parameter value, total weighted cost, run status, Truck #2 red-braking count, Truck #3 red-braking count, total red-braking count, Truck #2 accident count, Truck #3 accident count, total accident count, run-output CSV path, and failure reason when status is `Failed`.
- The selected cost-function weights shall be copied into the bulk output folder for traceability.
- Bulk results shall open in a separate popup window containing the result chart and table.
- The results popup shall show total cost function value vs parameter value with one line per selected cost function.
- The results popup shall show `Total weighted cost` in a separate chart.
- The charts shall include titles and top-right legends outside the plotted data area.
- Weighted chart value labels shall use plain integer formatting when values are whole numbers.
- The results popup shall provide buttons to save each chart as an automatically named JPG in the bulk output folder.
- The results table columns shall auto-resize to the popup width, with wrapped headers when needed.
- Clicking a chart point shall highlight the selected point and show all scenarios for that parameter value in the table below the chart.
- Scenarios that triggered the selected cost function for the clicked parameter value shall be shown with red text.
- Scenarios that did not trigger the selected cost function shall remain visible so the user can double-click and inspect their behavior too.
- Double-clicking a completed bulk run output row shall open a new independent visualization window for that specific simulation output CSV.
- Repeated double-clicks shall allow multiple bulk visualization windows to stay open at the same time for comparison.
- Each bulk visualization window shall keep independent playback state, charts, time slider, and header.
- The visualization header for a bulk run shall include the scenario name, parameter value, and cost function name.

Hard constraints:

- no collision,
- no minimum-gap violation.

Optimization priorities:

1. Never violating minimum gap.
2. Avoiding unnecessary full stops.
3. Reducing acceleration/deceleration oscillations.

---

## 23. Stage C visual real-time simulation

Stage C shall provide a visual real-time simulation of the convoy.

The visual simulation shall show:

- Truck #1, Truck #2, and Truck #3 positions,
- current gaps,
- truck velocities,
- tracking status,
- state-machine state,
- braking/acceleration command,
- communication messages,
- violations.

The visual simulation shall show actual gap arrows and orange-trigger-gap arrows so the user can compare actual gap versus required gap for each follower. Orange-trigger arrows shall be vertically separated to avoid overlap. The Truck #1-to-Truck #2 required-gap value shall be shown below its arrow, without a `Req` prefix. In fixed orange mode, the trigger gap equals `Orange distance`. In TimeHeadway mode, the fixed Orange distance label is not relevant; the visualization shall show TimeHeadway/target-gap context instead of emphasizing the fixed Orange distance.

---

## 24. Validation requirements

Before the simulation starts, the simulator shall validate:

- leader velocity profile acceleration and deceleration feasibility,
- initial gaps and truck length consistency,
- CSV file format and required columns,
- road type exists in braking-distance table,
- braking type exists in braking-distance table,
- parameter numeric ranges,
- timing parameters are positive,
- output resolution is compatible with simulation time step,
- communication reliability is between 0 and 100 percent,
- truck image identification resume distance and loss distance are valid numeric values.

The simulator shall warn, but not necessarily block, if:

- maximum allowed gap is greater than image identification loss distance,
- start moving gap appears likely to violate max gap or image-identification loss distance,
- follower behavior becomes impossible under the selected acceleration/deceleration limits.

Impossible follower behavior during the run shall be reported as a violation flag.

---

## 25. Open implementation questions

The requirements are mostly defined, but the following points should be clarified before coding detailed behavior:

1. Leader resume after communication override:
   - The requirement says the leader resumes the scenario velocity profile using linear acceleration if needed, and the rest of the leader behavior is linked to the original position according to the original simulation table.
   - This needs an exact algorithm: should the leader seek the original scenario position curve, the original scenario velocity at the current time, or the nearest future point on the original position profile?

2. Loss event file:
   - The proposed file supports `Loss` and optional `Resume` events.
   - Confirm whether multiple loss/resume cycles per truck are allowed.

3. Violation-state behavior:
   - Should the simulation continue after a collision/minimum-gap violation for analysis, or stop immediately?

4. Orange/red braking table interpolation:
   - Confirm whether interpolation should clamp outside table velocity range or produce a validation warning.

5. Communication reliability:
   - Confirm whether the reliability percentage applies to the original message, approval message, or the full message-approval transaction.

6. Immediate stop after 30-second tracking timeout:
   - Confirm whether "stops immediately" means infinite/instant stop in the model or maximum physical braking.

7. SIMULATION_FROZEN state:
   - Confirm whether frozen states should still be displayed in the output table after the end time, or only retained internally.

---

## 26. Development approach

The recommended implementation order is:

1. Build Stage A GUI and parameter/input loading.
2. Implement input validation.
3. Implement leader profile interpolation.
4. Implement physics update.
5. Implement follower state machine.
6. Implement image loss/resume logic.
7. Implement communication ON/OFF logic.
8. Generate output table.
9. Generate charts.
10. Add start/pause/stop simulation control.
11. Add Stage B optimization later.
12. Add Stage C real-time visual simulation later.

The first working version should focus on correctness, traceability, and explainability rather than optimization.
