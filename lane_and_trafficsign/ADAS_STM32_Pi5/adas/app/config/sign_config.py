# =============================================================================
# Traffic Sign Configuration
# =============================================================================

# YOLO class names (must match model output)
CLASS_STOP = "stop"
CLASS_TURN_LEFT = "turn_left"
CLASS_TURN_RIGHT = "turn_right"

# Steering values sent to STM32 via UART (int8 range: -100 to 100)
TURN_LEFT_STEERING = -80       # strong left offset
TURN_RIGHT_STEERING = 80       # strong right offset

# Target motor speed during turning manoeuvres (RPM)
TURN_SPEED = 20

# Stop command values
STOP_SPEED = 0
STOP_STEERING = 0

# EMA ramp rates (0.0 = no change, 1.0 = instant jump)
# Lower values = smoother but slower response
STEERING_RAMP_ALPHA = 0.15
SPEED_RAMP_ALPHA = 0.2

# STOP must remain asserted long enough to survive a one-frame detector flicker.
STOP_MIN_HOLD_SECONDS = 2.0
STOP_CLEAR_CONSECUTIVE_FRAMES = 5
