import cv2 as cv
import numpy as np

try:
    from . import lane_config
except ImportError:
    import lane_config


class LaneDetector:
    def __init__(self):
        self.img_width = lane_config.IMAGE_WIDTH
        self.img_height = lane_config.IMAGE_HEIGHT

        self.base_src_pts = np.float32(lane_config.WARP_SRC)
        self.base_dst_pts = np.float32(lane_config.WARP_DST)
        self.warp_matrix = None
        self.inv_warp_matrix = None
        self._warp_cache_key = None
        self.warp_width = lane_config.WARP_WIDTH
        self.warp_height = lane_config.WARP_HEIGHT

        self.n_windows = lane_config.N_WINDOWS
        self.margin = lane_config.MARGIN
        self.min_pixels = lane_config.MIN_PIXELS
        self.polyfit_degree = lane_config.POLYFIT_DEGREE

        self.lane_width_min = lane_config.LANE_WIDTH_MIN
        self.lane_width_max = lane_config.LANE_WIDTH_MAX

        self.smoothing_alpha = lane_config.SMOOTHING_ALPHA
        self.prev_left_fit = None
        self.prev_right_fit = None

        self.consecutive_invalid_frames = lane_config.CONSECUTIVE_INVALID_FRAMES
        self.max_invalid_frames = lane_config.MAX_INVALID_FRAMES
        
        self.blur_kernel = lane_config.GAUSSIAN_BLUR_KERNEL
        self.white_threshold = lane_config.WHITE_THRESHOLD
        self.yellow_low_h = lane_config.YELLOW_LOW_H
        self.yellow_high_h = lane_config.YELLOW_HIGH_H
        self.yellow_min_s = lane_config.YELLOW_MIN_S
        self.yellow_max_s = lane_config.YELLOW_MAX_S
        self.yellow_min_v = lane_config.YELLOW_MIN_V
        self.yellow_max_v = lane_config.YELLOW_MAX_V

        self.show_lane_lines = lane_config.SHOW_LANE_LINES
        self.show_warp = lane_config.SHOW_WARP

    def preprocess(self, frame):
        return cv.GaussianBlur(frame, (self.blur_kernel, self.blur_kernel), 0)

    def warp_perspective(self, preprocessed_frame):
        h, w = preprocessed_frame.shape[:2]
        warp_matrix, _ = self._get_warp_matrices(w, h)
        return cv.warpPerspective(
            preprocessed_frame,
            warp_matrix,    
            (w, h),
        )

    def _get_warp_matrices(self, width, height):
        cache_key = (width, height)
        if self._warp_cache_key == cache_key:
            return self.warp_matrix, self.inv_warp_matrix

        scale = self._point_scale(width, height)
        src_pts = self.base_src_pts * scale
        dst_pts = self.base_dst_pts * scale
        self.warp_matrix = cv.getPerspectiveTransform(src_pts, dst_pts)
        self.inv_warp_matrix = cv.getPerspectiveTransform(dst_pts, src_pts)
        self.warp_width = width
        self.warp_height = height
        self._warp_cache_key = cache_key
        return self.warp_matrix, self.inv_warp_matrix

    def _point_scale(self, width, height):
        return np.float32(
            [
                (width - 1) / (lane_config.IMAGE_WIDTH - 1),
                (height - 1) / (lane_config.IMAGE_HEIGHT - 1),
            ]
        )

    def thresholding(self, warped_frame):
        gray = cv.cvtColor(warped_frame, cv.COLOR_BGR2GRAY)
        hsv = cv.cvtColor(warped_frame, cv.COLOR_BGR2HSV)

        lower_white = np.array([0, 0, self.white_threshold])
        upper_white = np.array([180, 30, 255])

        lower_yellow = np.array([self.yellow_low_h, self.yellow_min_s, self.yellow_min_v])
        upper_yellow = np.array([self.yellow_high_h, self.yellow_max_s, self.yellow_max_v])

        white_mask = cv.inRange(hsv, lower_white, upper_white)
        yellow_mask = cv.inRange(hsv, lower_yellow, upper_yellow)
        color_mask = cv.bitwise_or(white_mask, yellow_mask)

        adaptive_mask = cv.adaptiveThreshold(
            gray,
            255,
            cv.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv.THRESH_BINARY,
            51,
            -8,
        )
        edge_mask = cv.Canny(gray, 50, 150)
        edge_mask = cv.dilate(edge_mask, np.ones((3,3), dtype=np.uint8), iterations=1)

        binary = cv.bitwise_or(color_mask, adaptive_mask)
        binary = cv.bitwise_or(binary, edge_mask)

        kernel = cv.getStructuringElement(cv.MORPH_RECT, (1, 30))
        binary = cv.dilate(binary, kernel, iterations=2)
        binary = cv.erode(binary, kernel, iterations=2)
        binary = cv.morphologyEx(binary, cv.MORPH_CLOSE, kernel)

        return binary

    def sliding_windows(self, binary, left_base, right_base, return_debug=False):

        window_height = binary.shape[0] // self.n_windows
        curr_left = int(left_base)
        curr_right = int(right_base)

        left_shifts = []
        right_shifts = []

        nonzeroy, nonzerox = binary.nonzero()
        left_lane_inds = []
        right_lane_inds = []
        windows = []

        for window in range(self.n_windows):
            win_y_low = binary.shape[0] - (window + 1) * window_height
            win_y_high = binary.shape[0] - window * window_height
            win_y_mid = (win_y_low + win_y_high) // 2

            if window > 0:
                if self.prev_left_fit is not None:
                    curr_left = int(np.polyval(self.prev_left_fit, win_y_mid))
                elif len(left_shifts) > 0:
    
                    curr_left += int(np.mean(left_shifts))

                if self.prev_right_fit is not None:
                    curr_right = int(np.polyval(self.prev_right_fit, win_y_mid))
                elif len(right_shifts) > 0:
                    curr_right += int(np.mean(right_shifts))

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
                next_left = int(np.mean(nonzerox[good_left]))
                if window > 0:
                    left_shifts.append(next_left - curr_left)
                curr_left = next_left
            else:

                if len(left_shifts) > 0:
                    curr_left += int(np.mean(left_shifts))

            if len(good_right) > self.min_pixels:
                next_right = int(np.mean(nonzerox[good_right]))
                if window > 0:
                    right_shifts.append(next_right - curr_right)
                curr_right = next_right
            else:
                if len(right_shifts) > 0:
                    curr_right += int(np.mean(right_shifts))

        left_lane_inds = np.concatenate(left_lane_inds) if left_lane_inds else np.array([], dtype=np.int64)
        right_lane_inds = np.concatenate(right_lane_inds) if right_lane_inds else np.array([], dtype=np.int64)

        left_fit = self._fit_lane(nonzerox[left_lane_inds], nonzeroy[left_lane_inds])
        right_fit = self._fit_lane(nonzerox[right_lane_inds], nonzeroy[right_lane_inds])

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
    
    def compute_center(self, left_fitx, right_fitx):
        center_fitx = (left_fitx + right_fitx)/2
        return center_fitx

    def _fit_lane(self, x_values, y_values):
        min_points = self.polyfit_degree + 1
        if x_values.size < min_points or y_values.size < min_points:
            return None
        return np.polyfit(y_values, x_values, self.polyfit_degree)

    def smooth_fit(self, current_fit, previous_fit):
        if current_fit is None:
            return previous_fit
        if previous_fit is None:
            return current_fit
        alpha = self.smoothing_alpha
        return (alpha * current_fit) + ((1.0 - alpha) * previous_fit)

    def find_lane(self, binary):
        if self.prev_left_fit is not None and self.prev_right_fit is not None:
            y_eval = binary.shape[0] - 1
            left_base = int(np.polyval(self.prev_left_fit, y_eval))
            right_base = int(np.polyval(self.prev_right_fit, y_eval))
        else:
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

        valid = self._valid_lane_pair(left_fit, right_fit, binary.shape[0])
        if valid:
            self.consecutive_invalid_frames = 0
            
            left_fit = self.smooth_fit(left_fit, self.prev_left_fit)
            right_fit = self.smooth_fit(right_fit, self.prev_right_fit)

            self.prev_left_fit = left_fit
            self.prev_right_fit = right_fit
        else:
            self.consecutive_invalid_frames += 1
            
            if self.prev_left_fit is not None and self.prev_right_fit is not None:
                if self.consecutive_invalid_frames > self.max_invalid_frames:
                    self.prev_left_fit = None
                    self.prev_right_fit = None
                else:
                    left_fit = self.prev_left_fit
                    right_fit = self.prev_right_fit
            else:
                self.prev_left_fit = left_fit
                self.prev_right_fit = right_fit

        debug["valid"] = valid
        debug["left_base"] = left_base
        debug["right_base"] = right_base
        return left_fit, right_fit, debug

    def _valid_lane_pair(self, left_fit, right_fit, height):
        if left_fit is None or right_fit is None:
            return False

        y_bottom = height - 1
        left_x_bottom = float(np.polyval(left_fit, y_bottom))
        right_x_bottom = float(np.polyval(right_fit, y_bottom))
        width_bottom = right_x_bottom - left_x_bottom

        y_top = 0
        left_x_top = float(np.polyval(left_fit, y_top))
        right_x_top = float(np.polyval(right_fit, y_top))
        width_top = right_x_top - left_x_top

        width_scale = self.warp_width / lane_config.WARP_WIDTH
        min_width = self.lane_width_min * width_scale
        max_width = self.lane_width_max * width_scale

      
        if not (min_width <= width_bottom <= max_width) or not (min_width <= width_top <= max_width):
            return False

        if self.prev_left_fit is not None:
            prev_left_x_top = float(np.polyval(self.prev_left_fit, y_top))
            if abs(left_x_top - prev_left_x_top) > 65:
                return False

        return True

    def draw_sliding_windows(self, binary, debug, left_fit=None, right_fit=None):
        if len(binary.shape) == 2:
            out_img = np.dstack((binary, binary, binary))
        else:
            out_img = binary.copy()

        out_img = out_img.astype(np.uint8)
        nonzerox = debug.get("nonzerox", np.array([], dtype=np.int64))
        nonzeroy = debug.get("nonzeroy", np.array([], dtype=np.int64))
        left_inds = debug.get("left_inds", np.array([], dtype=np.int64))
        right_inds = debug.get("right_inds", np.array([], dtype=np.int64))

        out_img[nonzeroy[left_inds], nonzerox[left_inds]] = (255, 0, 0)
        out_img[nonzeroy[right_inds], nonzerox[right_inds]] = (0, 0, 255)

        for window in debug.get("windows", []):
            lx1, ly1, lx2, ly2 = window["left"]
            rx1, ry1, rx2, ry2 = window["right"]
            cv.rectangle(out_img, (lx1, ly1), (lx2, ly2), (0, 255, 0), 2)
            cv.rectangle(out_img, (rx1, ry1), (rx2, ry2), (0, 255, 0), 2)

        self._draw_fit_curve(out_img, left_fit, (255, 255, 0))
        self._draw_fit_curve(out_img, right_fit, (0, 255, 255))
        return out_img

    def _draw_fit_curve(self, image, fit, color):
        if fit is None:
            return

        ploty = np.linspace(0, image.shape[0] - 1, image.shape[0])
        fitx = np.polyval(fit, ploty)
        points = np.array([np.transpose(np.vstack([fitx, ploty]))], dtype=np.int32)
        cv.polylines(image, points, isClosed=False, color=color, thickness=3)

    def draw_lane_overlay(self, frame, left_fit, right_fit):
        if left_fit is None or right_fit is None:
            return frame

        h, w = frame.shape[:2]
        _, inv_warp_matrix = self._get_warp_matrices(w, h)
        ploty = np.linspace(0, h - 1, h)
        leftx = np.polyval(left_fit, ploty)
        rightx = np.polyval(right_fit, ploty)

        lane_warp = np.zeros((h, w, 3), dtype=np.uint8)
        pts_left = np.array([np.transpose(np.vstack([leftx, ploty]))])
        pts_right = np.array([np.flipud(np.transpose(np.vstack([rightx, ploty])))])
        pts = np.hstack((pts_left, pts_right)).astype(np.int32)

        cv.fillPoly(lane_warp, [pts], (0, 180, 0))
        cv.polylines(lane_warp, pts_left.astype(np.int32), False, (255, 255, 0), 8)
        cv.polylines(lane_warp, pts_right.astype(np.int32), False, (0, 255, 255), 8)

        unwarped = cv.warpPerspective(
            lane_warp,
            inv_warp_matrix,
            (w, h),
        )
        return cv.addWeighted(frame, 1.0, unwarped, 0.35, 0)

    def draw_warp_source(self, frame):
        h, w = frame.shape[:2]
        scale = self._point_scale(w, h)
        src_pts = (self.base_src_pts * scale).astype(np.int32)
        out = frame.copy()
        cv.polylines(out, [src_pts], isClosed=True, color=(0, 255, 255), thickness=2)
        for index, point in enumerate(src_pts):
            x, y = point
            cv.circle(out, (x, y), 5, (0, 0, 255), -1)
            cv.putText(out, str(index), (x + 6, y - 6), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        return out

    def process_frame(self, frame, return_debug=False):
        preprocessed = self.preprocess(frame)
        warped = self.warp_perspective(preprocessed)
        binary = self.thresholding(warped)
        left_fit, right_fit, debug = self.find_lane(binary)

        annotated = self.draw_lane_overlay(frame.copy(), left_fit, right_fit)
        sliding_view = self.draw_sliding_windows(binary, debug, left_fit, right_fit)

        data = {
            "left_fit": left_fit,
            "right_fit": right_fit,
            "valid": debug["valid"],
            "warp_source": self.draw_warp_source(frame),
            "warped": warped,
            "binary": binary,
            "sliding_windows": sliding_view,
            "debug": debug,
        }
        return annotated, data

    def update(self, frame):
        return self.process_frame(frame)