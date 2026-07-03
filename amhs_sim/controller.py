from __future__ import annotations

from dataclasses import dataclass, field

from .model import Foup, Hoist, Motor, Telemetry, VehicleState


@dataclass
class OhtController:
    """Embedded-style OHT state machine with drive and hoist control."""

    vehicle_id: str
    position_m: float = 0.0
    state: VehicleState = VehicleState.IDLE
    motor: Motor = field(default_factory=Motor)
    hoist: Hoist = field(default_factory=Hoist)
    job: Foup | None = None
    completed_jobs: int = 0
    fault_reason: str = ""

    @property
    def target_m(self) -> float:
        if self.job is None:
            return self.position_m
        if self.state in (VehicleState.TO_PICKUP, VehicleState.PICKING):
            return self.job.source.position_m
        return self.job.destination.position_m

    def dispatch(self, job: Foup) -> bool:
        if self.state is not VehicleState.IDLE:
            return False
        self.job = job
        self.state = VehicleState.TO_PICKUP
        return True

    def emergency_stop(self, reason: str) -> None:
        self.motor.velocity_mps = 0.0
        self.hoist.active = False
        self.fault_reason = reason
        self.state = VehicleState.FAULT

    def reset_fault(self) -> bool:
        if self.state is not VehicleState.FAULT:
            return False
        self.fault_reason = ""
        if self.job is None:
            self.state = VehicleState.IDLE
        else:
            self.state = VehicleState.TO_DROPOFF if self.job.picked else VehicleState.TO_PICKUP
        return True

    def update(self, time_s: float, dt_s: float) -> Telemetry:
        if self.state in (VehicleState.TO_PICKUP, VehicleState.TO_DROPOFF):
            previous = self.position_m
            self.position_m = self.motor.update(self.position_m, self.target_m, dt_s)
            reached = abs(self.position_m - self.target_m) < 0.03
            crossed = (previous - self.target_m) * (self.position_m - self.target_m) <= 0
            if reached or crossed:
                self.position_m = self.target_m
                self.motor.velocity_mps = 0.0
                self.hoist.start()
                self.state = (
                    VehicleState.PICKING
                    if self.state is VehicleState.TO_PICKUP
                    else VehicleState.DROPPING
                )
        elif self.state in (VehicleState.PICKING, VehicleState.DROPPING):
            if self.hoist.update(dt_s):
                if self.state is VehicleState.PICKING:
                    assert self.job is not None
                    self.job.picked = True
                    self.state = VehicleState.TO_DROPOFF
                else:
                    assert self.job is not None
                    self.job.delivered = True
                    self.completed_jobs += 1
                    self.job = None
                    self.state = VehicleState.IDLE

        return Telemetry(
            time_s=time_s,
            vehicle=self.vehicle_id,
            state=self.state.name,
            position_m=round(self.position_m, 3),
            velocity_mps=round(self.motor.velocity_mps, 3),
            target_m=round(self.target_m, 3),
            foup_id=self.job.foup_id if self.job else "",
        )
