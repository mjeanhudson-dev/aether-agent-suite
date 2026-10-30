"""
CROSSWIND: GROUND EFFECT — Mission Flight Simulation Runner
Mission Bravo-6: Mount Hayes Blizzard Evacuation (10-20 Min Co-op Contract Simulation)
"""

import time
import math
from physics import FlightDynamicsEngine, THE_IRON_MULE

def run_simulation(headless: bool = True):
    engine = FlightDynamicsEngine(THE_IRON_MULE)

    print("======================================================================")
    print("=== CROSSWIND: GROUND EFFECT — Atmospheric Survival Mission Runner ===")
    print("=== Mission Bravo-6: Mount Hayes Blizzard Evacuation               ===")
    print("=== Aircraft: The Iron Mule (Twin-Turboprop Freighter, 10,500 kg)  ===")
    print("======================================================================\n")

    # Initial flight state
    altitude_m = 950.0          # ~3,100 ft AGL
    airspeed_kts = 125.0        # Approach speed
    alpha_deg = 5.2             # Trimmed pitch attitude
    flaps_ratio = 0.50          # Flaps 20 deg
    runway_heading_deg = 350.0  # Runway 35
    lateral_offset_m = 12.0     # 12 meters right of centerline
    vs_mps = -4.5               # Initial sink rate ~ -885 ft/min
    time_elapsed = 0.0
    dt = 1.0                    # 1-second simulation step

    # Weather conditions
    base_wind_speed = 36.0      # 36 kts
    base_wind_dir = 275.0       # Direct crosswind from the west
    in_microburst = False
    engine_failure_active = False

    print("Briefing: Severe mountain wave blizzard approaching. Catastrophic crosswind on Rwy 35.")
    print("Pre-flight check complete. Beginning final approach descent vector...\n")

    touchdown_record = None

    while altitude_m > 0.0 and time_elapsed < 300.0:
        time_elapsed += dt

        # 1. In-flight failure event at 1,500 ft AGL (~480m)
        if altitude_m <= 480.0 and not engine_failure_active:
            engine_failure_active = True
            print(">>> ⚠️ EMERGENCY [02:14]: LEFT ENGINE OIL PRESSURE CRITICAL! Propeller feathered.")
            airspeed_kts -= 4.0
            alpha_deg += 0.8

        # 2. Mountain Microburst at 600 ft AGL (altitude ~ 180m)
        if 80.0 <= altitude_m <= 190.0:
            in_microburst = True
            current_wind_speed = base_wind_speed + 12.0
            current_wind_dir = base_wind_dir + 35.0
            vs_mps = min(-6.2, vs_mps - 1.2) # Downdraft forces rapid sink
        else:
            in_microburst = False
            current_wind_speed = base_wind_speed
            current_wind_dir = base_wind_dir
            # Gradual glidepath stabilization
            if altitude_m > 25.0:
                vs_mps = max(-4.8, min(-3.2, vs_mps + 0.3 * dt))

        # 3. Aerodynamics & Ground Effect
        aero = engine.compute_aerodynamics(airspeed_kts, alpha_deg, altitude_m, flaps_ratio)
        crosswind = engine.compute_crosswind_kinematics(airspeed_kts, current_wind_speed, current_wind_dir, runway_heading_deg)

        # Ground effect cushion below 25m (altitude < wingspan)
        residual_crab = crosswind["crab_angle_deg"]
        if altitude_m <= 25.0:
            alpha_deg = min(11.0, alpha_deg + 0.6) # Pilot flares
            flaps_ratio = 1.0 # Full barn-door flaps
            airspeed_kts = max(78.0, airspeed_kts - (3.5 * dt)) # Floating bleed-off

            # Cushion softens sink rate, strictly clamped between -0.45 m/s and -1.8 m/s (no ballooning climb)
            cushion_cushion_factor = (1.0 - aero["sigma"])
            target_sink = -0.50 - (0.90 * aero["sigma"])
            vs_mps = max(-1.8, min(-0.40, (vs_mps * 0.7) + (target_sink * 0.3)))

            # Pilot kicks right rudder to decrab at 10m
            if altitude_m <= 10.0:
                residual_crab = max(-1.2, min(1.2, crosswind["crab_angle_deg"] * 0.08))
                lateral_offset_m = max(-0.8, min(0.8, lateral_offset_m * 0.3))

        # Check for stall
        if aero["is_stalled"]:
            print(">>> 🚨 CRITICAL STALL WARNING: Airflow detachment across main wing!")
            vs_mps -= 3.0

        # Descent integration
        altitude_m = max(0.0, altitude_m + (vs_mps * dt))

        # ASCII Cockpit Telemetry display every 15 seconds or near touchdown
        if int(time_elapsed) % 15 == 0 or altitude_m <= 25.0:
            cushion_bar = "■" * int((1.0 - aero["sigma"]) * 10)
            cushion_pad = " " * (10 - len(cushion_bar))
            haptics = engine.compute_dualsense_haptics(airspeed_kts, alpha_deg, False)

            status_flag = "NORMAL GLIDEPATH"
            if in_microburst: status_flag = "⚠️ MICROBURST WINDSHEAR"
            elif altitude_m <= 25.0: status_flag = "🟢 IN GROUND EFFECT (FLARE)"
            elif engine_failure_active: status_flag = "⚡ SINGLE-ENGINE DRIFT"

            print(f"[T+{int(time_elapsed):03d}s] Alt: {altitude_m:5.1f}m ({int(altitude_m * 3.28084):4d}ft) | "
                  f"IAS: {airspeed_kts:5.1f}kt | V/S: {vs_mps * 196.85:6.0f}fpm | "
                  f"Crab: {crosswind['crab_angle_deg']:+4.1f}° | Cushion: [{cushion_bar}{cushion_pad}] | "
                  f"Yoke Force: {haptics['trigger_force_counts']:3d}/255 | {status_flag}")

        if altitude_m <= 0.0:
            # Touchdown event!
            touchdown_record = engine.score_touchdown(
                vertical_speed_mps=vs_mps,
                centerline_dev_m=lateral_offset_m,
                residual_crab_deg=residual_crab,
                max_gear_fpm=THE_IRON_MULE.max_gear_fpm
            )
            break

    print("\n======================================================================")
    print("=== FINAL MISSION TELEMETRY SCORECARD (TOUCHDOWN EVALUATION)        ===")
    print("======================================================================")
    print(f"  Touchdown Grade:       {touchdown_record['grade']}")
    print(f"  Vertical Touchdown:    {touchdown_record['fpm']:.1f} ft/min")
    print(f"  Centerline Deviation:  {abs(touchdown_record['centerline_dev_m']):.2f} meters ({abs(touchdown_record['centerline_dev_m']) * 3.28084 * 12:.1f} inches)")
    print(f"  Residual Crab Angle:   {touchdown_record['residual_crab_deg']:+.2f}°")
    print(f"  Airframe Gear Status:  {'💥 COLLAPSED' if touchdown_record['gear_collapsed'] else '✅ INTACT & SECURED'}")
    print(f"  Tire Sideload Status:  {'🔥 BLOWN / GROUND LOOP' if touchdown_record['tire_blown'] else '✅ MAINTAINED TRACTION'}")
    print(f"  FINAL GREASE SCORE:    {touchdown_record['final_score']} / 12,500 POINTS")
    print("======================================================================\n")

    return touchdown_record

if __name__ == "__main__":
    run_simulation(headless=True)
