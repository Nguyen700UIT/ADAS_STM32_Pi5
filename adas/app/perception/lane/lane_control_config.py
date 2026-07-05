"""
Lane Control Configuration
Tuned for lane keeping on a Raspberry Pi 5 + STM32 vehicle.
All units are in pixels (from detector.py's bird's-eye warped space)
unless otherwise specified.
"""

# ============================================================================
# IMAGE & VEHICLE GEOMETRY
# ============================================================================

# Image center (where the camera/vehicle is pointing)
# For 640x480: center_x = 320, center_y = 240
IMAGE_CENTER_X = 320.0
IMAGE_CENTER_Y = 240.0

# Camera calibration: pixels per meter at the bottom of the image
# Measure this experimentally: place a 1m object at the bottom of the frame
# and count pixels. Default = 0 means pixel-only mode (no meter conversion).
PIXELS_PER_METER = 0.0

# ============================================================================
# PID CONTROLLER GAINS
# ============================================================================

# --- Proportional Gain (Kp) ---
# How aggressively the controller responds to the current error.
#   Too high  → oscillation, wobbling
#   Too low   → slow response, drifts to edge
# Starting range: 0.005 to 0.02
KP = 0.015

# --- Integral Gain (Ki) ---
# Eliminates steady-state error (e.g., constant offset from center).
#   Too high  → overshoot, instability
#   Too low   → persistent offset remains
# Should be 10-100x smaller than Kp.
# Starting range: 0.0001 to 0.001
KI = 0.0003

# --- Derivative Gain (Kd) ---
# Dampens oscillations by reacting to the rate of change of error.
#   Too high  → jittery, amplifies noise
#   Too low   → overshoot, slow settling
# Starting range: 0.01 to 0.05
KD = 0.02

# ============================================================================
# STEERING LIMITS
# ============================================================================

# Maximum steering angle in degrees (hardware limit)
# Typical servo range: ±25° to ±45°
STEERING_MAX_ANGLE = 25.0

# Minimum steering angle (dead zone) — small angles are ignored
# Prevents constant micro-corrections that cause servo jitter
STEERING_DEAD_ZONE_DEG = 1.0

# ============================================================================
# ERROR COMPUTATION
# ============================================================================

# Where to measure the lane offset along the y-axis (in warped space)
#   -1 = bottom of the image (vehicle position, most responsive)
#   -3 = slightly ahead (smoother but more lag)
#   -5 = further ahead (good for high speed)
ERROR_SCAN_Y_INDEX = -1  # -1 = last element = bottom of warped image

# Error threshold (pixels) below which the vehicle is considered "centered"
# Prevents unnecessary corrections when already centered
ERROR_DEAD_ZONE_PX = 5.0

# Maximum error in pixels (for normalization / clamping)
# If error exceeds this, treat as max error (emergency)
ERROR_MAX_PX = 200.0

# ============================================================================
# SERVO PWM MAPPING (for STM32)
# ============================================================================

# Servo pulse width range (microseconds)
# Standard servo: 1000µs = full left, 1500µs = center, 2000µs = full right
SERVO_PWM_MIN = 1000
SERVO_PWM_CENTER = 1500
SERVO_PWM_MAX = 2000

# Servo angle range (degrees) corresponding to min/max PWM
# e.g., -25° = 1000µs, 0° = 1500µs, +25° = 2000µs
SERVO_ANGLE_MIN = -25.0
SERVO_ANGLE_MAX = 25.0

# ============================================================================
# CONTROL LOOP TIMING
# ============================================================================

# Expected frame rate (Hz) — used as default dt for PID
# Your camera runs at ~30 FPS, so dt ≈ 0.033s
EXPECTED_FPS = 30
EXPECTED_DT = 1.0 / EXPECTED_FPS  # ≈ 0.033 seconds

# Maximum allowed dt (seconds) — if dt exceeds this, reset PID
# Prevents integral windup after a frame drop
DT_MAX = 0.1

# ============================================================================
# LANE DEPARTURE WARNING
# ============================================================================

# Offset threshold (pixels) to trigger lane departure warning
DEPARTURE_THRESHOLD_PX = 80.0

# Number of consecutive frames with departure before triggering
DEPARTURE_CONSECUTIVE_FRAMES = 5

# ============================================================================
# SPEED-ADAPTIVE CONTROL (optional, for future use)
# ============================================================================

# Speed-based gain scaling: gains are multiplied by this factor
# at the corresponding speed (km/h). Useful for highway vs. parking lot.
# Format: (speed_kmh, Kp_scale, Ki_scale, Kd_scale)
SPEED_GAIN_TABLE = [
    (0,   1.5, 1.0, 0.5),   # Low speed: more Kp, less Kd
    (20,  1.0, 1.0, 1.0),   # Medium speed: nominal
    (40,  0.7, 0.5, 1.5),   # High speed: less Kp, more Kd
    (60,  0.5, 0.3, 2.0),   # Very high speed: minimal Kp, max Kd
]

# ============================================================================
# DEBUG & LOGGING
# ============================================================================

# Print PID debug info to console
DEBUG_PID = False

# Log file for PID data (empty string = no logging)
LOG_FILE = ""

# Fields to log (comma-separated): error, P, I, D, output, timestamp
LOG_FIELDS = ["error", "P", "I", "D", "output", "timestamp"]