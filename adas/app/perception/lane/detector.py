import cv2 as cv 
import numpy as np 
import lane_config
from camera import Camera

camera = Camera()

class LaneDetector:
    
    def __init__(self):
        # --- Load all config parameters ---
        # Image dimensions
        self.img_width = lane_config.IMAGE_WIDTH
        self.img_height = lane_config.IMAGE_HEIGHT


        # Perspective transform matrices (precomputed)
        src_pts = np.float32(lane_config.WARP_SRC)
        dst_pts = np.float32(lane_config.WARP_DST)
        self.warp_matrix = cv.getPerspectiveTransform(src_pts, dst_pts)
        self.inv_warp_matrix = cv.getPerspectiveTransform(dst_pts, src_pts)
        self.warp_width = lane_config.WARP_WIDTH
        self.warp_height = lane_config.WARP_HEIGHT

        # Sliding window parameters (in warped bird's-eye space)
        self.n_windows = lane_config.N_WINDOWS
        self.margin = lane_config.MARGIN
        self.min_pixels = lane_config.MIN_PIXELS

        # Lane polynomial fit
        self.polyfit_degree = lane_config.POLYFIT_DEGREE

        # Lane width validation (in warped space)
        self.lane_width_min = lane_config.LANE_WIDTH_MIN
        self.lane_width_max = lane_config.LANE_WIDTH_MAX

        # Smoothing (EMA) for polynomial coefficients
        self.smoothing_alpha = lane_config.SMOOTHING_ALPHA
        self.prev_left_fit = None   # Polynomial coefficients for left lane
        self.prev_right_fit = None  # Polynomial coefficients for right lane

        # Preprocessing
        self.blur_kernel = lane_config.GAUSSIAN_BLUR_KERNEL
        self.canny_low = lane_config.CANNY_LOW_THRESHOLD
        self.canny_high = lane_config.CANNY_HIGH_THRESHOLD

        # White / yellow color thresholds
        self.white_threshold = lane_config.WHITE_THRESHOLD
        self.yellow_low_h = lane_config.YELLOW_LOW_H
        self.yellow_high_h = lane_config.YELLOW_HIGH_H
        self.yellow_min_s = lane_config.YELLOW_MIN_S
        self.yellow_max_s = lane_config.YELLOW_MAX_S
        self.yellow_min_v = lane_config.YELLOW_MIN_V
        self.yellow_max_v = lane_config.YELLOW_MAX_V

        # Debug flags
        self.show_lane_lines = lane_config.SHOW_LANE_LINES
        self.show_warp = lane_config.SHOW_WARP

    def preprocess(self, frame):
        gaussianBlurred = cv.GaussianBlur(frame, (self.blur_kernel, self.blur_kernel), 0)
        return gaussianBlurred
    
    def warp_perspective(self, preprocessed_frame):
        transformedFrame = cv.warpPerspective(preprocessed_frame, self.warp_matrix, (self.warp_width, self.warp_height))
        return transformedFrame
    
    def thresholding(self, warped_frame):
        hsv = cv.cvtColor(warped_frame, cv.COLOR_RGB2HSV)
        
        lower_white = np.array([0, 0, self.white_threshold])
        upper_white = np.array([180, 30, 255])

        lower_yellow = np.array([self.yellow_low_h, self.yellow_min_s, self.yellow_min_v])
        upper_yellow = np.array([self.yellow_high_h, self.yellow_max_s, self.yellow_max_v])

        white_mask = cv.inRange(hsv, lower_white, upper_white)
        yellow_mask = cv.inRange(hsv, lower_yellow, upper_yellow)

        binary = cv.bitwise_or(white_mask, yellow_mask)

        kernel = np.ones((3,3))
        binary = cv.morphologyEx(binary, cv.MORPH_CLOSE, kernel)
        binary = cv.morphologyEx(binary, cv.MORPH_OPEN, kernel)
        return binary
    