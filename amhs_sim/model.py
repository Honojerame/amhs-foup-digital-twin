from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class VehicleState(Enum):
    IDLE = auto()
    TO_PICKUP = auto()
    PICKING = auto()
    TO_DROPOFF = auto()
    DROPPING = auto()
    FAULT = auto()


@dataclass(frozen=True)
class Station:
    name: str
    position_m: float


@dataclass
class Foup:
    foup_id: str
    source: Station
    destination: Station
    picked: bool = False
    delivered: bool = False


@dataclass
class Motor:
    """Simple velocity-loop servo model with acceleration and speed limits."""

    max_speed_mps: float = 2.0
    max_accel_mps2: float = 1.25
    kp: float = 2.4
    velocity_mps: float = 0.0

    def update(self, position_m: float, target_m: float, dt_s: float) -> float:
        error = target_m - position_m
        desired_velocity = max(-self.max_speed_mps, min(self.max_speed_mps, self.kp * error))
        acceleration = max(
            -self.max_accel_mps2,
            min(self.max_accel_mps2, (desired_velocity - self.velocity_mps) / dt_s),
        )
        self.velocity_mps += acceleration * dt_s
        return position_m + self.velocity_mps * dt_s


@dataclass
class Hoist:
    """Microcontroller-facing lift actuator with limit-switch interlocks."""

    travel_s: float = 1.2
    elapsed_s: float = 0.0
    active: bool = False

    def start(self) -> None:
        self.active = True
        self.elapsed_s = 0.0

    def update(self, dt_s: float) -> bool:
        if not self.active:
            return False
        self.elapsed_s += dt_s
        if self.elapsed_s >= self.travel_s:
            self.active = False
            return True
        return False


@dataclass
class Telemetry:
    time_s: float
    vehicle: str
    state: str
    position_m: float
    velocity_mps: float
    target_m: float
    foup_id: str

