import unittest

from amhs_sim.controller import OhtController
from amhs_sim.model import Foup, Station, VehicleState
from amhs_sim.simulation import FabSimulation, demo_fab


class SimulationTests(unittest.TestCase):
    def test_demo_delivers_all_foups(self) -> None:
        fab = demo_fab()
        summary = fab.run(120)
        self.assertEqual(summary["jobs_completed"], 3)
        self.assertEqual(summary["jobs_queued"], 0)

    def test_busy_vehicle_rejects_second_dispatch(self) -> None:
        station = Station("A", 1)
        vehicle = OhtController("OHT-01")
        self.assertTrue(vehicle.dispatch(Foup("F1", station, station)))
        self.assertFalse(vehicle.dispatch(Foup("F2", station, station)))

    def test_emergency_stop_removes_actuator_torque(self) -> None:
        vehicle = OhtController("OHT-01")
        vehicle.motor.velocity_mps = 1.0
        vehicle.emergency_stop("photoeye blocked")
        self.assertEqual(vehicle.state, VehicleState.FAULT)
        self.assertEqual(vehicle.motor.velocity_mps, 0.0)

    def test_telemetry_is_recorded_for_every_vehicle_tick(self) -> None:
        fab = FabSimulation(vehicle_count=2, dt_s=0.1)
        fab.step()
        self.assertEqual(len(fab.telemetry), 2)


if __name__ == "__main__":
    unittest.main()

