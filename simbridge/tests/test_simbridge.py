"""
Track 3: Automated Verification Suite for SimBridge (`test_simbridge.py`)
Tests C^2 smootherstep, Casiez 1-Euro adaptive filter, sagittal plane recline immunity,
inverse game-deadzone pre-compensation, 200 ms loading-stall smootherstep blend,
15-count menu trigger isolation, and DualSense 0x21/0x26 adaptive trigger synthesis.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bridge import (
    DualSenseImuSample,
    DualSenseTriggerSynthesizer,
    OneEuroFilter,
    SimBridgeMiddleware,
    SimTelemetryFrame,
    TriggerMode,
    TurnAndLeanFusion,
    inverse_deadzone_precompensate,
    project_sagittal_roll_rate,
    smootherstep_c2,
)


class TestSimBridgeMiddleware(unittest.TestCase):
    def test_smootherstep_c2_polynomial_invariants(self) -> None:
        self.assertEqual(smootherstep_c2(-5.0, 0.0, 1.0), 0.0)
        self.assertEqual(smootherstep_c2(0.0, 0.0, 1.0), 0.0)
        self.assertAlmostEqual(smootherstep_c2(0.5, 0.0, 1.0), 0.5, places=7)
        self.assertEqual(smootherstep_c2(1.0, 0.0, 1.0), 1.0)
        self.assertEqual(smootherstep_c2(5.0, 0.0, 1.0), 1.0)

        # Verify strict monotonicity across [0, 1]
        samples = [smootherstep_c2(i / 20.0, 0.0, 1.0) for i in range(21)]
        for a, b in zip(samples, samples[1:]):
            self.assertLessEqual(a, b)

    def test_rule1_inverse_deadzone_precompensation(self) -> None:
        d_game = 0.20
        # Zero / micro-epsilon input must map to 0.0
        self.assertEqual(inverse_deadzone_precompensate(0.0, d_game=d_game), 0.0)
        self.assertEqual(inverse_deadzone_precompensate(5e-5, d_game=d_game), 0.0)

        # Positive input x = 0.25 -> sqrt(0.25) = 0.5 -> 0.20 + 0.80 * 0.5 = 0.60
        pos = inverse_deadzone_precompensate(0.25, d_game=d_game)
        self.assertAlmostEqual(pos, 0.60, places=6)

        # Negative input x = -0.25 -> -0.60 (antisymmetric)
        neg = inverse_deadzone_precompensate(-0.25, d_game=d_game)
        self.assertAlmostEqual(neg, -0.60, places=6)

        # Full lock maps to +/- 1.0
        self.assertAlmostEqual(inverse_deadzone_precompensate(1.0, d_game=d_game), 1.0, places=6)
        self.assertAlmostEqual(inverse_deadzone_precompensate(-1.0, d_game=d_game), -1.0, places=6)

    def test_rule2_loading_screen_stall_200ms_smootherstep_blend(self) -> None:
        bridge = SimBridgeMiddleware(d_game=0.18)

        # Active steering before loading stall
        for i in range(10):
            bridge.process_frame(
                DualSenseImuSample(
                    timestamp_ms=float(i * 4),
                    omega_z_rad_s=-1.5,
                    r2_raw=100,
                )
            )

        # Simulate 2500 ms loading screen gap (> 1200 ms threshold)
        resume_t0 = 2600.0
        frame0 = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=resume_t0, omega_z_rad_s=-1.5, r2_raw=100)
        )
        # Frame 0 MUST softly zero steering to prevent violent steering rack snap
        self.assertEqual(frame0.loading_blend_factor, 0.0)
        self.assertEqual(frame0.normalized_proxy_steer, 0.0)
        self.assertEqual(frame0.thumb_lx, 0)

        # Mid-ramp at +100 ms (50% of 200 ms window) -> S(0.5) = 0.5
        frame_mid = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=resume_t0 + 100.0, omega_z_rad_s=-1.5, r2_raw=100)
        )
        self.assertAlmostEqual(frame_mid.loading_blend_factor, 0.5, places=5)
        self.assertNotEqual(frame_mid.thumb_lx, 0)

        # Completion at +200 ms -> S(1.0) = 1.0
        frame_end = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=resume_t0 + 200.0, omega_z_rad_s=-1.5, r2_raw=100)
        )
        self.assertAlmostEqual(frame_end.loading_blend_factor, 1.0, places=5)

    def test_rule3_menu_trigger_isolation_and_15_count_deadzone(self) -> None:
        bridge = SimBridgeMiddleware()
        self.assertFalse(bridge.race_active)

        # Resting finger float in menus (12 counts <= 15 deadzone)
        menu_frame = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=0.0, l2_raw=12, r2_raw=15)
        )
        self.assertFalse(menu_frame.race_active)
        self.assertEqual(menu_frame.l2_output, 0)
        self.assertEqual(menu_frame.r2_output, 0)
        self.assertEqual(menu_frame.l2_trigger_mode, TriggerMode.OFF_SOFT)
        self.assertEqual(menu_frame.r2_trigger_mode, TriggerMode.OFF_SOFT)
        self.assertEqual(menu_frame.hid_report_64b[22], 0x00)

        # Pressing L2 strongly in menus (e.g. 200) passes L2 > 15 but MUST NOT latch race_active
        menu_l2_frame = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=4.0, l2_raw=200, r2_raw=30)
        )
        self.assertFalse(menu_l2_frame.race_active)
        self.assertEqual(menu_l2_frame.l2_output, 200)
        self.assertEqual(menu_l2_frame.l2_trigger_mode, TriggerMode.OFF_SOFT)

        # Active throttle R2 > 35 latches race_active and engages 0x21 resistance
        race_frame = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=8.0, l2_raw=10, r2_raw=40),
            SimTelemetryFrame(speed_kmh=180.0, brake_slip_ratio=0.05),
        )
        self.assertTrue(race_frame.race_active)
        self.assertEqual(race_frame.l2_output, 10)  # No 15-count menu swallow once racing
        self.assertEqual(race_frame.l2_trigger_mode, TriggerMode.CONTINUOUS_RESISTANCE)
        self.assertEqual(race_frame.r2_trigger_mode, TriggerMode.CONTINUOUS_RESISTANCE)
        self.assertEqual(len(race_frame.hid_report_64b), 64)
        self.assertEqual(race_frame.hid_report_64b[22], int(TriggerMode.CONTINUOUS_RESISTANCE))

        # High brake slip triggers 0x26 oscillating ABS vibration pulse on L2
        abs_frame = bridge.process_frame(
            DualSenseImuSample(timestamp_ms=12.0, l2_raw=220, r2_raw=0),
            SimTelemetryFrame(speed_kmh=210.0, brake_slip_ratio=0.65),
        )
        self.assertEqual(abs_frame.l2_trigger_mode, TriggerMode.OSCILLATING_PULSE)
        self.assertEqual(abs_frame.hid_report_64b[22], int(TriggerMode.OSCILLATING_PULSE))
        self.assertGreaterEqual(abs_frame.hid_report_64b[25], 28)  # Frequency Hz

    def test_rule4_lap_and_recline_immunity_no_corner_decay(self) -> None:
        fusion = TurnAndLeanFusion(max_lock_deg=90.0)

        # Verify sagittal projection math at -45 deg pitch
        omega_roll = project_sagittal_roll_rate(omega_z_rad_s=1.0, omega_y_rad_s=1.0, pitch_deg=-45.0)
        # cos(-45) = sqrt(2)/2, sin(-45) = -sqrt(2)/2 -> omega_z*cos + omega_y*sin = 0
        self.assertAlmostEqual(omega_roll, 0.0, places=6)

        # Verify gravity anchor decoupling when reclined |pitch| > 30 deg (e.g. -45 deg)
        self.assertEqual(fusion.compute_recline_gravity_weight(-45.0), 0.0)
        self.assertEqual(fusion.compute_recline_gravity_weight(0.0), 1.0)

        # Turn into a 35-degree corner while reclined at -45 deg pitch
        fusion.integrated_angle_deg = 35.0
        # Hold steady corner for 250 frames (1 full second at 250 Hz) with zero gyro rate and zero lateral accel_x
        for i in range(250):
            angle, _ = fusion.update(
                DualSenseImuSample(
                    timestamp_ms=float(i * 4),
                    omega_y_rad_s=0.0,
                    omega_z_rad_s=0.0,
                    accel_x_g=0.0,
                    pitch_deg=-45.0,
                ),
                dt_sec=0.004,
            )
        # Because |pitch| = 45 > 30 deg, lateral gravity is 100% decoupled; angle MUST NOT decay!
        self.assertAlmostEqual(angle, 35.0, places=6)

    def test_casiez_one_euro_adaptive_filter_responsiveness(self) -> None:
        filt = OneEuroFilter(min_cutoff=1.0, beta=0.25)
        filt.filter(0.0, 0.004)

        # Slow micro-tremor step (0.002) is heavily smoothed
        slow_out = filt.filter(0.002, 0.004)
        slow_ratio = slow_out / 0.002

        filt.reset()
        filt.filter(0.0, 0.004)
        # Fast counter-steer flick step (0.80 in 4ms -> dx = 200/s) opens cutoff bandwidth
        fast_out = filt.filter(0.80, 0.004)
        fast_ratio = fast_out / 0.80

        self.assertGreater(fast_ratio, slow_ratio * 2.5)


if __name__ == "__main__":
    unittest.main()
