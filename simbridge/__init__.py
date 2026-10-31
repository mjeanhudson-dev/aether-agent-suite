"""
Track 3: SimBridge — Universal DirectInput/XInput/HID Telemetry & Haptic Middleware.
Implements 1st-Party Unified Turn & Lean C2 Smootherstep fusion, Rate-Driven Casiez 1-Euro Filter,
inverse game-deadzone pre-compensation, 200 ms C2 loading-stall smootherstep blend,
menu trigger isolation (15-count deadzone), and DualSense 0x21/0x26 adaptive trigger synthesis.
"""

from .bridge import (
    TriggerMode,
    DualSenseImuSample,
    SimTelemetryFrame,
    XInputProxyFrame,
    smootherstep_c2,
    inverse_deadzone_precompensate,
    project_sagittal_roll_rate,
    OneEuroFilter,
    TurnAndLeanFusion,
    DualSenseTriggerSynthesizer,
    SimBridgeMiddleware,
)

__all__ = [
    "TriggerMode",
    "DualSenseImuSample",
    "SimTelemetryFrame",
    "XInputProxyFrame",
    "smootherstep_c2",
    "inverse_deadzone_precompensate",
    "project_sagittal_roll_rate",
    "OneEuroFilter",
    "TurnAndLeanFusion",
    "DualSenseTriggerSynthesizer",
    "SimBridgeMiddleware",
]
