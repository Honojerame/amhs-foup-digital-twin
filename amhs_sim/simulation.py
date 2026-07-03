from __future__ import annotations

from collections import deque
from dataclasses import asdict

from .controller import OhtController
from .model import Foup, Station, Telemetry


class FabSimulation:
    """Deterministic dispatch and discrete-time AMHS plant simulation."""

    def __init__(
        self,
        vehicle_count: int = 2,
        dt_s: float = 0.05,
        stations: list[Station] | None = None,
    ) -> None:
        self.dt_s = dt_s
        self.time_s = 0.0
        self.vehicles = [OhtController(f"OHT-{i + 1:02d}") for i in range(vehicle_count)]
        self.queue: deque[Foup] = deque()
        self.telemetry: list[Telemetry] = []
        self.stations = stations or []

    def add_job(self, foup: Foup) -> None:
        self.queue.append(foup)

    def dispatch(self) -> None:
        for vehicle in self.vehicles:
            if not self.queue:
                break
            if vehicle.dispatch(self.queue[0]):
                self.queue.popleft()

    def step(self) -> None:
        self.dispatch()
        self.time_s += self.dt_s
        self.telemetry.extend(v.update(self.time_s, self.dt_s) for v in self.vehicles)

    def run(self, duration_s: float = 60.0) -> dict[str, object]:
        for _ in range(int(duration_s / self.dt_s)):
            self.step()
            if not self.queue and all(v.job is None for v in self.vehicles):
                break
        return {
            "elapsed_s": round(self.time_s, 2),
            "jobs_completed": sum(v.completed_jobs for v in self.vehicles),
            "jobs_queued": len(self.queue),
            "vehicles": [
                {"id": v.vehicle_id, "state": v.state.name, "completed": v.completed_jobs}
                for v in self.vehicles
            ],
        }

    def telemetry_dicts(self) -> list[dict[str, object]]:
        return [asdict(row) for row in self.telemetry]

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-safe plant snapshot for HMIs and telemetry adapters."""
        return {
            "time_s": round(self.time_s, 2),
            "stations": [asdict(station) for station in self.stations],
            "queue": [
                {
                    "foup_id": job.foup_id,
                    "source": job.source.name,
                    "destination": job.destination.name,
                }
                for job in self.queue
            ],
            "completed": sum(vehicle.completed_jobs for vehicle in self.vehicles),
            "vehicles": [
                {
                    "id": vehicle.vehicle_id,
                    "state": vehicle.state.name,
                    "position_m": round(vehicle.position_m, 3),
                    "velocity_mps": round(vehicle.motor.velocity_mps, 3),
                    "target_m": round(vehicle.target_m, 3),
                    "foup_id": vehicle.job.foup_id if vehicle.job else "",
                    "carrying": bool(vehicle.job and vehicle.job.picked),
                    "fault": vehicle.fault_reason,
                    "completed": vehicle.completed_jobs,
                }
                for vehicle in self.vehicles
            ],
        }


def demo_fab() -> FabSimulation:
    stocker = Station("STOCKER-A", 2.0)
    litho = Station("LITHO-01", 18.0)
    etch = Station("ETCH-02", 32.0)
    metrology = Station("METROLOGY-01", 9.0)
    fab = FabSimulation(vehicle_count=2, stations=[stocker, metrology, litho, etch])
    fab.add_job(Foup("FOUP-1001", stocker, litho))
    fab.add_job(Foup("FOUP-1002", etch, metrology))
    fab.add_job(Foup("FOUP-1003", litho, etch))
    return fab
