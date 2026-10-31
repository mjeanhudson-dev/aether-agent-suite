"""
Track 3: Universal DirectInput/XInput/HID Telemetry & Haptic Middleware (`bridge.py`)
Implements:
1. C^2 Smootherstep S(t) = 6t^5 - 15t^4 + 10t^3
2. Rate-Driven Casiez 1-Euro Adaptive Filter (OneEuroFilter)
3. 1st-Party Unified Turn & Lean C^2 Smootherstep Fusion with Lap & Recline Immunity
   - Sagittal plane projection: omega_roll = -(omega_z * cos(theta_pitch) + omega_y * sin(theta_pitch))
   - Lateral accelerometer gravity decoupling when |theta_pitch| > 30 deg
4. Inverse Game-Deadzone Pre-Compensation:
   - X_proxy = (d_game + (1 - d_game) * sqrt(|x|)) * sgn(x)
5. Loading Screen Exit Transition:
   - 200 ms C^2 smootherstep ramp when polling gap > 1200 ms (Frame 0 softly zeroes to 0)
6. Menu Trigger Isolation (15-count deadzone on L2/R2; stock soft mode 0x00 in menus;
   latched into race_active only by R2 > 35 or rumble > 0) and DualSense 0x21/0x26 HID synthesizer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import math
from typing import Dict, Optional, Tuple


class TriggerMode(IntEnum):
    OFF_SOFT = 0x00
    CONTINUOUS_RESISTANCE = 0x21
    OSCILLATING_PULSE = 0x26


def smootherstep_c2(x: float, edge0: float = 0.0, edge1: float = 1.0) -> float:
    """
    Ken Perlin C^2 Smootherstep polynomial:
    S(t) = 6t^5 - 15t^4 + 10t^3, for t in [0, 1].
    Guarantees zero 1st and 2nd derivatives at both endpoints.
    """
    if edge1 == edge0:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def project_sagittal_roll_rate(omega_z_rad_s: float, omega_y_rad_s: float, pitch_deg: float) -> float:
    """
    Rule 4 (Lap & Recline Immunity):
    Projects steering wheel rotation across the sagittal plane using filtered pitch angle:
    omega_roll = -(omega_z * cos(theta_pitch) + omega_y * sin(theta_pitch))
    """
    theta_rad = math.radians(pitch_deg)
    return -(omega_z_rad_s * math.cos(theta_rad) + omega_y_rad_s * math.sin(theta_rad))


def inverse_deadzone_precompensate(
    normalized_steer: float,
    d_game: float = 0.18,
    epsilon: float = 1e-4,
) -> float:
    """
    Rule 1 (Zero Stock Game XML Tampering):
    Pre-compensates the game's internal deadzone and quadratic response curve:
    X_proxy = (d_game + (1 - d_game) * sqrt(|x|)) * sgn(x)
    """
    clamped_x = max(-1.0, min(1.0, float(normalized_steer)))
    abs_x = abs(clamped_x)
    if abs_x <= epsilon:
        return 0.0
    d_clamped = max(0.0, min(0.95, float(d_game)))
    sign_x = 1.0 if clamped_x > 0.0 else -1.0
    compensated = (d_clamped + (1.0 - d_clamped) * math.sqrt(abs_x)) * sign_x
    return max(-1.0, min(1.0, compensated))


def normalized_to_xinput_thumb(value: float) -> int:
    """
    Maps normalized [-1.0, 1.0] steering output to 16-bit signed XInput sThumbLX [-32768, 32767].
    """
    clamped = max(-1.0, min(1.0, float(value)))
    if clamped >= 0.0:
        return int(round(clamped * 32767.0))
    return int(round(clamped * 32768.0))


@dataclass(frozen=True)
class DualSenseImuSample:
    timestamp_ms: float
    omega_x_rad_s: float = 0.0
    omega_y_rad_s: float = 0.0
    omega_z_rad_s: float = 0.0
    accel_x_g: float = 0.0
    accel_y_g: float = 0.0
    accel_z_g: float = 1.0
    pitch_deg: float = 0.0
    l2_raw: int = 0  # 0..255
    r2_raw: int = 0  # 0..255


@dataclass(frozen=True)
class SimTelemetryFrame:
    speed_kmh: float = 0.0
    brake_slip_ratio: float = 0.0  # 0.0..1.0 (triggers ABS pulse above threshold)
    lateral_g: float = 0.0
    left_rumble: int = 0
    right_rumble: int = 0


@dataclass(frozen=True)
class XInputProxyFrame:
    thumb_lx: int
    normalized_proxy_steer: float
    fused_angle_deg: float
    l2_output: int
    r2_output: int
    race_active: bool
    loading_blend_factor: float
    l2_trigger_mode: TriggerMode
    r2_trigger_mode: TriggerMode
    hid_report_64b: bytes


class OneEuroFilter:
    """
    Rate-Driven Casiez 1-Euro Adaptive Low-Pass Filter.
    fc = min_cutoff + beta * |dx_filtered|
    Eliminates micro-tremor jitter at rest while preserving zero-lag response on rapid counter-steers.
    """

    def __init__(
        self,
        min_cutoff: float = 1.2,
        beta: float = 0.04,
        d_cutoff: float = 10.0,
    ) -> None:
        if min_cutoff <= 0.0 or d_cutoff <= 0.0:
            raise ValueError("Cutoff frequencies must be strictly positive")
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._x_prev: Optional[float] = None
        self._dx_prev: float = 0.0

    @staticmethod
    def _smoothing_factor(cutoff_hz: float, dt_sec: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff_hz)
        return 1.0 / (1.0 + tau / dt_sec)

    def reset(self) -> None:
        self._x_prev = None
        self._dx_prev = 0.0

    def filter(self, x: float, dt_sec: float) -> float:
        if self._x_prev is None or dt_sec <= 0.0:
            self._x_prev = float(x)
            return self._x_prev

        dx = (float(x) - self._x_prev) / dt_sec
        alpha_d = self._smoothing_factor(self.d_cutoff, dt_sec)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self._dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        alpha = self._smoothing_factor(cutoff, dt_sec)
        x_hat = alpha * float(x) + (1.0 - alpha) * self._x_prev

        self._x_prev = x_hat
        self._dx_prev = dx_hat
        return x_hat


class TurnAndLeanFusion:
    """
    1st-Party Unified Turn & Lean C^2 Smootherstep Fusion with Reclined Posture Immunity.
    - Projects gyro rate across sagittal plane: omega_roll = -(omega_z cos(theta) + omega_y sin(theta))
    - Decouples lateral accelerometer gravity (accel_x) when |theta_pitch| > 30 deg via C^2 smootherstep
      so steady corner holds never decay back to center when reclined in a lap/couch posture.
    """

    def __init__(
        self,
        max_lock_deg: float = 90.0,
        base_anchor_blend: float = 0.04,
        recline_start_deg: float = 15.0,
        recline_full_decouple_deg: float = 30.0,
    ) -> None:
        self.max_lock_deg = float(max_lock_deg)
        self.base_anchor_blend = float(base_anchor_blend)
        self.recline_start_deg = float(recline_start_deg)
        self.recline_full_decouple_deg = float(recline_full_decouple_deg)
        self.integrated_angle_deg: float = 0.0

    def reset(self) -> None:
        self.integrated_angle_deg = 0.0

    def compute_recline_gravity_weight(self, pitch_deg: float) -> float:
        """
        Returns [0.0, 1.0] weight for accelerometer lateral gravity anchor.
        At |pitch| <= 15 deg -> 1.0
        At |pitch| >= 30 deg -> 0.0 (100% decoupled per Rule 4)
        """
        abs_pitch = abs(float(pitch_deg))
        if abs_pitch >= self.recline_full_decouple_deg:
            return 0.0
        if abs_pitch <= self.recline_start_deg:
            return 1.0
        return 1.0 - smootherstep_c2(abs_pitch, self.recline_start_deg, self.recline_full_decouple_deg)

    def update(self, sample: DualSenseImuSample, dt_sec: float) -> Tuple[float, float]:
        """
        Updates unified Turn & Lean steering angle and returns (fused_angle_deg, normalized_steer [-1, 1]).
        """
        if dt_sec <= 0.0:
            norm = max(-1.0, min(1.0, self.integrated_angle_deg / self.max_lock_deg))
            return self.integrated_angle_deg, norm

        omega_roll_rad_s = project_sagittal_roll_rate(
            sample.omega_z_rad_s, sample.omega_y_rad_s, sample.pitch_deg
        )
        omega_roll_deg_s = math.degrees(omega_roll_rad_s)

        # Pure gyro turn integration step
        turn_angle = self.integrated_angle_deg + omega_roll_deg_s * dt_sec

        # Lateral accelerometer lean angle estimate
        clamped_ax = max(-1.0, min(1.0, sample.accel_x_g))
        lean_angle_deg = math.degrees(math.asin(clamped_ax))

        # Rate-dependent C^2 smootherstep: high angular velocity favors pure gyro turn integration
        rate_suppress = 1.0 - smootherstep_c2(abs(omega_roll_deg_s), 10.0, 120.0)
        recline_weight = self.compute_recline_gravity_weight(sample.pitch_deg)
        effective_anchor_alpha = self.base_anchor_blend * recline_weight * rate_suppress

        self.integrated_angle_deg = (
            (1.0 - effective_anchor_alpha) * turn_angle + effective_anchor_alpha * lean_angle_deg
        )
        self.integrated_angle_deg = max(
            -self.max_lock_deg, min(self.max_lock_deg, self.integrated_angle_deg)
        )

        normalized = max(-1.0, min(1.0, self.integrated_angle_deg / self.max_lock_deg))
        return self.integrated_angle_deg, normalized


class DualSenseTriggerSynthesizer:
    """
    Synthesizes 64-byte DualSense USB HID Output Packets (`0x02` report ID)
    with Mode `0x21` (Continuous Dynamic Resistance) and Mode `0x26` (Oscillating ABS/Slip Pulse),
    while enforcing Menu Trigger Isolation (stock soft mode `0x00` when `race_active == False`).
    """

    @staticmethod
    def synthesize_packet(
        race_active: bool,
        telemetry: SimTelemetryFrame,
        abs_slip_threshold: float = 0.25,
    ) -> Tuple[TriggerMode, TriggerMode, bytes]:
        buf = bytearray(64)
        buf[0] = 0x02  # USB HID Output Report ID
        buf[1] = 0xFF  # Valid flag bitmask 1
        buf[2] = 0xF7  # Valid flag bitmask 2

        if not race_active:
            # Rule 3: In frontend menus, L2/R2 resistance MUST remain in stock soft mode (0x00)
            buf[11] = int(TriggerMode.OFF_SOFT)  # R2 mode offset
            buf[22] = int(TriggerMode.OFF_SOFT)  # L2 mode offset
            return TriggerMode.OFF_SOFT, TriggerMode.OFF_SOFT, bytes(buf)

        # Active race mode: compute speed-proportional resistance [40..235]
        speed_norm = max(0.0, min(1.0, telemetry.speed_kmh / 300.0))
        brake_force = int(round(60.0 + 175.0 * speed_norm))
        throttle_force = int(round(35.0 + 95.0 * speed_norm))

        # R2 (Throttle): Continuous dynamic resistance (0x21)
        r2_mode = TriggerMode.CONTINUOUS_RESISTANCE
        buf[11] = int(r2_mode)
        buf[12] = 0x18  # Start resistance zone
        buf[13] = throttle_force

        # L2 (Brake): Oscillating vibration pulse (0x26) on ABS/tire lockup, otherwise continuous resistance (0x21)
        if telemetry.brake_slip_ratio >= abs_slip_threshold:
            l2_mode = TriggerMode.OSCILLATING_PULSE
            abs_freq_hz = int(round(28.0 + 20.0 * min(1.0, telemetry.brake_slip_ratio)))
            buf[22] = int(l2_mode)
            buf[23] = 0x10  # Start zone
            buf[24] = min(255, brake_force)  # Amplitude
            buf[25] = abs_freq_hz  # Frequency in Hz
        else:
            l2_mode = TriggerMode.CONTINUOUS_RESISTANCE
            buf[22] = int(l2_mode)
            buf[23] = 0x14  # Start zone
            buf[24] = brake_force

        return l2_mode, r2_mode, bytes(buf)


class SimBridgeMiddleware:
    """
    Complete SimBridge Runtime Pipeline combining:
    - 1-Euro Adaptive Filtering
    - Unified Turn & Lean C^2 Smootherstep Fusion + Recline Immunity
    - Inverse Game-Deadzone Pre-Compensation
    - 200 ms C^2 Loading-Stall Smootherstep Blend (gap > 1200 ms)
    - Menu Trigger Isolation (15-count deadzone, R2 > 35 or rumble > 0 latch)
    - DualSense 0x21 / 0x26 Adaptive Trigger Synthesizer
    """

    LOADING_STALL_GAP_MS: float = 1200.0
    LOADING_RAMP_DURATION_MS: float = 200.0
    MENU_TRIGGER_DEADZONE_COUNTS: int = 15
    RACE_LATCH_R2_THRESHOLD: int = 35

    def __init__(
        self,
        d_game: float = 0.18,
        max_lock_deg: float = 90.0,
        min_cutoff: float = 1.2,
        beta: float = 0.04,
    ) -> None:
        self.d_game = float(d_game)
        self.one_euro = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.fusion = TurnAndLeanFusion(max_lock_deg=max_lock_deg)
        self.race_active: bool = False
        self._last_timestamp_ms: Optional[float] = None
        self._ramp_start_ms: Optional[float] = None

    def reset_to_menu(self) -> None:
        self.race_active = False
        self.fusion.reset()
        self.one_euro.reset()

    def process_frame(
        self,
        sample: DualSenseImuSample,
        telemetry: Optional[SimTelemetryFrame] = None,
    ) -> XInputProxyFrame:
        telem = telemetry or SimTelemetryFrame()

        # 1. Detect loading screen stall (gap > 1200 ms)
        if self._last_timestamp_ms is None:
            dt_ms = 4.0  # Nominal 250 Hz initial step
        else:
            dt_ms = sample.timestamp_ms - self._last_timestamp_ms

        if dt_ms > self.LOADING_STALL_GAP_MS:
            # Rule 2: Initiate 200 ms C^2 smootherstep transition; Frame 0 must softly zero
            self._ramp_start_ms = sample.timestamp_ms

        self._last_timestamp_ms = sample.timestamp_ms
        dt_sec = max(0.0005, min(0.1, dt_ms / 1000.0))

        # 2. Compute 200 ms loading-stall smootherstep blend factor
        if self._ramp_start_ms is not None:
            elapsed_ramp_ms = max(0.0, sample.timestamp_ms - self._ramp_start_ms)
            loading_blend = smootherstep_c2(elapsed_ramp_ms, 0.0, self.LOADING_RAMP_DURATION_MS)
            if elapsed_ramp_ms >= self.LOADING_RAMP_DURATION_MS:
                self._ramp_start_ms = None
                loading_blend = 1.0
        else:
            loading_blend = 1.0

        # 3. Rule 3: Menu Trigger Isolation & 15-Count Deadzone
        if not self.race_active:
            if sample.r2_raw > self.RACE_LATCH_R2_THRESHOLD or telem.left_rumble > 0 or telem.right_rumble > 0:
                self.race_active = True

        if not self.race_active:
            l2_out = 0 if sample.l2_raw <= self.MENU_TRIGGER_DEADZONE_COUNTS else int(sample.l2_raw)
            r2_out = 0 if sample.r2_raw <= self.MENU_TRIGGER_DEADZONE_COUNTS else int(sample.r2_raw)
        else:
            l2_out = max(0, min(255, int(sample.l2_raw)))
            r2_out = max(0, min(255, int(sample.r2_raw)))

        # 4. Unified Turn & Lean Fusion + 1-Euro Filter + Inverse Game-Deadzone Pre-Compensation
        fused_angle_deg, raw_norm_steer = self.fusion.update(sample, dt_sec)
        filtered_norm_steer = self.one_euro.filter(raw_norm_steer, dt_sec)
        precompensated_steer = inverse_deadzone_precompensate(filtered_norm_steer, d_game=self.d_game)

        # Apply 200 ms C^2 loading-stall smootherstep blend
        blended_proxy_steer = precompensated_steer * loading_blend
        thumb_lx = normalized_to_xinput_thumb(blended_proxy_steer)

        # 5. Synthesize 64-byte DualSense 0x21/0x26 HID output packet
        l2_mode, r2_mode, hid_packet = DualSenseTriggerSynthesizer.synthesize_packet(
            race_active=self.race_active,
            telemetry=telem,
        )

        return XInputProxyFrame(
            thumb_lx=thumb_lx,
            normalized_proxy_steer=blended_proxy_steer,
            fused_angle_deg=fused_angle_deg,
            l2_output=l2_out,
            r2_output=r2_out,
            race_active=self.race_active,
            loading_blend_factor=loading_blend,
            l2_trigger_mode=l2_mode,
            r2_trigger_mode=r2_mode,
            hid_report_64b=hid_packet,
        )
