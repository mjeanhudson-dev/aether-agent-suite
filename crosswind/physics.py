"""
CROSSWIND: GROUND EFFECT — Physical Flight Dynamics Core
Blade Element Theory, True Ground Effect, Crosswind Kinematics & Touchdown Mechanics
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

@dataclass
class AircraftParams:
    name: str
    mass_kg: float
    wingspan_m: float
    wing_area_m2: float
    aspect_ratio: float
    oswald_efficiency: float
    cl_alpha: float             # Lift curve slope per radian (e.g. 5.5)
    cl_max: float               # Stall lift coefficient (e.g. 1.6)
    cd_zero: float              # Parasitic drag coefficient (e.g. 0.025)
    max_gear_fpm: float         # Gear collapse vertical velocity threshold (e.g. -600 ft/min)
    vne_kts: float              # Velocity never exceed (e.g. 210 kts)

# Predefined Aircraft Fleet
THE_IRON_MULE = AircraftParams(
    name="The Iron Mule (Twin Turboprop)",
    mass_kg=10500.0,
    wingspan_m=26.0,
    wing_area_m2=75.0,
    aspect_ratio=9.0,
    oswald_efficiency=0.82,
    cl_alpha=5.7,
    cl_max=1.85,
    cd_zero=0.028,
    max_gear_fpm=-600.0,
    vne_kts=220.0
)

THE_YUKON_BEAVER = AircraftParams(
    name="The Yukon Beaver (Radial STOL)",
    mass_kg=2300.0,
    wingspan_m=14.6,
    wing_area_m2=23.2,
    aspect_ratio=9.2,
    oswald_efficiency=0.78,
    cl_alpha=5.2,
    cl_max=2.10,
    cd_zero=0.034,
    max_gear_fpm=-500.0,
    vne_kts=155.0
)

class FlightDynamicsEngine:
    """
    Flight dynamics computation engine supporting Ground Effect and Blade Element kinematics.
    """
    RHO_SEA_LEVEL = 1.225 # kg/m^3
    GRAVITY = 9.80665     # m/s^2

    def __init__(self, aircraft: AircraftParams = THE_IRON_MULE):
        self.aircraft = aircraft
        self.air_density = self.RHO_SEA_LEVEL

    @staticmethod
    def ground_effect_factor(altitude_m: float, wingspan_m: float) -> float:
        """
        Calculate induced drag reduction factor sigma(h/b).
        sigma(h/b) = 16(h/b)^2 / (1 + 16(h/b)^2)
        At h/b > 1.0, sigma ~ 1.0 (no ground effect).
        At h/b = 0.1, sigma ~ 0.138 (induced drag drops by 86%).
        """
        h_over_b = max(0.01, altitude_m / max(1.0, wingspan_m))
        h_b_sq = h_over_b * h_over_b
        return (16.0 * h_b_sq) / (1.0 + 16.0 * h_b_sq)

    @staticmethod
    def ground_effect_lift_boost(altitude_m: float, wingspan_m: float, cl_alpha: float, aspect_ratio: float) -> float:
        """
        Effective lift curve slope increase in ground effect.
        """
        h_over_b = max(0.01, altitude_m / max(1.0, wingspan_m))
        term = (2.0 * cl_alpha) / (math.pi * math.pi * aspect_ratio) * math.log(1.0 + math.exp(-math.pi * h_over_b))
        denom = max(0.2, 1.0 - term)
        return cl_alpha / denom

    def compute_aerodynamics(self, airspeed_kts: float, alpha_deg: float, altitude_agl_m: float, flaps_ratio: float = 0.0) -> Dict[str, float]:
        """
        Compute total lift, drag, and airframe forces for a given flight state.
        """
        v_mps = airspeed_kts * 0.514444
        dynamic_pressure = 0.5 * self.air_density * v_mps * v_mps
        alpha_rad = math.radians(alpha_deg)

        # Ground effect attenuation
        sigma = self.ground_effect_factor(altitude_agl_m, self.aircraft.wingspan_m)
        effective_cl_alpha = self.ground_effect_lift_boost(altitude_agl_m, self.aircraft.wingspan_m, self.aircraft.cl_alpha, self.aircraft.aspect_ratio)

        # Flap lift and drag deltas
        cl_flap = flaps_ratio * 0.55
        cd_flap = flaps_ratio * 0.045

        # Lift coefficient with stall ceiling
        cl_unclamped = (effective_cl_alpha * alpha_rad) + cl_flap
        is_stalled = False
        stall_warning = False

        effective_cl_max = self.aircraft.cl_max + (flaps_ratio * 0.3)
        alpha_crit_deg = 16.5
        cl_crit = min(effective_cl_max, max(-0.5, (effective_cl_alpha * math.radians(alpha_crit_deg)) + cl_flap))

        if alpha_deg >= 14.5:
            stall_warning = True
        if alpha_deg >= alpha_crit_deg:
            is_stalled = True
            delta_alpha = alpha_deg - alpha_crit_deg
            # C^1 continuous Viterna-Corrigan post-stall cosine decay anchored to cl_crit
            decay_angle = min(math.pi * 0.5, math.radians(delta_alpha * 3.5))
            cl = cl_crit * math.cos(decay_angle)
        else:
            cl = min(effective_cl_max, max(-0.5, cl_unclamped))

        # Induced drag: C_Di = sigma * C_L^2 / (pi * e * AR)
        denom_cdi = math.pi * self.aircraft.oswald_efficiency * self.aircraft.aspect_ratio
        cd_induced = sigma * (cl * cl) / max(0.1, denom_cdi)
        cd_total = self.aircraft.cd_zero + cd_flap + cd_induced

        lift_newtons = dynamic_pressure * self.aircraft.wing_area_m2 * cl
        drag_newtons = dynamic_pressure * self.aircraft.wing_area_m2 * cd_total

        return {
            "lift_n": lift_newtons,
            "drag_n": drag_newtons,
            "cl": cl,
            "cd": cd_total,
            "sigma": sigma,
            "dynamic_pressure_pa": dynamic_pressure,
            "is_stalled": is_stalled,
            "stall_warning": stall_warning
        }

    def compute_blade_element_aerodynamics(
        self,
        airspeed_kts: float,
        alpha_deg: float,
        altitude_agl_m: float,
        bank_angle_deg: float = 0.0,
        flaps_ratio: float = 0.0,
        num_stations: int = 20,
    ) -> Dict[str, Any]:
        """
        Discretize wing into spanwise Blade Element Theory (BET) stations y_k in [-b/2, b/2].
        Local ground effect height:
            h(y_k) = max(0.1, altitude_agl_m + y_k * sin(bank_angle_rad))
        Produces authentic asymmetric cushion roll moments in banked ground effect flares.
        """
        v_mps = airspeed_kts * 0.514444
        dynamic_pressure = 0.5 * self.air_density * v_mps * v_mps
        alpha_rad = math.radians(alpha_deg)
        bank_rad = math.radians(bank_angle_deg)
        sin_bank = math.sin(bank_rad)

        b = self.aircraft.wingspan_m
        dy = b / float(num_stations)
        area_per_station = self.aircraft.wing_area_m2 / float(num_stations)
        cl_flap = flaps_ratio * 0.55
        cd_flap = flaps_ratio * 0.045
        effective_cl_max = self.aircraft.cl_max + (flaps_ratio * 0.3)
        alpha_crit_deg = 16.5

        stations: List[Dict[str, float]] = []
        total_lift_n = 0.0
        total_drag_n = 0.0
        roll_moment_nm = 0.0

        for k in range(num_stations):
            y_k = -0.5 * b + (k + 0.5) * dy
            h_k = max(0.1, altitude_agl_m + (y_k * sin_bank))
            sigma_k = self.ground_effect_factor(h_k, b)
            cl_alpha_k = self.ground_effect_lift_boost(
                h_k, b, self.aircraft.cl_alpha, self.aircraft.aspect_ratio
            )

            cl_unclamped_k = (cl_alpha_k * alpha_rad) + cl_flap
            cl_crit_k = min(
                effective_cl_max,
                max(-0.5, (cl_alpha_k * math.radians(alpha_crit_deg)) + cl_flap),
            )

            if alpha_deg >= alpha_crit_deg:
                decay = min(math.pi * 0.5, math.radians((alpha_deg - alpha_crit_deg) * 3.5))
                cl_k = cl_crit_k * math.cos(decay)
            else:
                cl_k = min(effective_cl_max, max(-0.5, cl_unclamped_k))

            denom_cdi = math.pi * self.aircraft.oswald_efficiency * self.aircraft.aspect_ratio
            cdi_k = sigma_k * (cl_k * cl_k) / max(0.1, denom_cdi)
            cd_k = self.aircraft.cd_zero + cd_flap + cdi_k

            lift_k = dynamic_pressure * area_per_station * cl_k
            drag_k = dynamic_pressure * area_per_station * cd_k
            moment_k = y_k * lift_k

            total_lift_n += lift_k
            total_drag_n += drag_k
            roll_moment_nm += moment_k

            stations.append({
                "station_index": k,
                "y_m": y_k,
                "altitude_m": h_k,
                "sigma": sigma_k,
                "cl": cl_k,
                "cd": cd_k,
                "lift_n": lift_k,
                "drag_n": drag_k,
            })

        return {
            "total_lift_n": total_lift_n,
            "total_drag_n": total_drag_n,
            "roll_moment_nm": roll_moment_nm,
            "num_stations": num_stations,
            "stations": stations,
        }

    @staticmethod
    def compute_crosswind_kinematics(airspeed_kts: float, wind_speed_kts: float, wind_dir_deg: float, runway_heading_deg: float) -> Dict[str, float]:
        """
        Calculate crosswind, headwind components, required crab angle, and decrab rudder authority.
        """
        relative_wind_rad = math.radians(wind_dir_deg - runway_heading_deg)
        headwind_kts = wind_speed_kts * math.cos(relative_wind_rad)
        crosswind_kts = wind_speed_kts * math.sin(relative_wind_rad)

        v_tas = max(10.0, airspeed_kts)
        crab_ratio = max(-0.95, min(0.95, crosswind_kts / v_tas))
        crab_angle_deg = math.degrees(math.asin(crab_ratio))

        # Required rudder deflection to decrab to 0 deg before touchdown
        rudder_deflection_pct = min(100.0, abs(crab_angle_deg) * 3.8)

        return {
            "headwind_kts": headwind_kts,
            "crosswind_kts": crosswind_kts,
            "crab_angle_deg": crab_angle_deg,
            "rudder_deflection_pct": rudder_deflection_pct
        }

    @staticmethod
    def score_touchdown(vertical_speed_mps: float, centerline_dev_m: float, residual_crab_deg: float, max_gear_fpm: float = -600.0) -> Dict[str, Any]:
        """
        Evaluate touchdown telemetry and determine structural outcome.
        vertical_speed_mps: negative is descent (e.g. -1.0 m/s ~ -196 ft/min)
        """
        fpm = vertical_speed_mps * 196.85 # m/s to ft/min

        grade = "UNKNOWN"
        gear_collapsed = False
        tire_blown = False
        base_points = 10000

        # Check gear collapse limit
        if fpm < max_gear_fpm:
            grade = "GEAR_COLLAPSE"
            gear_collapsed = True
            base_points = 0
        elif fpm >= -120.0:
            grade = "GREASE_BUTTER"
            base_points += 2500
        elif fpm >= -350.0:
            grade = "FIRM_OPERATIONAL"
            base_points += 1000
        else: # -351 to max_gear_fpm
            grade = "HARD_LANDING"
            base_points -= 1500

        # Check side-load blowout from landing with uncorrected crab
        if not gear_collapsed and abs(residual_crab_deg) > 7.5:
            tire_blown = True
            base_points -= 3000
            grade += " (TIRE BLOWOUT / SIDELOAD)"

        # Penalty deductions
        fpm_penalty = abs(fpm) * 5.0
        centerline_penalty = abs(centerline_dev_m) * 150.0
        final_score = max(0, int(base_points - fpm_penalty - centerline_penalty))

        return {
            "grade": grade,
            "fpm": fpm,
            "centerline_dev_m": centerline_dev_m,
            "residual_crab_deg": residual_crab_deg,
            "gear_collapsed": gear_collapsed,
            "tire_blown": tire_blown,
            "final_score": final_score
        }

    def compute_dualsense_haptics(self, airspeed_kts: float, alpha_deg: float, is_touchdown: bool, vspeed_fpm: float = 0.0) -> Dict[str, Any]:
        """
        Map flight dynamic states to physical DualSense trigger and haptic modes.
        """
        # 1. Aerodynamic Dynamic Pressure Yoke Resistance (Mode 0x21 Static Force)
        v_ratio = min(1.0, max(0.0, airspeed_kts / self.aircraft.vne_kts))
        trigger_resistance_counts = int(20 + 200 * (v_ratio * v_ratio))

        # 2. Pre-stall Buffet (Mode 0x26 Frequency Vibration)
        stall_vibration_active = alpha_deg >= 14.5
        vibration_freq_hz = 32 if stall_vibration_active else 0
        vibration_amplitude = 220 if stall_vibration_active else 0

        # 3. Touchdown Shockwave
        touchdown_impulse_counts = 0
        if is_touchdown:
            touchdown_impulse_counts = min(255, int(abs(vspeed_fpm) * 0.4))

        return {
            "trigger_mode": "0x21_STATIC_RESISTANCE",
            "trigger_force_counts": trigger_resistance_counts,
            "stall_vibration_freq_hz": vibration_freq_hz,
            "stall_vibration_amplitude": vibration_amplitude,
            "touchdown_impulse_counts": touchdown_impulse_counts
        }
