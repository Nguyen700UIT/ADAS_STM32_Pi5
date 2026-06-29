import cv2 as cv 
import numpy as np 
import lane_config

class LaneDetector:
    
    def __init__(self):
        # --- Load all config parameters ---
        # Image dimensions
        self.img_width = lane_config.IMAGE_WIDTH
        self.img_height = lane_config.IMAGE_HEIGHT

        # ROI (region of interest)
        self.roi_top = lane_config.ROI_TOP
        self.roi_bottom = lane_config.ROI_BOTTOM
        self.roi_left = lane_config.ROI_LEFT
        self.roi_right = lane_config.ROI_RIGHT

        # Perspective transform matrices (precomputed)
        src_pts = np.float32(lane_config.WARP_SRC)
        dst_pts = np.float32(lane_config.WARP_DST)
        self.warp_matrix = cv.getPerspectiveTransform(src_pts, dst_pts)
        self.inv_warp_matrix = cv.getPerspectiveTransform(dst_pts, src_pts)
        self.warp_width = lane_config.WARP_WIDTH
        self.warp_height = lane_config.WARP_HEIGHT

        # Hough Transform parameters
        self.hough_rho = lane_config.HOUGH_RHO
        self.hough_theta = lane_config.HOUGH_THETA
        self.hough_threshold = lane_config.HOUGH_THRESHOLD
        self.hough_min_line_length = lane_config.HOUGH_MIN_LINE_LENGTH
        self.hough_max_line_gap = lane_config.HOUGH_MAX_LINE_GAP

        # Slope filtering
        self.slope_min = lane_config.SLOPE_MIN
        self.slope_max = lane_config.SLOPE_MAX
        self.lane_center_x = lane_config.LANE_CENTER_X

        # Lane width validation
        self.lane_width_min = lane_config.LANE_WIDTH_MIN
        self.lane_width_max = lane_config.LANE_WIDTH_MAX

        # Smoothing (EMA)
        self.smoothing_alpha = lane_config.SMOOTHING_ALPHA
        self.prev_left_fit = None   # (m, b) for left lane: x = m*y + b
        self.prev_right_fit = None  # (m, b) for right lane

        # Preprocessing
        self.blur_kernel = lane_config.GAUSSIAN_BLUR_KERNEL
        self.canny_low = lane_config.CANNY_LOW_THRESHOLD
        self.canny_high = lane_config.CANNY_HIGH_THRESHOLD

        # White / yellow color thresholds
        self.white_threshold = lane_config.WHITE_THRESHOLD
        self.yellow_low_h = lane_config.YELLOW_LOW_H
        self.yellow_high_h = lane_config.YELLOW_HIGH_H
        self.yellow_min_s = lane_config.YELLOW_MIN_S
        self.yellow_min_v = lane_config.YELLOW_MIN_V

        # Debug flags
        self.show_hough_lines = lane_config.SHOW_HOUGH_LINES
        self.show_lane_lines = lane_config.SHOW_LANE_LINES
        self.show_warp = lane_config.SHOW_WARP

        # Precompute the ROI mask for fast application
        self._build_roi_mask()

    def _build_roi_mask(self):
        """Build a binary mask for the region of interest."""
        mask = np.zeros((self.img_height, self.img_width), dtype=np.uint8)
        mask[self.roi_top:self.roi_bottom, self.roi_left:self.roi_right] = 255
        self.roi_mask = mask
        
