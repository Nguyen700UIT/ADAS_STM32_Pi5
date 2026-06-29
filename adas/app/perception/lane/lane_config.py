"""
Lane detection configuration for Pi Camera Module 3.
Camera: Pi Camera Module 3 (picamera2)
Resolution: 640x480
Format: RGB888
"""

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480


# Perspective transform (bird's-eye view) source points
# These define a trapezoid in the image that maps to a rectangle in top-down view
# Tuned for Pi Camera Module 3's wide FOV (~102°-120°) at 640x480
WARP_SRC = [
    [int(IMAGE_WIDTH * 0.15), IMAGE_HEIGHT],           # Bottom-left
    [int(IMAGE_WIDTH * 0.45), int(IMAGE_HEIGHT * 0.6)], # Top-left
    [int(IMAGE_WIDTH * 0.55), int(IMAGE_HEIGHT * 0.6)], # Top-right
    [int(IMAGE_WIDTH * 0.85), IMAGE_HEIGHT],            # Bottom-right
]

# Perspective transform destination points (bird's-eye view rectangle)
WARP_DST = [
    [int(IMAGE_WIDTH * 0.2), IMAGE_HEIGHT],
    [int(IMAGE_WIDTH * 0.2), 0],
    [int(IMAGE_WIDTH * 0.8), 0],
    [int(IMAGE_WIDTH * 0.8), IMAGE_HEIGHT],
]


# Warped (bird's-eye) output dimensions
WARP_WIDTH = 640
WARP_HEIGHT = 480

# Sliding window parameters for lane detection in warped bird's-eye view
N_WINDOWS = 9                     # Number of sliding windows vertically
MARGIN = 80                       # Horizontal search margin on each side (pixels in warped space)
MIN_PIXELS = 50                   # Minimum pixels to re-center the window

# Lane polynomial fit parameters
POLYFIT_DEGREE = 2                # Polynomial degree for lane fitting (2 = quadratic)

# Lane width validation (in pixels in warped bird's-eye space)
LANE_WIDTH_MIN = 150              # Minimum expected lane width
LANE_WIDTH_MAX = 500              # Maximum expected lane width

# Smoothing (exponential moving average) for polynomial coefficients
SMOOTHING_ALPHA = 0.3             # Lower = smoother but more lag

# Image preprocessing
GAUSSIAN_BLUR_KERNEL = 5          # Kernel size for blur (odd number)
CANNY_LOW_THRESHOLD = 50          # Canny edge detection low threshold
CANNY_HIGH_THRESHOLD = 150        # Canny edge detection high threshold

# Color space thresholds for white & yellow lane lines
# (tuned for Pi Camera Module 3 RGB888 output)
WHITE_THRESHOLD = 200             # White line intensity threshold (0-255)
YELLOW_LOW_H = 15                 # Yellow hue low (HSV)
YELLOW_HIGH_H = 35                # Yellow hue high (HSV)
YELLOW_MIN_S = 80                 # Yellow min saturation
YELLOW_MIN_V = 100                # Yellow min value

# Debug / visualization
SHOW_LANE_LINES = True            # Draw final filtered lane lines
SHOW_WARP = False                 # Show bird's-eye view
