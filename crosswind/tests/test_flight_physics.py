"""
CROSSWIND: GROUND EFFECT — Automated Flight Dynamics Verification Suite
Exhaustive unit testing for Blade Element Theory, Ground Effect, Crosswinds, and Scoring.
"""

import unittest
import math
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from physics import FlightDynamicsEngine, THE_IRON_MULE, THE_YUKON_BEAVER

class TestFlightDynamics(unittest.TestCase):
    def setUp(self):
        self.engine = FlightDynamicsEngine(THE_IRON_MULE)

    def test_ground_effect_induced_drag_reduction(self):
        """
        Verify sigma(h/b) induced drag reduction inside ground effect.
        """
        wingspan = THE_IRON_MULE.wingspan_m # 26m
        # Out of ground effect at 100m (h/b ~ 3.8)
        sigma_high = FlightDynamicsEngine.ground_effect_factor(100.0, wingspan)
        self.assertAlmostEqual(sigma_high, 1.0, delta=0.02)

        # In ground effect at 2.6m (h/b = 0.1)
        sigma_flare = FlightDynamicsEngine.ground_effect_factor(2.6, wingspan)
        # Expected: 16(0.01) / (1 + 16(0.01)) = 0.16 / 1.16 ~ 0.1379
        self.assertLess(sigma_flare, 0.20)
        self.assertGreater(sigma_flare, 0.10)

        # Confirm induced drag is drastically lower in flare
        aero_high = self.engine.compute_aerodynamics(airspeed_kts=110.0, alpha_deg=6.0, altitude_agl_m=100.0)
        aero_flare = self.engine.compute_aerodynamics(airspeed_kts=110.0, alpha_deg=6.0, altitude_agl_m=2.6)

        self.assertLess(aero_flare["cd"], aero_high["cd"])
        self.assertGreater(aero_flare["lift_n"], aero_high["lift_n"])

    def test_stall_warning_and_critical_stall(self):
        """
        Verify pre-stall buffet warning and deep stall lift loss.
        """
        # Normal approach attitude
        aero_normal = self.engine.compute_aerodynamics(airspeed_kts=115.0, alpha_deg=8.0, altitude_agl_m=50.0)
        self.assertFalse(aero_normal["stall_warning"])
        self.assertFalse(aero_normal["is_stalled"])

        # Pre-stall warning attitude (alpha = 15.0 deg)
        aero_warning = self.engine.compute_aerodynamics(airspeed_kts=95.0, alpha_deg=15.0, altitude_agl_m=50.0)
        self.assertTrue(aero_warning["stall_warning"])
        self.assertFalse(aero_warning["is_stalled"])

        # Deep stall (alpha = 18.0 deg)
        aero_stalled = self.engine.compute_aerodynamics(airspeed_kts=80.0, alpha_deg=18.0, altitude_agl_m=50.0)
        self.assertTrue(aero_stalled["is_stalled"])

    def test_crosswind_kinematics_and_crab_angle(self):
        """
        Verify crab angle computation and crosswind decomposition.
        """
        # Runway 350 deg, Wind from 260 deg (90 deg crosswind from left) at 30 kts
        kin = FlightDynamicsEngine.compute_crosswind_kinematics(
            airspeed_kts=120.0,
            wind_speed_kts=30.0,
            wind_dir_deg=260.0,
            runway_heading_deg=350.0
        )

        # 90 deg relative wind means crosswind component should be ~ 30 kts
        self.assertAlmostEqual(abs(kin["crosswind_kts"]), 30.0, delta=1.5)
        # Crab angle should be arcsin(30 / 120) = arcsin(0.25) ~ 14.47 deg
        self.assertAlmostEqual(abs(kin["crab_angle_deg"]), 14.5, delta=1.0)
        # Rudder deflection required should be significant
        self.assertGreater(kin["rudder_deflection_pct"], 40.0)

    def test_touchdown_scoring_and_gear_collapse(self):
        """
        Verify Grease touchdown bonus vs. Gear Collapse failure thresholds.
        """
        # 1. Grease / Butter touchdown (-75 ft/min ~ -0.38 m/s)
        grease = FlightDynamicsEngine.score_touchdown(
            vertical_speed_mps=-0.38,
            centerline_dev_m=0.2,
            residual_crab_deg=0.5
        )
        self.assertEqual(grease["grade"], "GREASE_BUTTER")
        self.assertFalse(grease["gear_collapsed"])
        self.assertGreater(grease["final_score"], 11500)

        # 2. Firm operational touchdown (-250 ft/min ~ -1.27 m/s)
        firm = FlightDynamicsEngine.score_touchdown(
            vertical_speed_mps=-1.27,
            centerline_dev_m=0.8,
            residual_crab_deg=1.2
        )
        self.assertEqual(firm["grade"], "FIRM_OPERATIONAL")
        self.assertFalse(firm["gear_collapsed"])

        # 3. Catastrophic gear collapse (-750 ft/min ~ -3.81 m/s)
        collapse = FlightDynamicsEngine.score_touchdown(
            vertical_speed_mps=-3.81,
            centerline_dev_m=1.0,
            residual_crab_deg=0.0
        )
        self.assertEqual(collapse["grade"], "GEAR_COLLAPSE")
        self.assertTrue(collapse["gear_collapsed"])
        self.assertEqual(collapse["final_score"], 0)

        # 4. Sideload tire blowout from touching down with uncorrected crab
        blowout = FlightDynamicsEngine.score_touchdown(
            vertical_speed_mps=-0.8,
            centerline_dev_m=0.5,
            residual_crab_deg=11.2 # Exceeds 7.5 deg threshold
        )
        self.assertTrue(blowout["tire_blown"])
        self.assertIn("TIRE BLOWOUT", blowout["grade"])

    def test_dualsense_haptics_mapping(self):
        """
        Verify dynamic pressure trigger stiffening and stall buffet frequencies.
        """
        # Low speed (50 kts) -> light trigger
        haptics_low = self.engine.compute_dualsense_haptics(airspeed_kts=50.0, alpha_deg=6.0, is_touchdown=False)
        # High speed (200 kts) -> heavy trigger
        haptics_high = self.engine.compute_dualsense_haptics(airspeed_kts=200.0, alpha_deg=6.0, is_touchdown=False)

        self.assertLess(haptics_low["trigger_force_counts"], haptics_high["trigger_force_counts"])
        self.assertEqual(haptics_low["stall_vibration_freq_hz"], 0)

        # Stall condition engages 32 Hz buffet
        haptics_stall = self.engine.compute_dualsense_haptics(airspeed_kts=90.0, alpha_deg=15.5, is_touchdown=False)
        self.assertEqual(haptics_stall["stall_vibration_freq_hz"], 32)
        self.assertEqual(haptics_stall["stall_vibration_amplitude"], 220)

    def test_viterna_corrigan_lift_continuity_at_critical_alpha(self):
        """
        Verify C^1 Viterna-Corrigan continuity across the alpha = 16.5 deg stall boundary.
        """
        aero_pre = self.engine.compute_aerodynamics(airspeed_kts=100.0, alpha_deg=16.499, altitude_agl_m=50.0)
        aero_post = self.engine.compute_aerodynamics(airspeed_kts=100.0, alpha_deg=16.501, altitude_agl_m=50.0)

        # Delta in Cl across 0.002 deg must be negligible (< 0.005) - no jump discontinuity
        self.assertAlmostEqual(aero_pre["cl"], aero_post["cl"], delta=0.005)
        self.assertTrue(aero_post["is_stalled"])
        self.assertFalse(aero_pre["is_stalled"])

    def test_spanwise_blade_element_theory_ground_cushion_roll_moment(self):
        """
        Verify 20 spanwise BET stations and asymmetric cushion roll moments in banked flares.
        """
        # 1. Level flight inside ground effect: perfectly symmetric, roll moment is 0
        bet_level = self.engine.compute_blade_element_aerodynamics(
            airspeed_kts=105.0, alpha_deg=7.0, altitude_agl_m=3.0, bank_angle_deg=0.0, num_stations=20
        )
        self.assertEqual(bet_level["num_stations"], 20)
        self.assertEqual(len(bet_level["stations"]), 20)
        self.assertAlmostEqual(bet_level["roll_moment_nm"], 0.0, delta=1e-3)

        # 2. Banked flare inside ground effect: lower wing gets higher lift cushion, producing roll moment
        bet_banked_ground = self.engine.compute_blade_element_aerodynamics(
            airspeed_kts=105.0, alpha_deg=7.0, altitude_agl_m=3.0, bank_angle_deg=5.0, num_stations=20
        )
        self.assertNotEqual(bet_banked_ground["roll_moment_nm"], 0.0)
        self.assertGreater(abs(bet_banked_ground["roll_moment_nm"]), 500.0)

        # 3. Banked flare outside ground effect (200m AGL): sigma ~ 1 across all stations, moment is 0
        bet_banked_high = self.engine.compute_blade_element_aerodynamics(
            airspeed_kts=105.0, alpha_deg=7.0, altitude_agl_m=200.0, bank_angle_deg=5.0, num_stations=20
        )
        self.assertAlmostEqual(bet_banked_high["roll_moment_nm"], 0.0, delta=1.0)

if __name__ == "__main__":
    unittest.main()
