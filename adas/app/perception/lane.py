"""
Lane Detection Module for ADAS on Raspberry Pi 5 + PiCamera + OpenCV

Provides functions and a LaneDetector class for detecting lane markings
from a front-facing camera feed. Supports both straight and curved road
detection with temporal smoothing.

Pipeline:
    frame → preprocess → region_of_interest → detect_lines → separate_lines
         → average_lines → fit_polynomial → calculate_offset → draw_lanes

Exports:
    - LaneDetector (class)
    - preprocess (function)
    - separate_lines (function)
    - calculate_offset (function)
"""

import cv2 as cv
import numpy as np
from typing import Optional, Tuple, List


# ============================================================================
# CONSTANTS & DEFAULT CONFIG
# ============================================================================

# Default ROI vertices as a fraction of frame dimensions [height, width]
# Format: (x1, y1), (x2, y2), (x3, y3), (x4, y4)  (top-left → clockwise)
# Default is a trapezoid covering the lower half of the frame
DEFAULT_ROI_FRAC = np.array([
    [0.12, 0.65],   # top-left
    [0.40, 0.85],   # bottom-left
    [0.60, 0.85],   # bottom-right
    [0.88, 0.65],   # top-right
], dtype=np.float32)

# Image processing
DEFAULT_GAUSSIAN_KERNEL = (5, 5)
DEFAULT_CANNY_LOW = 50
DEFAULT_CANNY_HIGH = 150
DEFAULT_HOUGH_RHO = 1               # Distance resolution in pixels
DEFAULT_HOUGH_THETA = np.pi / 180   # Angular resolution in radians
DEFAULT_HOUGH_THRESHOLD = 20        # Min votes for a line
DEFAULT_HOUGH_MIN_LEN = 40          # Min line length in pixels
DEFAULT_HOUGH_MAX_GAP = 20          # Max gap between segments

# Line classification
DEFAULT_SLOPE_THRESHOLD = 0.3       # Reject slopes with |slope| < this (too flat)
DEFAULT_LANE_WIDTH_FRAC = 0.35      # Typical lane width as fraction of frame width
DEFAULT_LANE_WIDTH_TOLERANCE = 0.5  # ± tolerance for lane width sanity check

# Temporal smoothing (exponential moving average)
DEFAULT_SMOOTHING_ALPHA = 0.6       # 0.0 = no smoothing, 1.0 = full smooth


# ============================================================================
# IMAGE PREPROCESSING
# ============================================================================

def preprocess(frame: np.ndarray,
               kernel_size: Tuple[int, int] = DEFAULT_GAUSSIAN_KERNEL,
               canny_low: int = DEFAULT_CANNY_LOW,
               canny_high: int = DEFAULT_CANNY_HIGH) -> np.ndarray:
    """
    Convert a BGR frame to edge-detected binary image.

    Pipeline: BGR → Gray → GaussianBlur → Canny

    Args:
        frame: Input BGR image (H, W, 3).
        kernel_size: Gaussian kernel size (must be odd).
        canny_low: Lower hysteresis threshold for Canny.
        canny_high: Upper hysteresis threshold for Canny.

    Returns:
        Binary edge image (H, W).
    """
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    blurred = cv.GaussianBlur(gray, kernel_size, 0)
    edges = cv.Canny(blurred, canny_low, canny_high)
    return edges


# ============================================================================
# REGION OF INTEREST
# ============================================================================

