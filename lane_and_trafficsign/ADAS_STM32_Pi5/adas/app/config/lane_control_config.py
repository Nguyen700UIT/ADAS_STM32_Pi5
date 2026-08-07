IMG_CENTER = 320

# Pure Pursuit Parameters
# Assuming lane is 26cm real-world width, and ~473 pixels in warped view.
# Scale: ~18.2 pixels/cm. For a car with 15cm wheelbase, it's ~270 pixels.
WHEELBASE_PX = 270
LOOKAHEAD_DISTANCE_PX = 250
LOOKAHEAD_POINTS_Y = [200, 320, 380] # Kept for backward compatibility
LOOKAHEAD_POINTS_WEIGHTS = [0.2, 0.3, 0.5] # Kept for backward compatibility if needed

#Steering angle (degrees)
SERVO_CENTER = 0
MAX_STEERING_ANGLE = 30.0
MIN_STEERING_ANGLE = -30.0
STEERING_GAIN = 0.12

#Curvature radius (meters)
STRAIGHT_RADIUS = 4000
CURVE_RADIUS = 1500
SHARP_CURVE_RADIUS = 700

# Target speed in motor RPM. STM32 closes the loop from encoder RPM and
# converts the PID output to PWM internally.
# Negative values request reverse motion.
MAX_SPEED = 40
NORMAL_SPEED = 30
LOW_SPEED = 20

#Deadband
OFFSET_DEADBAND = 5

# Maximum pixel offset (warped space) that corresponds to ±100 steering error.
# Offsets beyond this are clamped. Tuned for 640x480 bird's-eye view.
# Increase if car oversteers, decrease if it understeers.
MAX_OFFSET_PX = 200

#Lane change offset 
LANE_CHANGE_OFFSET = 200

#EMA smoothing for steering
STEERING_EMA_ALPHA = 0.3

#Lane departure warning
DEPARTURE_THRESHOLD_PX = 80.0
DEPARTURE_CONSECUTIVE_FRAMES = 5

