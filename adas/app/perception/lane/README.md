# Lane Detection Module — `detector.py` API Reference

## Overview

`LaneDetector` is a computer vision pipeline that detects lane markings in a vehicle dashcam video frame. It uses perspective warping (bird's-eye view), color-based thresholding (white/yellow), sliding window search, polynomial fitting, temporal smoothing, and lane validation to produce a green overlay on the drivable lane region.

## Quick Start

```python
import cv2 as cv
from detector import LaneDetector

# Initialize detector
detector = LaneDetector()

# Read a frame (BGR format)
frame = cv.imread("road.jpg")

# Process a single frame → output with green lane overlay
output = detector.process_frame(frame)

# Show result
cv.imshow("Lane Output", output)
cv.waitKey(0)
```

---

## Class: `LaneDetector`

### Constructor: `LaneDetector()`

Loads all parameters from `lane_config.py`:
- Image dimensions (width/height)
- Perspective transform matrices (warp / inverse warp)
- Sliding window parameters (n_windows, margin, min_pixels)
- Polynomial fit degree
- Lane width validation thresholds
- EMA smoothing alpha
- Gaussian blur kernel size
- White / yellow HSV thresholds

---

## Public Methods

### `process_frame(frame, return_debug=False)`

**Purpose:** Run the full lane detection pipeline on a single frame.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `frame` | `numpy.ndarray` (H×W×3) | required | BGR image from OpenCV. Will be auto-resized to config dimensions (640×480) if needed. |
| `return_debug` | `bool` | `False` | If `True`, returns `(output, debug_view)` tuple. |

**Returns:**
- If `return_debug=False`: `output` — BGR image with green lane overlay, same dimensions as input frame.
- If `return_debug=True`: `(output, debug_view)` where `debug_view` is a 1280×960 composite showing 4 panels:
  - **Top-Left:** Input frame (resized to 640×480)
  - **Top-Right:** Binary threshold image (white + yellow lane pixels)
  - **Bottom-Left:** Warped bird's-eye view
  - **Bottom-Right:** Output with lane overlay + info text

**Internal pipeline (called in order):**
1. `preprocess(frame)` — Gaussian blur
2. `warp_perspective(preprocessed)` — Bird's-eye transform
3. `thresholding(warped)` — HSV color thresholding → binary
4. `find_lane(binary)` — Histogram peak search → sliding windows → polyfit → validation → smoothing
5. `draw_lane_mask(ploty, left_fitx, right_fitx)` — Fill green polygon in warped space
6. `inverse_warp(mask)` — Warp mask back to original perspective
7. `overlay_lane(frame, mask)` — Blend green mask onto original frame

---

### `preprocess(frame)`

**Purpose:** Apply Gaussian blur to reduce noise.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `frame` | `numpy.ndarray` | BGR image (typically 640×480) |

**Returns:** Blurred BGR image.

**Config:** `GAUSSIAN_BLUR_KERNEL` (default: 5)

---

### `warp_perspective(preprocessed_frame)`

**Purpose:** Transform the image to bird's-eye (top-down) view.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `preprocessed_frame` | `numpy.ndarray` | Blurred BGR image |

**Returns:** Warped BGR image (640×480).

**Config:** `WARP_SRC`, `WARP_DST`, `WARP_WIDTH`, `WARP_HEIGHT`

---

### `thresholding(warped_frame)`

**Purpose:** Convert warped image to binary mask showing only lane line pixels.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `warped_frame` | `numpy.ndarray` | Bird's-eye BGR image |

**Returns:** Single-channel binary image (0 or 255).

**Detection logic:**
- **White lines:** HSV where `V ≥ threshold` (bright) AND `S ≤ 30` (low saturation = white/gray)
- **Yellow lines:** HSV where `H in [10..35]` AND `S ≥ 50` AND `V ≥ 50`

**Config:** `WHITE_THRESHOLD`, `YELLOW_LOW_H`, `YELLOW_HIGH_H`, `YELLOW_MIN_S`, `YELLOW_MIN_V`

---

### `find_lane(binary)`

**Purpose:** Detect left and right lane lines from the binary image.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `binary` | `numpy.ndarray` | Single-channel binary (warped space, 640×480) |

**Returns:** Dictionary with keys:
- `left_fit` — Polynomial coefficients (2nd degree) for left lane, shape `(3,)`
- `right_fit` — Polynomial coefficients for right lane, shape `(3,)`
- `ploty` — y-axis values `np.linspace(0, warp_height-1, warp_height)`, shape `(480,)`
- `left_fitx` — x-coordinates of left lane at each `ploty`, shape `(480,)`
- `right_fitx` — x-coordinates of right lane at each `ploty`, shape `(480,)`
- `debug` — Debug info from sliding windows (windows, indices, etc.)

Returns `None` if no valid lanes found.

**Internal steps:**
1. Compute histogram of bottom half of binary image
2. Find left peak (left half) and right peak (right half) as starting points
3. Run `sliding_windows()` to collect lane pixel indices
4. Fit 2nd-degree polynomial with `np.polyfit()`
5. Validate lane width (must be within `LANE_WIDTH_MIN`..`LANE_WIDTH_MAX`)
6. Apply EMA smoothing using previous frame's fit
7. Fall back to previous fit if validation fails

**Config:** `N_WINDOWS`, `MARGIN`, `MIN_PIXELS`, `POLYFIT_DEGREE`, `LANE_WIDTH_MIN`, `LANE_WIDTH_MAX`, `SMOOTHING_ALPHA`

---

### `sliding_windows(binary, left_base, right_base, return_debug=False)`

**Purpose:** Search for lane pixels using sliding windows from bottom to top.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `binary` | `numpy.ndarray` | required | Binary image in warped space |
| `left_base` | `int` | required | Starting x-coordinate for left lane search |
| `right_base` | `int` | required | Starting x-coordinate for right lane search |
| `return_debug` | `bool` | `False` | Include debug info in return |

**Returns:**
- `(left_fit, right_fit)` — polynomial coefficients if `return_debug=False`
- `(left_fit, right_fit, debug)` — if `return_debug=True`
- `(None, None)` or `(None, None, debug)` — if fitting fails (caught by exception)

---

### `generate_lane_points(left_fit, right_fit)`

**Purpose:** Generate full (x, y) points from polynomial coefficients.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `left_fit` | `numpy.ndarray` | Polynomial coefficients `(3,)` for left lane |
| `right_fit` | `numpy.ndarray` | Polynomial coefficients `(3,)` for right lane |

**Returns:** `(ploty, left_fitx, right_fitx)` — each `numpy.ndarray` of shape `(480,)`.

---

### `validate_lane(left_fitx, right_fitx)`

**Purpose:** Check that lane width is within expected range.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `left_fitx` | `numpy.ndarray` | Left lane x-coordinates |
| `right_fitx` | `numpy.ndarray` | Right lane x-coordinates |

**Returns:** `True` if `LANE_WIDTH_MIN ≤ (right_fitx - left_fitx) ≤ LANE_WIDTH_MAX` for all points, else `False`.

---

### `smooth_lane(left_fit, right_fit)`

**Purpose:** Apply exponential moving average (EMA) to polynomial coefficients across frames.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `left_fit` | `numpy.ndarray` | Current frame's left polynomial coefficients |
| `right_fit` | `numpy.ndarray` | Current frame's right polynomial coefficients |

**Returns:** `(smoothed_left_fit, smoothed_right_fit)`

**Formula:** `fit = α * current_fit + (1 - α) * previous_fit`

**Config:** `SMOOTHING_ALPHA` (default: 0.3 — lower = smoother but more lag)

---

### `compute_center(left_fitx, right_fitx)`

**Purpose:** Compute center line between left and right lanes.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `left_fitx` | `numpy.ndarray` | Left lane x-coordinates |
| `right_fitx` | `numpy.ndarray` | Right lane x-coordinates |

**Returns:** `(left_fitx + right_fitx) / 2` — center x-coordinates, shape `(480,)`.

---

### `draw_lane_mask(ploty, left_fitx, right_fitx)`

**Purpose:** Draw a filled green polygon between the two lane curves in warped space.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `ploty` | `numpy.ndarray` | y-coordinates `(480,)` |
| `left_fitx` | `numpy.ndarray` | Left lane x-coordinates `(480,)` |
| `right_fitx` | `numpy.ndarray` | Right lane x-coordinates `(480,)` |

**Returns:** 3-channel BGR image (640×480) with green (0,255,0) polygon fill.

---

### `inverse_warp(mask)`

**Purpose:** Transform the lane mask from bird's-eye view back to original perspective.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `mask` | `numpy.ndarray` | Lane mask in warped space (640×480) |

**Returns:** Inverse-warped mask in original image space (640×480).

---

### `overlay_lane(frame, inversed_mask)`

**Purpose:** Blend the green lane mask onto the original frame.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `frame` | `numpy.ndarray` | Original BGR image |
| `inversed_mask` | `numpy.ndarray` | Lane mask in original perspective |

**Returns:** `cv.addWeighted(frame, 1.0, mask, 0.6, 0)` — frame with semi-transparent green lane fill.

---

## Configuration Reference (`lane_config.py`)

### Image Dimensions
| Parameter | Default | Description |
|-----------|---------|-------------|
| `IMAGE_WIDTH` | 640 | Input frame width |
| `IMAGE_HEIGHT` | 480 | Input frame height |

### Perspective Transform
| Parameter | Default | Description |
|-----------|---------|-------------|
| `WARP_SRC` | 4 source points | Trapezoid in original image (road region) |
| `WARP_DST` | 4 destination points | Rectangle in bird's-eye view |
| `WARP_WIDTH` | 640 | Output warped image width |
| `WARP_HEIGHT` | 480 | Output warped image height |

### Sliding Windows
| Parameter | Default | Description |
|-----------|---------|-------------|
| `N_WINDOWS` | 9 | Number of vertical search windows |
| `MARGIN` | 100 | Half-width of each window (pixels) |
| `MIN_PIXELS` | 30 | Minimum pixels to re-center window |

### Polynomial Fitting
| Parameter | Default | Description |
|-----------|---------|-------------|
| `POLYFIT_DEGREE` | 2 | Polynomial degree (2 = quadratic) |

### Lane Validation
| Parameter | Default | Description |
|-----------|---------|-------------|
| `LANE_WIDTH_MIN` | 100 | Minimum lane width in warped pixels |
| `LANE_WIDTH_MAX` | 600 | Maximum lane width in warped pixels |

### Smoothing
| Parameter | Default | Description |
|-----------|---------|-------------|
| `SMOOTHING_ALPHA` | 0.3 | EMA factor (lower = smoother) |

### Preprocessing
| Parameter | Default | Description |
|-----------|---------|-------------|
| `GAUSSIAN_BLUR_KERNEL` | 5 | Blur kernel size (odd) |

### Color Thresholds (HSV)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `WHITE_THRESHOLD` | 150 | Minimum V value for white pixels |
| `YELLOW_LOW_H` | 10 | Hue lower bound for yellow |
| `YELLOW_HIGH_H` | 35 | Hue upper bound for yellow |
| `YELLOW_MIN_S` | 50 | Minimum S for yellow |
| `YELLOW_MIN_V` | 50 | Minimum V for yellow |

> **Note:** White saturation upper bound is hardcoded at `S ≤ 30` in `thresholding()`.
> Yellow max saturation/value are both `255`.