def region_of_interest(edges: np.ndarray,
                       roi_vertices: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Mask the edges image to keep only the road region (trapezoidal ROI).

    If no vertices are provided, uses DEFAULT_ROI_FRAC scaled to frame size.

    Args:
        edges: Binary edge image (H, W).
        roi_vertices: Array of 4 (x, y) vertices defining the polygon.
                      If None, a default trapezoid is computed.

    Returns:
        Masked edge image (H, W) — zero outside ROI.
    """
    h, w = edges.shape[:2]

    if roi_vertices is None:
        vertices = (DEFAULT_ROI_FRAC * np.array([w, h])).astype(np.int32)
    else:
        vertices = roi_vertices.astype(np.int32)

    mask = np.zeros_like(edges)
    cv.fillPoly(mask, [vertices], 255)
    masked = cv.bitwise_and(edges, mask)
    return masked


# ============================================================================
# LINE DETECTION
# ============================================================================

def detect_lines(edges: np.ndarray,
                 rho: float = DEFAULT_HOUGH_RHO,
                 theta: float = DEFAULT_HOUGH_THETA,
                 threshold: int = DEFAULT_HOUGH_THRESHOLD,
                 min_line_len: int = DEFAULT_HOUGH_MIN_LEN,
                 max_line_gap: int = DEFAULT_HOUGH_MAX_GAP) -> np.ndarray:
    """
    Detect line segments using Probabilistic Hough Transform.

    Args:
        edges: Binary edge image (H, W).
        rho: Distance resolution in pixels.
        theta: Angular resolution in radians.
        threshold: Minimum votes to consider a line.
        min_line_len: Minimum line length in pixels.
        max_line_gap: Maximum gap between segments to merge.

    Returns:
        Array of shape (N, 1, 4) where each row is [x1, y1, x2, y2].
        Returns empty array (N, 1, 4) if no lines found.
    """
    lines = cv.HoughLinesP(
        edges,
        rho=rho,
        theta=theta,
        threshold=threshold,
        minLineLength=min_line_len,
        maxLineGap=max_line_gap,
    )
    if lines is None:
        return np.empty((0, 1, 4), dtype=np.int32)
    return lines


# ============================================================================
# LINE SEPARATION & AVERAGING
# ============================================================================

def separate_lines(lines: np.ndarray,
                   slope_threshold: float = DEFAULT_SLOPE_THRESHOLD,
                   img_width: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Classify detected line segments into left and right lane markings.

    Criteria:
        - Left lane  → negative slope (\) in image coordinates
        - Right lane → positive slope (/)
        - Reject lines with |slope| < slope_threshold (too horizontal/noise)
        - Optionally reject lines based on x-intercept position

    Args:
        lines: Array of shape (N, 1, 4) [x1, y1, x2, y2].
        slope_threshold: Minimum absolute slope to consider a line valid.
        img_width: Frame width (used for x-intercept filtering).
                   If None, filtering is skipped.

    Returns:
        Tuple of (left_lines, right_lines), each (M, 4) [x1, y1, x2, y2].
        Either may be empty (0, 4) if no matching lines found.
    """
    left_lines = []
    right_lines = []

    for line in lines:
        x1, y1, x2, y2 = line[0]

        # Avoid division by zero for vertical lines
        if x2 == x1:
            continue

        slope = (y2 - y1) / (x2 - x1)
        length = np.hypot(x2 - x1, y2 - y1)

        # Reject horizontal/noisy lines
        if abs(slope) < slope_threshold:
            continue

        # x-intercept at the bottom of the frame (y = max(y1,y2))
        # y = mx + b  →  x = (y - b) / m
        b = y1 - slope * x1
        x_bottom = (max(y1, y2) - b) / slope

        # Left lane: negative slope, intercept in left half of image
        if slope < 0:
            if img_width is None or (0 <= x_bottom <= img_width * 0.55):
                left_lines.append([x1, y1, x2, y2])
        # Right lane: positive slope, intercept in right half of image
        else:
            if img_width is None or (img_width * 0.45 <= x_bottom <= img_width):
                right_lines.append([x1, y1, x2, y2])

    left_arr = np.array(left_lines, dtype=np.int32).reshape(-1, 4) if left_lines else np.empty((0, 4), dtype=np.int32)
    right_arr = np.array(right_lines, dtype=np.int32).reshape(-1, 4) if right_lines else np.empty((0, 4), dtype=np.int32)

    return left_arr, right_arr


def average_lines(segments: np.ndarray,
                  prev_line: Optional[np.ndarray] = None,
                  alpha: float = DEFAULT_SMOOTHING_ALPHA,
                  img_height: Optional[int] = None) -> Optional[np.ndarray]:
    """
    Average multiple line segments into a single representative line and
    apply exponential moving average (EMA) temporal smoothing.

    Args:
        segments: Array of shape (M, 4) [x1, y1, x2, y2] for one lane side.
        prev_line: Previously averaged line [x1, y1, x2, y2] (for smoothing).
        alpha: Smoothing factor (0.0 = no smoothing, 1.0 = very smooth).
        img_height: Image height in pixels. If provided, the extrapolated
                    line will span the full height of the ROI.

    Returns:
        Smoothed line [x1, y1, x2, y2] or None if no segments provided.
    """
    if segments.shape[0] == 0:
        return prev_line  # Keep previous if no new detections

    # Compute the average line from all segments
    avg_line = np.mean(segments, axis=0, dtype=np.float32).astype(np.int32)

    # Extrapolate to full ROI height if requested
    if img_height is not None and img_height > 0:
        avg_line = extrapolate_line(*avg_line, img_height)

    # Temporal smoothing via EMA
    if prev_line is not None and alpha > 0:
        smoothed = (alpha * avg_line + (1.0 - alpha) * prev_line).astype(np.int32)
        return smoothed

    return avg_line


def extrapolate_line(x1: int, y1: int, x2: int, y2: int,
                     h: int) -> np.ndarray:
    """
    Extend a line segment to span from the bottom (y = h-1) to the
    top (y = h * 0.6 or similar) of the ROI for display purposes.

    Uses the formula: y = mx + b  →  solve for x at given y.

    Args:
        x1, y1, x2, y2: Line segment endpoints.
        h: Image height (used to define top/bottom y-coordinates).

    Returns:
        Array [x1_bot, h-1, x1_top, y_top] where the line spans the ROI.
    """
    # Avoid division by zero
    if x2 == x1:
        return np.array([x1, h - 1, x1, int(h * 0.6)], dtype=np.int32)

    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1

    y_bottom = h - 1
    y_top = int(h * 0.6)

    # Solve for x at desired y-values
    x_bottom = int((y_bottom - intercept) / slope)
    x_top = int((y_top - intercept) / slope)

    return np.array([x_bottom, y_bottom, x_top, y_top], dtype=np.int32)


# ============================================================================
# POLYNOMIAL FITTING (for curved lanes)
# ============================================================================

def fit_polynomial(left_pts: np.ndarray,
                   right_pts: np.ndarray,
                   order: int = 2) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Fit a polynomial (y = ax² + bx + c) to the left and right lane points.

    This is used for curved roads where a linear approximation is insufficient.

    Args:
        left_pts: Array of (x, y) points for the left lane, shape (N, 2).
        right_pts: Array of (x, y) points for the right lane, shape (M, 2).
        order: Polynomial order (default 2 for quadratic).

    Returns:
        Tuple of (left_coeffs, right_coeffs), each array of length `order+1`.
        Returns (None, None) if fitting fails.
    """
    left_coeffs = right_coeffs = None

    if left_pts.shape[0] >= order + 1:
        left_coeffs = np.polyfit(left_pts[:, 1], left_pts[:, 0], order)

    if right_pts.shape[0] >= order + 1:
        right_coeffs = np.polyfit(right_pts[:, 1], right_pts[:, 0], order)

    return left_coeffs, right_coeffs


def evaluate_polynomial(coeffs: np.ndarray, y_vals: np.ndarray) -> np.ndarray:
    """
    Evaluate a polynomial at given y-values.

    Args:
        coeffs: Polynomial coefficients (e.g., [a, b, c] for quadratic).
        y_vals: y-values to evaluate at.

    Returns:
        x-values corresponding to the given y-values.
    """
    return np.polyval(coeffs, y_vals)


# ============================================================================
# LATERAL OFFSET CALCULATION
# ============================================================================

def calculate_offset(frame_width: int,
                     left_line: Optional[np.ndarray],
                     right_line: Optional[np.ndarray],
                     pixels_per_meter: float = 0.0) -> Tuple[float, float, float]:
    """
    Calculate the lateral offset of the vehicle from the lane center.

    The offset is computed at the bottom of the frame (where the car is).

    Args:
        frame_width: Width of the frame in pixels.
        left_line: Left lane line array [x1, y1, x2, y2] or None.
        right_line: Right lane line array [x1, y1, x2, y2] or None.
        pixels_per_meter: Conversion factor (0 = use pixels only).

    Returns:
        Tuple of (offset_pixels, offset_meters, lane_width_pixels).
        - offset_pixels: +ve = right of center, -ve = left of center
        - offset_meters: same in meters (0 if pixels_per_meter == 0)
        - lane_width_pixels: detected lane width at bottom
    """
    if left_line is None and right_line is None:
        return 0.0, 0.0, 0.0

    frame_center_x = frame_width / 2.0

    # Get x-position at the bottom of the frame (y = max y-coordinate)
    if left_line is not None:
        _, ly1, _, ly2 = left_line
        left_x_at_scan = _x_at_y(left_line, max(ly1, ly2))
    else:
        left_x_at_scan = 0.0

    if right_line is not None:
        _, ry1, _, ry2 = right_line
        right_x_at_scan = _x_at_y(right_line, max(ry1, ry2))
    else:
        right_x_at_scan = float(frame_width)

    lane_center_x = (left_x_at_scan + right_x_at_scan) / 2.0
    lane_width_px = right_x_at_scan - left_x_at_scan

    offset_px = lane_center_x - frame_center_x
    offset_m = offset_px / pixels_per_meter if pixels_per_meter > 0 else 0.0

    return offset_px, offset_m, lane_width_px


def _x_at_y(line: np.ndarray, y_target: float) -> float:
    """Helper: compute x-coordinate at a given y on the line [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = line
    if y2 == y1:
        return float(x1)
    slope = (x2 - x1) / (y2 - y1)  # dx/dy
    return float(x1 + slope * (y_target - y1))


# ============================================================================
# CURVATURE CALCULATION
# ============================================================================

def calculate_curvature(coeffs: np.ndarray,
                        y_eval: float,
                        pixels_per_meter: float = 1.0) -> float:
    """
    Calculate the radius of curvature of a lane at a given y-value.

    Formula (for y = ax² + bx + c):
        R = (1 + (2*a*y_eval + b)²)^1.5  /  |2*a|

    Args:
        coeffs: Polynomial coefficients [a, b, c] (fit with x = f(y)).
        y_eval: y-value (in meters) at which to evaluate curvature.
        pixels_per_meter: Conversion factor (px) / (m).

    Returns:
        Radius of curvature in meters.
        Positive = left curve, Negative = right curve.
    """
    if coeffs is None or len(coeffs) < 2:
        return float('inf')

    # Fit was done in pixel space, convert y_eval to pixels
    y_eval_px = y_eval * pixels_per_meter

    a, b = coeffs[0], coeffs[1]

    # Radius of curvature formula
    denominator = abs(2.0 * a)
    if denominator < 1e-6:
        return float('inf')  # Straight road

    curvature = (1 + (2 * a * y_eval_px + b) ** 2) ** 1.5 / denominator

    # Negative curvature = curve to the right (in image coords)
    if a > 0:
        curvature = -curvature

    return curvature


# ============================================================================
# VISUALIZATION
# ============================================================================

def draw_lanes(frame: np.ndarray,
               left_line: Optional[np.ndarray],
               right_line: Optional[np.ndarray],
               color: Tuple[int, int, int] = (0, 255, 0),
               thickness: int = 8) -> np.ndarray:
    """
    Draw detected lane lines and fill the lane area on the frame.

    Args:
        frame: Input BGR image (will be modified in-place).
        left_line: Left lane line [x1, y1, x2, y2] or None.
        right_line: Right lane line [x1, y1, x2, y2] or None.
        color: BGR color for lane lines (default green).
        thickness: Line thickness in pixels.

    Returns:
        Annotated frame with lane overlay.
    """
    overlay = frame.copy()

    if left_line is not None:
        x1, y1, x2, y2 = left_line
        cv.line(overlay, (x1, y1), (x2, y2), color, thickness)

    if right_line is not None:
        x1, y1, x2, y2 = right_line
        cv.line(overlay, (x1, y1), (x2, y2), color, thickness)

    # Fill lane area polygon
    if left_line is not None and right_line is not None:
        pts = np.array([
            [left_line[0], left_line[1]],
            [left_line[2], left_line[3]],
            [right_line[2], right_line[3]],
            [right_line[0], right_line[1]],
        ], dtype=np.int32)
        cv.fillPoly(overlay, [pts], (0, 255, 0))

        # Blend overlay with original frame
        alpha = 0.3
        frame = cv.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        return frame

    return overlay


def display_info(frame: np.ndarray,
                 offset_px: float = 0.0,
                 offset_m: float = 0.0,
                 curvature: float = 0.0,
                 lane_width: float = 0.0,
                 departed: bool = False,
                 show_lane: bool = True,
                 show_curvature: bool = True,
                 show_offset: bool = True) -> np.ndarray:
    """
    Display ADAS HUD information (offset, curvature, warnings) on the frame.

    Args:
        frame: BGR image (will be modified in-place).
        offset_px: Lateral offset in pixels.
        offset_m: Lateral offset in meters.
        curvature: Radius of curvature in meters.
        lane_width: Lane width in pixels.
        departed: Whether a lane departure is detected.
        show_lane: Show lane width indicator.
        show_curvature: Show curvature value.
        show_offset: Show offset value.

    Returns:
        Annotated frame.
    """
    # Lane departure warning
    if departed:
        cv.putText(frame, "LANE DEPARTURE!", (50, 100),
                   cv.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    # Offset info
    if show_offset:
        label = f"Offset: {offset_px:+.1f}px ({offset_m:+.2f}m)"
        color = (0, 255, 0) if abs(offset_px) < 30 else (0, 255, 255) if abs(offset_px) < 60 else (0, 0, 255)
        cv.putText(frame, label, (50, 60), cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Lane width
    if show_lane and lane_width > 0:
        cv.putText(frame, f"Lane Width: {lane_width:.0f}px", (50, 90),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    # Curvature
    if show_curvature and curvature != float('inf'):
        label = f"Curvature: {abs(curvature):.0f}m"
        label += " (R)" if curvature < 0 else " (L)"
        cv.putText(frame, label, (50, 120), cv.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

    return frame


# ============================================================================
# VALIDATION
# ============================================================================

def validate_detection(left_line: Optional[np.ndarray],
                       right_line: Optional[np.ndarray],
                       frame_width: int,
                       prev_left: Optional[np.ndarray] = None,
                       prev_right: Optional[np.ndarray] = None,
                       lane_width_tolerance: float = DEFAULT_LANE_WIDTH_TOLERANCE) -> bool:
    """
    Validate detected lane pair for consistency.

    Checks:
        - Lane width is within expected range
        - Lines do not cross
        - Temporal consistency (optional)

    Args:
        left_line: Left lane line or None.
        right_line: Right lane line or None.
        frame_width: Frame width in pixels.
        prev_left: Previous left line (optional, for temporal check).
        prev_right: Previous right line (optional, for temporal check).
        lane_width_tolerance: Fraction of expected width for tolerance.

    Returns:
        True if valid, False otherwise.
    """
    if left_line is None or right_line is None:
        return False

    expected_width = frame_width * DEFAULT_LANE_WIDTH_FRAC
    _, _, _, lane_width = calculate_offset(frame_width, left_line, right_line)

    # Check lane width is reasonable
    min_w = expected_width * (1 - lane_width_tolerance)
    max_w = expected_width * (1 + lane_width_tolerance)
    if not (min_w <= lane_width <= max_w):
        return False

    # Check lines don't cross (left x < right x at bottom)
    left_x_bot = _x_at_y(left_line, max(left_line[1], left_line[3]))
    right_x_bot = _x_at_y(right_line, max(right_line[1], right_line[3]))
    if left_x_bot >= right_x_bot:
        return False

    return True


# ============================================================================
# LANE DETECTOR CLASS
# ============================================================================

class LaneDetector:
    """
    Main lane detection class that encapsulates the full pipeline.

    Manages temporal state (smoothing buffers, previous lines) and provides
    a single `update()` entry point for processing each camera frame.

    Usage:
        detector = LaneDetector()
        while True:
            frame = camera.get_frame()
            annotated, data = detector.update(frame)
            # data = {'left_line', 'right_line', 'offset_px',
            #         'offset_m', 'curvature', 'departed', 'lane_width'}
    """

    def __init__(self,
                 roi_vertices: Optional[np.ndarray] = None,
                 smoothing_alpha: float = DEFAULT_SMOOTHING_ALPHA,
                 pixels_per_meter: float = 0.0,
                 departure_threshold_px: float = 60.0,
                 curvature_y_eval_m: float = 30.0):
        """
        Initialize the LaneDetector.

        Args:
            roi_vertices: ROI polygon vertices (4 x 2). Default = None (auto-compute).
            smoothing_alpha: Temporal smoothing strength (0.0 - 1.0).
            pixels_per_meter: Camera calibration factor (0 = pixel mode only).
            departure_threshold_px: Offset threshold (px) to trigger departure warning.
            curvature_y_eval_m: y-value (meters) at which to evaluate curvature.
        """
        self.roi_vertices = roi_vertices
        self.smoothing_alpha = smoothing_alpha
        self.pixels_per_meter = pixels_per_meter
        self.departure_threshold_px = departure_threshold_px
        self.curvature_y_eval_m = curvature_y_eval_m

        # Temporal state
        self._prev_left_line: Optional[np.ndarray] = None
        self._prev_right_line: Optional[np.ndarray] = None
        self._prev_left_poly: Optional[np.ndarray] = None
        self._prev_right_poly: Optional[np.ndarray] = None

    def reset(self) -> None:
        """Reset all temporal state (e.g., after a sharp turn or lane change)."""
        self._prev_left_line = None
        self._prev_right_line = None
        self._prev_left_poly = None
        self._prev_right_poly = None

    def update(self, frame: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        Run the full lane detection pipeline on a single frame.

        Args:
            frame: Input BGR image (H, W, 3).

        Returns:
            Tuple of (annotated_frame, data_dict) where data_dict contains:
                - 'left_line':  (4,) array or None
                - 'right_line': (4,) array or None
                - 'offset_px': float
                - 'offset_m': float
                - 'lane_width': float
                - 'curvature': float
                - 'departed': bool
                - 'valid': bool
        """
        h, w = frame.shape[:2]

        # --- Pipeline ---
        edges = preprocess(frame)
        masked = region_of_interest(edges, self.roi_vertices)
        line_segments = detect_lines(masked)

        left_segs, right_segs = separate_lines(line_segments, img_width=w)

        # Average with temporal smoothing
        left_line = average_lines(left_segs, self._prev_left_line, self.smoothing_alpha, h)
        right_line = average_lines(right_segs, self._prev_right_line, self.smoothing_alpha, h)

        # Validate
        valid = validate_detection(left_line, right_line, w)

        if not valid:
            # Fall back to polynomial fitting if available, else revert to previous
            if self._prev_left_line is not None and self._prev_right_line is not None:
                left_line = self._prev_left_line
                right_line = self._prev_right_line
                valid = True

        # Update temporal state
        self._prev_left_line = left_line
        self._prev_right_line = right_line

        # Calculate offset
        offset_px, offset_m, lane_width = calculate_offset(
            w, left_line, right_line, self.pixels_per_meter
        )

        # Calculate curvature (if polynomial coeffs available)
        curvature = float('inf')
        if valid and left_line is not None:
            # Simple curvature from left line endpoints
            pts = np.array([
                [left_line[0], left_line[1]],
                [left_line[2], left_line[3]],
            ])
            if pts.shape[0] >= 3:
                coeffs, _ = fit_polynomial(pts, np.empty((0, 2)))
                if coeffs is not None:
                    curvature = calculate_curvature(coeffs, self.curvature_y_eval_m, max(self.pixels_per_meter, 1.0))

        # Lane departure check
        departed = abs(offset_px) > self.departure_threshold_px if valid else False

        # Draw on frame
        annotated = draw_lanes(frame.copy(), left_line, right_line)
        annotated = display_info(
            annotated,
            offset_px=offset_px,
            offset_m=offset_m,
            curvature=curvature,
            lane_width=lane_width,
            departed=departed,
        )

        data = {
            'left_line': left_line,
            'right_line': right_line,
            'offset_px': offset_px,
            'offset_m': offset_m,
            'lane_width': lane_width,
            'curvature': curvature,
            'departed': departed,
            'valid': valid,
        }

        return annotated, data

    def get_steering_angle(self) -> float:
        """
        Compute a steering angle recommendation based on lane offset.

        Simple PD-style control:
            angle = -Kp * offset_px

        Returns:
            Steering angle in degrees (-25 to +25).
            Negative = steer left, Positive = steer right.
        """
        if self._prev_left_line is None or self._prev_right_line is None:
            return 0.0

        # Use the stored offset from the last update
        # (In practice, call this after update() to get fresh data)
        h, w = 480, 640  # Default; override with actual frame dimensions
        offset_px, _, _ = calculate_offset(w, self._prev_left_line, self._prev_right_line)

        # Simple proportional control
        Kp = 0.4  # Gain factor
        angle = -Kp * offset_px

        # Clamp to reasonable steering range
        angle = np.clip(angle, -25.0, 25.0)
        return angle

    def is_departing(self,
                     offset_px: Optional[float] = None,
                     threshold: Optional[float] = None) -> bool:
        """
        Check if the vehicle is departing from the lane.

        Args:
            offset_px: Current lateral offset in pixels.
                       If None, uses the internally computed offset.
            threshold: Offset threshold in pixels. If None, uses init value.

        Returns:
            True if departure detected, False otherwise.
        """
        if offset_px is None:
            if self._prev_left_line is None or self._prev_right_line is None:
                return False
            offset_px, _, _ = calculate_offset(640, self._prev_left_line, self._prev_right_line)

        thresh = threshold if threshold is not None else self.departure_threshold_px
        return abs(offset_px) > thresh


# ============================================================================
# CONVENIENCE FUNCTION (standalone pipeline)
# ============================================================================

def process_frame(frame: np.ndarray) -> Tuple[np.ndarray, dict]:
    """
    Standalone convenience function to process a single frame.

    This is a stateless, one-shot pipeline. For continuous video processing
    with temporal smoothing, use LaneDetector instead.

    Args:
        frame: Input BGR image (H, W, 3).

    Returns:
        Tuple of (annotated_frame, data_dict).
    """
    h, w = frame.shape[:2]

    edges = preprocess(frame)
    masked = region_of_interest(edges)
    line_segments = detect_lines(masked)

    left_segs, right_segs = separate_lines(line_segments, img_width=w)

    left_line = average_lines(left_segs, img_height=h) if left_segs.shape[0] > 0 else None
    right_line = average_lines(right_segs, img_height=h) if right_segs.shape[0] > 0 else None

    offset_px, offset_m, lane_width = calculate_offset(w, left_line, right_line)
    departed = abs(offset_px) > 60.0

    annotated = draw_lanes(frame.copy(), left_line, right_line)
    annotated = display_info(annotated, offset_px=offset_px, offset_m=offset_m, departed=departed)

    data = {
        'left_line': left_line,
        'right_line': right_line,
        'offset_px': offset_px,
        'offset_m': offset_m,
        'lane_width': lane_width,
        'departed': departed,
        'valid': left_line is not None and right_line is not None,
    }

    return annotated, data