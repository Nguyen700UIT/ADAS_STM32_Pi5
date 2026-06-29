"""
Lane detection configuration for Pi Camera Module 3.
Camera: Pi Camera Module 3 (picamera2)
Resolution: 640x480
Format: RGB888
"""

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480


ROI_TOP = int(IMAGE_HEIGHT * 0.6)       # Start at 60% down (y=288)
ROI_BOTTOM = IMAGE_HEIGHT               # Full bottom (y=480)
ROI_LEFT = 0                            # Full width
ROI_RIGHT = IMAGE_WIDTH

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
WARP_WIDTH = 320
WARP_HEIGHT = 480

# Hough Transform parameters for lane line detection
HOUGH_RHO = 2                     # Distance resolution 
HOUGH_THETA = 1                   # Angular resolution 
HOUGH_THRESHOLD = 50              # Min intersections to detect a line
HOUGH_MIN_LINE_LENGTH = 40        # Min line segment length (pixels)
HOUGH_MAX_LINE_GAP = 100          # Max gap between segments to merge (pixels)

# Lane line slope filtering (in image space, before warp)
# Reject lines with slopes outside typical lane line range
# Left lane: positive slope (bottom-left to top-right), right lane: negative slope
SLOPE_MIN = 0.3                   # Min absolute slope to filter near-horizontal noise
SLOPE_MAX = 2.0                   # Max absolute slope to filter near-vertical noise

# Separate left vs right lanes by x-position at the bottom of ROI
LANE_CENTER_X = IMAGE_WIDTH // 2  # Center divider between left/right lanes

# Lane width validation (in pixels at bottom of image)
LANE_WIDTH_MIN = 150              # Minimum pixel distance between left & right lanes at bottom
LANE_WIDTH_MAX = 500              # Maximum pixel distance between left & right lanes at bottom

# Smoothing (exponential moving average) for lane line averages
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
SHOW_HOUGH_LINES = False          # Draw raw Hough lines on output
SHOW_LANE_LINES = True            # Draw final filtered lane lines
SHOW_WARP = False                 # Show bird's-eye view
