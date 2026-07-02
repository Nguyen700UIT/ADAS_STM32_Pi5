"""
Lane detection configuration
Resolution: 640x480
Format: BGR (OpenCV default)
Tuned for highway lane detection from vehicle dashcam video.
"""

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
IMAGE_MAX_X = IMAGE_WIDTH - 1
IMAGE_MAX_Y = IMAGE_HEIGHT - 1


# Perspective transform (bird's-eye view) source points
# These define a trapezoid in the image that maps to a rectangle in top-down view
# The bottom points are wider to capture the full road width near the vehicle.
# The top points converge to capture the vanishing point area.
WARP_SRC = [
    [int(IMAGE_WIDTH * 0.20), IMAGE_MAX_Y],              # Bottom-left  (wider, captures more road)
    [int(IMAGE_WIDTH * 0.43), int(IMAGE_HEIGHT * 0.65)], # Top-left
    [int(IMAGE_WIDTH * 0.57), int(IMAGE_HEIGHT * 0.65)], # Top-right
    [int(IMAGE_WIDTH * 0.80), IMAGE_MAX_Y],              # Bottom-right (wider)
]

# Perspective transform destination points (bird's-eye view rectangle)
WARP_DST = [
    [int(IMAGE_WIDTH * 0.25), IMAGE_MAX_Y],
    [int(IMAGE_WIDTH * 0.25), 0],
    [int(IMAGE_WIDTH * 0.75), 0],
    [int(IMAGE_WIDTH * 0.75), IMAGE_MAX_Y],
]


# Warped (bird's-eye) output dimensions
WARP_WIDTH = 640
WARP_HEIGHT = 480

# Sliding window parameters for lane detection in warped bird's-eye view
N_WINDOWS = 9                     # Number of sliding windows vertically
MARGIN = 100                      # Horizontal search margin on each side (pixels in warped space)
MIN_PIXELS = 30                   # Minimum pixels to re-center the window

# Lane polynomial fit parameters
POLYFIT_DEGREE = 2                # Polynomial degree for lane fitting (2 = quadratic)

# Lane width validation (in pixels in warped bird's-eye space)
LANE_WIDTH_MIN = 100              # Minimum expected lane width
LANE_WIDTH_MAX = 600              # Maximum expected lane width

# Smoothing (exponential moving average) for polynomial coefficients
SMOOTHING_ALPHA = 0.3             # Lower = smoother but more lag

# Image preprocessing
GAUSSIAN_BLUR_KERNEL = 5          # Kernel size for blur (odd number)


# Color space thresholds for white & yellow lane lines
# (tuned for dashcam video converted to HSV via BGR2HSV)
WHITE_THRESHOLD = 150             # White line intensity (high value + low saturation = white)
YELLOW_LOW_H = 10                 # Yellow hue low (HSV)
YELLOW_HIGH_H = 35                # Yellow hue high (HSV)
YELLOW_MIN_S = 50                 # Yellow min saturation
YELLOW_MAX_S = 255
YELLOW_MIN_V = 50                 # Yellow min value
YELLOW_MAX_V = 255

# Additional detection parameters (not loaded by config but used internally)
# White saturation upper bound is now set in detector.py's thresholding method
# Debug / visualization
SHOW_LANE_LINES = True            # Draw final filtered lane lines
SHOW_WARP = False                 # Show bird's-eye view
