# AMHS system architecture

This drawing separates the fab-level software, OHT embedded controller, physical
plant, and real-time digital-twin interface. The simulator preserves the same
command, feedback, and safety boundaries used in an industrial AMHS.

```mermaid
flowchart TB
  subgraph L4["Level 4 — Manufacturing operations"]
    MES["MES / lot scheduling"]
  end

  subgraph L3["Level 3 — Material control system"]
    REQ["Transport request API"]
    DISPATCH["FIFO FOUP dispatcher"]
    ROUTE["Station and route model"]
  end

  subgraph L2["Level 2 — OHT embedded controller"]
    FSM["Deterministic MCU state machine"]
    MOTION["Position-to-velocity loop"]
    SEQ["Hoist sequence controller"]
    SAFE["Safety interlock manager"]
  end

  subgraph L1["Level 1 — Drives and I/O"]
    VFD["Servo drive / motor"]
    HOIST["Hoist actuator"]
    ENC["Position encoder"]
    PE["Obstacle photoeye"]
    LS["Hoist limit switches"]
  end

  subgraph L0["Level 0 — Physical process"]
    RAIL["Overhead rail"]
    CARRIER["FOUP carrier"]
    PORT["Tool load port / stocker"]
  end

  subgraph DT["Digital twin and operator HMI"]
    PLANT["Discrete-time plant model"]
    SNAP["Thread-safe telemetry snapshot"]
    API["HTTP control + state API"]
    DASH["Browser control-room dashboard"]
  end

  MES --> REQ --> DISPATCH
  ROUTE --> DISPATCH -->|"transport job"| FSM
  FSM --> MOTION -->|"velocity command"| VFD --> RAIL
  FSM --> SEQ -->|"raise / lower"| HOIST --> CARRIER
  RAIL --> CARRIER --> PORT
  ENC -->|"position feedback"| MOTION
  PE --> SAFE
  LS --> SAFE
  SAFE -->|"enable / E-stop"| FSM

  VFD -. "simulated dynamics" .-> PLANT
  HOIST -. "simulated timing" .-> PLANT
  PLANT --> SNAP --> API --> DASH
  DASH -->|"pause, speed, reset, fault injection"| API
  API -->|"operator commands"| FSM
```

## Runtime data flow

```mermaid
sequenceDiagram
  participant UI as Browser HMI
  participant API as HTTP API
  participant Twin as LiveFab adapter
  participant MCU as OHT controller
  participant Plant as Motor + hoist plant

  loop Every 50 ms
    Twin->>MCU: deterministic control tick
    MCU->>Plant: velocity / actuator command
    Plant-->>MCU: position / completion feedback
  end
  loop Every 100 ms
    UI->>API: GET /api/state
    API->>Twin: snapshot under lock
    Twin-->>API: JSON plant state
    API-->>UI: vehicles, stations, FOUPs, metrics
  end
  UI->>API: POST /api/control (E-stop)
  API->>MCU: assert photoeye interlock
  MCU->>Plant: remove drive torque and stop hoist
```

## Control-state model

```mermaid
stateDiagram-v2
  [*] --> IDLE
  IDLE --> TO_PICKUP: dispatch FOUP
  TO_PICKUP --> PICKING: encoder at source
  PICKING --> TO_DROPOFF: hoist completion
  TO_DROPOFF --> DROPPING: encoder at destination
  DROPPING --> IDLE: transfer complete
  TO_PICKUP --> FAULT: safety interlock
  PICKING --> FAULT: safety interlock
  TO_DROPOFF --> FAULT: safety interlock
  DROPPING --> FAULT: safety interlock
  FAULT --> TO_PICKUP: reset, empty carrier
  FAULT --> TO_DROPOFF: reset, loaded carrier
```

## Design choices

- The simulation tick is deterministic and independent from browser polling.
- `LiveFab` is the synchronization boundary between plant state and HTTP threads.
- The dashboard has no third-party runtime dependencies; Python serves static
  assets and JSON using the standard library.
- Fault injection uses the same controller transition as a physical photoeye
  interlock, so the visualization exercises actual control logic rather than a
  cosmetic animation state.
