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

# Speed during turning manoeuvres (PWM duty cycle)
TURN_SPEED = 20

# Stop command values
STOP_SPEED = 0
STOP_STEERING = 0
