IMG_CENTER = 320

#Lookahead points
LOOKAHEAD_POINTS_Y = [200, 320, 380]
LOOKAHEAD_POINTS_WEIGHTS = [0.2, 0.3, 0.5]

#Steering angle (degrees)
SERVO_CENTER = 0
MAX_STEERING_ANGLE = 30.0
MIN_STEERING_ANGLE = -30.0
STEERING_GAIN = 0.12

#Curvature radius (meters)
STRAIGHT_RADIUS = 4000
CURVE_RADIUS = 1500
SHARP_CURVE_RADIUS = 700

#Speed range for the 8-byte packet (int16, -3599 to 3599)
# MAX_SPEED = full speed forward, NORMAL = cruising, LOW = sharp turns
# Negative values = reverse
MAX_SPEED = 40
NORMAL_SPEED = 30
LOW_SPEED = 20

#Deadband
OFFSET_DEADBAND = 5

#Lane change offset 
LANE_CHANGE_OFFSET = 200

#EMA smoothing for steering
STEERING_EMA_ALPHA = 0.3

#Lane departure warning
DEPARTURE_THRESHOLD_PX = 80.0
DEPARTURE_CONSECUTIVE_FRAMES = 5

