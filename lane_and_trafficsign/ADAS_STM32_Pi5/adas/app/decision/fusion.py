from enum import Enum

try:
    from ..config import sign_config as cfg
except ImportError:
    from config import sign_config as cfg


class FusionState(Enum):
    """Operating states for the ADAS fusion controller."""
    LANE_FOLLOWING = "lane_following"
    TURNING_LEFT = "turning_left"
    TURNING_RIGHT = "turning_right"
    STOPPED = "stopped"


class FusionController:
    """State machine that coordinates LaneController and SignController.

    Each frame, call ``update()`` with the latest perception results.
    The controller decides which sub-controller is active and sends the
    appropriate commands to the STM32.

    State transitions
    -----------------
    LANE_FOLLOWING  →  TURNING_LEFT   : "turn_left" detected
    LANE_FOLLOWING  →  TURNING_RIGHT  : "turn_right" detected
    LANE_FOLLOWING  →  STOPPED        : "stop" detected
    TURNING_LEFT    →  LANE_FOLLOWING  : sign gone AND lane_valid
    TURNING_RIGHT   →  LANE_FOLLOWING  : sign gone AND lane_valid
    STOPPED         →  LANE_FOLLOWING  : sign gone
    """

    def __init__(self, lane_controller, sign_controller):
        """
        Parameters
        ----------
        lane_controller : LaneController
            Handles lane-following UART commands.
        sign_controller : SignController
            Handles sign-action UART commands (turn / stop).
        """
        self.lane_ctrl = lane_controller
        self.sign_ctrl = sign_controller
        self.state = FusionState.LANE_FOLLOWING

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update(self, detected_signs, left_fit, right_fit,
               center_fitx, ploty, lane_valid):
        """Run one decision cycle.

        Parameters
        ----------
        detected_signs : list[str]
            Sign class names returned by ``SignDetector.find_sign()``.
        left_fit, right_fit, center_fitx, ploty :
            Lane detection outputs forwarded to ``LaneController.update()``.
        lane_valid : bool
            Whether a lane was successfully detected this frame.

        Returns
        -------
        dict
            Status information for logging / debugging.
        """
        has_stop = cfg.CLASS_STOP in detected_signs
        has_left = cfg.CLASS_TURN_LEFT in detected_signs
        has_right = cfg.CLASS_TURN_RIGHT in detected_signs

        # ----- LANE_FOLLOWING state -----
        if self.state == FusionState.LANE_FOLLOWING:
            # Priority: stop > turn_left > turn_right
            if has_stop:
                self.state = FusionState.STOPPED
                self.sign_ctrl.execute_stop()
                return self._status("stop sign detected → STOPPED")

            if has_left:
                self.state = FusionState.TURNING_LEFT
                self.sign_ctrl.execute_turn_left()
                return self._status("turn_left sign detected → TURNING_LEFT")

            if has_right:
                self.state = FusionState.TURNING_RIGHT
                self.sign_ctrl.execute_turn_right()
                return self._status("turn_right sign detected → TURNING_RIGHT")

            # No actionable sign — normal lane following
            lane_result = self.lane_ctrl.update(
                left_fit, right_fit, center_fitx, ploty, lane_valid
            )
            return self._status("lane following", lane_result=lane_result)

        # ----- STOPPED state -----
        if self.state == FusionState.STOPPED:
            if has_stop:
                # Sign still visible — keep stopped
                self.sign_ctrl.execute_stop()
                return self._status("stop sign still visible — holding stop")

            # Sign gone — resume lane following
            self.state = FusionState.LANE_FOLLOWING
            lane_result = self.lane_ctrl.update(
                left_fit, right_fit, center_fitx, ploty, lane_valid
            )
            return self._status(
                "stop sign gone → LANE_FOLLOWING", lane_result=lane_result
            )

        # ----- TURNING_LEFT state -----
        if self.state == FusionState.TURNING_LEFT:
            if not has_left and lane_valid:
                # Sign disappeared and we see a lane — resume
                self.state = FusionState.LANE_FOLLOWING
                lane_result = self.lane_ctrl.update(
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )
                return self._status(
                    "turn_left sign gone + lane valid → LANE_FOLLOWING",
                    lane_result=lane_result,
                )

            # Still turning
            self.sign_ctrl.execute_turn_left()
            return self._status("turning left — waiting for sign gone + lane")

        # ----- TURNING_RIGHT state -----
        if self.state == FusionState.TURNING_RIGHT:
            if not has_right and lane_valid:
                self.state = FusionState.LANE_FOLLOWING
                lane_result = self.lane_ctrl.update(
                    left_fit, right_fit, center_fitx, ploty, lane_valid
                )
                return self._status(
                    "turn_right sign gone + lane valid → LANE_FOLLOWING",
                    lane_result=lane_result,
                )

            self.sign_ctrl.execute_turn_right()
            return self._status("turning right — waiting for sign gone + lane")

        # Fallback (should never reach here)
        return self._status("unknown state")

    def reset(self):
        """Reset the fusion controller to its initial state."""
        self.state = FusionState.LANE_FOLLOWING
        self.lane_ctrl.reset()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _status(self, message, lane_result=None):
        return {
            "state": self.state.value,
            "message": message,
            "lane_result": lane_result,
        }
