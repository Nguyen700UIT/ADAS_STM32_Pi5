import cv2 as cv
import numpy as np

try:
    from . import lane_config
except ImportError:
    import lane_config


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


 
    def sliding_windows(self, binary, left_base, right_base, return_debug=False):
        window_height = binary.shape[0] // self.n_windows
        curr_left = int(left_base)
        curr_right = int(right_base)

        nonzeroy, nonzerox = binary.nonzero()
        left_lane_inds = []
        right_lane_inds = []
        windows = []

        for window in range(self.n_windows):
            win_y_low = binary.shape[0] - (window + 1) * window_height
            win_y_high = binary.shape[0] - window * window_height
            win_xleft_low = curr_left - self.margin
            win_xleft_high = curr_left + self.margin
            win_xright_low = curr_right - self.margin
            win_xright_high = curr_right + self.margin

            windows.append(
                {
                    "left": (win_xleft_low, win_y_low, win_xleft_high, win_y_high),
                    "right": (win_xright_low, win_y_low, win_xright_high, win_y_high),
                }
            )

            good_left = (
                (nonzeroy >= win_y_low)
                & (nonzeroy < win_y_high)
                & (nonzerox >= win_xleft_low)
                & (nonzerox < win_xleft_high)
            ).nonzero()[0]                                           
            good_right = (
                (nonzeroy >= win_y_low)
                & (nonzeroy < win_y_high)
                & (nonzerox >= win_xright_low)
                & (nonzerox < win_xright_high)
            ).nonzero()[0]

            left_lane_inds.append(good_left)
            right_lane_inds.append(good_right)

            if len(good_left) > self.min_pixels:
                curr_left = int(np.mean(nonzerox[good_left]))
            if len(good_right) > self.min_pixels:
                curr_right = int(np.mean(nonzerox[good_right]))

        left_lane_inds = np.concatenate(left_lane_inds) if left_lane_inds else np.array([], dtype=np.int64)
        right_lane_inds = np.concatenate(right_lane_inds) if right_lane_inds else np.array([], dtype=np.int64)

        left_fit = np.polyfit(nonzeroy[left_lane_inds], nonzerox[left_lane_inds], self.polyfit_degree)
        right_fit = np.polyfit(nonzeroy[right_lane_inds], nonzerox[right_lane_inds], self.polyfit_degree)
        
        if not return_debug:
            return left_fit, right_fit

        debug = {
            "windows": windows,
            "nonzerox": nonzerox,
            "nonzeroy": nonzeroy,
            "left_inds": left_lane_inds,
            "right_inds": right_lane_inds,
        }
        return left_fit, right_fit, debug

    def generate_lane_points(self, left_fit, right_fit):
        ploty = np.linspace(0, self.warp_height - 1, self.warp_height)
        left_fitx = np.polyval(left_fit, ploty)
        right_fitx = np.polyval(right_fit, ploty)
        return ploty, left_fitx, right_fitx

    def validate_lane(self, left_fitx, right_fitx):
        width = right_fitx - left_fitx
        if np.any(width < self.lane_width_min):
            return False
        if np.any(width > self.lane_width_max):
            return False
        
        return True
    
    def smooth_lane(self, left_fit, right_fit):

        if self.prev_left_fit is None:
            self.prev_left_fit = left_fit
            self.prev_right_fit = right_fit
            return left_fit, right_fit
        #EMA smoothing
        left_fit = (
            self.smoothing_alpha * left_fit +
            (1-self.smoothing_alpha) * self.prev_left_fit
        )

        right_fit = (
            self.smoothing_alpha * right_fit +
            (1-self.smoothing_alpha) * self.prev_right_fit
        )

        self.prev_left_fit = left_fit
        self.prev_right_fit = right_fit

        return left_fit, right_fit

    def compute_center(self, left_fitx, right_fitx):
        center_fitx = (left_fitx + right_fitx)/2
        return center_fitx

    def draw_lane_mask(self, ploty, left_fitx, right_fitx):
        mask = np.zeros((self.warp_height, self.warp_width, 3), dtype=np.unint8)
        pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
        pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
        pts = np.hstack((pts_left, pts_right)).astype(np.int32)

        cv.fillPoly(mask, [pts], (0,255,0))
        return mask
    
    def inverse_warp(self, mask):
        inversed_mask = cv.warpPerspective(mask, self.inv_warp_matrix, (self.img_width, self.img_height))
        return inversed_mask

    def overlay_lane(self, frame, inversed_mask):
        return cv.addWeighted(frame, 1.00, inversed_mask, 0.4, 0)


    def find_lane(self, binary):
        hist = np.sum(binary[binary.shape[0] // 2 :, :], axis=0)
        mid = int(hist.shape[0] / 2)
        left_base = int(np.argmax(hist[:mid]))
        right_base = int(np.argmax(hist[mid:]) + mid)

        left_fit, right_fit, debug = self.sliding_windows(
            binary,
            left_base,
            right_base,
            return_debug=True,
        )
        ploty, left_fitx, right_fitx = self.generate_lane_points(left_fit, right_fit)
        valid = self.validate_lane(left_fitx, right_fitx)

        if not valid:

            if self.prev_left_fit is None:
                return None

            left_fit = self.prev_left_fit
            right_fit = self.prev_right_fit
            ploty, left_fitx, right_fitx = self.generate_lane_points(left_fit, right_fit)

       
        left_fit,right_fit = self.smooth_lane(left_fit, right_fit)
        ploty, left_fitx, right_fitx = self.generate_lane_points(left_fit, right_fit)

        return {
        "left_fit": left_fit,
        "right_fit": right_fit,
        "ploty": ploty,
        "left_fitx": left_fitx,
        "right_fitx": right_fitx,
        "debug": debug,
        }   
    
    def process_frame(self, frame):
        frame = self.preprocess(frame)
        warped = self.warp_perspective(frame)
        binary = self.thresholding(warped)

        result = self.find_lane(binary)
        if result is None:
            return frame

        lane_mask = self.draw_lane_mask(
            result["ploty"],
            result["left_fitx"],
            result["right_fitx"]
        )

        lane_mask = self.inverse_warp(lane_mask)
        output = self.overlay_lane(frame, lane_mask)

        return output
    
    