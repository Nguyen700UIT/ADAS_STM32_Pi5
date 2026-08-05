"""
Interactive keyboard test for SignController.

Controls
--------
  Q  –  Turn LEFT
  E  –  Turn RIGHT
  F  –  STOP (brake)
  X  –  Quit

The script sends commands at ~20 Hz so that the EMA ramp in
SignController produces a smooth transition.

Usage
-----
  # Real UART (default /dev/ttyAMA0):
  python -m adas.tests.test_sign_control
  
  # Or with arguments:
  python -m adas.tests.test_sign_control --port /dev/ttyUSB0
  
  # Or simulation only:
  python -m adas.tests.test_sign_control --simulate
"""

import argparse
import sys
import time
import os

# ── keyboard input (non-blocking, no echo) ──────────────────────────
if os.name == "nt":
    import msvcrt

    def _get_key():
        """Return a single key press on Windows, or None."""
        if msvcrt.kbhit():
            return msvcrt.getch().decode("utf-8", errors="ignore").lower()
        return None
else:
    import tty
    import termios
    import select

    def _get_key():
        """Return a single key press on Linux/macOS, or None."""
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            return sys.stdin.read(1).lower()
        return None


# ── imports from the project ────────────────────────────────────────
from control.sign_controller import SignController
from config import sign_config as cfg


# ── pretty console helpers ──────────────────────────────────────────
_ACTION_LABEL = {
    "idle": "\033[90m   IDLE   \033[0m",
    "left": "\033[94m◀◀ LEFT  \033[0m",
    "right": "\033[93m  RIGHT ▶▶\033[0m",
    "stop": "\033[91m■■ STOP  \033[0m",
}


def _print_hud(action: str, ctrl: SignController, connected: bool, tx_count: int):
    """Overwrite the current terminal line with live status."""
    mode = "\033[92mUART\033[0m" if connected else "\033[93mSIM\033[0m"
    steer = ctrl.current_steering
    speed = ctrl.current_speed
    bar_len = 20
    bar_pos = int((steer + 100) / 200 * bar_len)
    bar = "─" * bar_pos + "●" + "─" * (bar_len - bar_pos)

    line = (
        f"\r  [{mode}]  {_ACTION_LABEL.get(action, action)}  "
        f"Steer: {steer:+7.1f}  [{bar}]  "
        f"Speed: {speed:5.1f}  "
        f"TX: {tx_count:>5d}"
    )
    sys.stdout.write(line)
    sys.stdout.flush()


# ── main ────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive keyboard test for SignController (Q/E/F)"
    )
    parser.add_argument(
        "--port", default="/dev/ttyAMA0", help="UART port (default: /dev/ttyAMA0)"
    )
    parser.add_argument(
        "--baud", type=int, default=115200, help="UART baud rate (default: 115200)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulation mode – skip UART, just print commands",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=20,
        help="Command send rate in Hz (default: 20)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    loop_period = 1.0 / args.rate

    # ── banner ──────────────────────────────────────────────────────
    print(f"\n{'═' * 60}")
    print("  SignController – Keyboard Test")
    print(f"{'═' * 60}")
    print(f"  Port:       {args.port}")
    print(f"  Baud:       {args.baud}")
    print(f"  Rate:       {args.rate} Hz")
    print(f"  Simulate:   {args.simulate}")
    print(f"{'─' * 60}")
    print(f"  Config:")
    print(f"    TURN_LEFT_STEERING  = {cfg.TURN_LEFT_STEERING}")
    print(f"    TURN_RIGHT_STEERING = {cfg.TURN_RIGHT_STEERING}")
    print(f"    TURN_SPEED          = {cfg.TURN_SPEED}")
    print(f"    STOP_SPEED          = {cfg.STOP_SPEED}")
    print(f"    STEERING_RAMP_ALPHA = {cfg.STEERING_RAMP_ALPHA}")
    print(f"    SPEED_RAMP_ALPHA    = {cfg.SPEED_RAMP_ALPHA}")
    print(f"{'─' * 60}")
    print("  Controls:")
    print("    Q  →  Turn LEFT")
    print("    E  →  Turn RIGHT")
    print("    F  →  STOP (brake)")
    print("    X  →  Quit")
    print(f"{'═' * 60}\n")

    # ── create controller ───────────────────────────────────────────
    if args.simulate:
        # Monkey-patch UART so nothing is actually sent
        ctrl = SignController.__new__(SignController)
        ctrl.turn_left_steering = cfg.TURN_LEFT_STEERING
        ctrl.turn_right_steering = cfg.TURN_RIGHT_STEERING
        ctrl.turn_speed = cfg.TURN_SPEED
        ctrl.stop_speed = cfg.STOP_SPEED
        ctrl.stop_steering = cfg.STOP_STEERING
        ctrl.steering_ramp_alpha = cfg.STEERING_RAMP_ALPHA
        ctrl.speed_ramp_alpha = cfg.SPEED_RAMP_ALPHA
        ctrl.current_steering = 0.0
        ctrl.current_speed = 0.0
        ctrl.last_send_time = time.time()
        ctrl.last_stm32_response = None
        ctrl.uart_connected = False

        # Stub UART methods
        class _FakeUart:
            serial_port = None
            def send_data(self, cmd_id, target_speed, steering_error, brake_command):
                pass
            def read_latest_telemetry(self):
                return None
            def close(self):
                pass

        ctrl.uart = _FakeUart()
        connected = False
        print("  [SIM] Running in simulation mode – no UART traffic.\n")
    else:
        ctrl = SignController(port=args.port, baudrate=args.baud)
        connected = ctrl.is_connected()
        if connected:
            print(f"  [OK] UART connected on {args.port}\n")
        else:
            print(f"  [WARN] UART failed to connect on {args.port} – falling back to SIM.\n")

    # ── set terminal to raw mode (Linux/macOS) ──────────────────────
    old_settings = None
    if os.name != "nt":
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    action = "idle"
    tx_count = 0

    try:
        while True:
            t0 = time.time()

            # ── read key ────────────────────────────────────────────
            key = _get_key()
            if key == "q":
                action = "left"
            elif key == "e":
                action = "right"
            elif key == "f":
                action = "stop"
            elif key == "x":
                print("\n\n  [EXIT] Quit requested.")
                break

            # ── execute action ──────────────────────────────────────
            if action == "left":
                ctrl.execute_turn_left()
                tx_count += 1
            elif action == "right":
                ctrl.execute_turn_right()
                tx_count += 1
            elif action == "stop":
                ctrl.execute_stop()
                tx_count += 1
            elif action == "idle":
                ctrl.execute_idle()
                tx_count += 1

            # ── read STM32 response (if connected) ─────────────────
            if connected:
                resp = ctrl.read_stm32_response()
                if resp:
                    sys.stdout.write(
                        f"\n  [RX] L:{resp['distance_left']}cm  "
                        f"R:{resp['distance_right']}cm  "
                        f"RPM:{resp['actual_rpm']}\n"
                    )

            # ── HUD ─────────────────────────────────────────────────
            _print_hud(action, ctrl, connected, tx_count)

            # ── pace the loop ───────────────────────────────────────
            elapsed = time.time() - t0
            sleep_time = loop_period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\n  [EXIT] Interrupted by Ctrl+C.")
    finally:
        # ── restore terminal ────────────────────────────────────────
        if old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        ctrl.close()

        print(f"\n{'═' * 60}")
        print("  Session Summary")
        print(f"{'═' * 60}")
        print(f"  Total TX commands:  {tx_count}")
        print(f"  Last action:        {action}")
        print(f"  Last steering:      {ctrl.current_steering:+.1f}")
        print(f"  Last speed:         {ctrl.current_speed:.1f}")
        print(f"{'═' * 60}")
        print("  Done.\n")


if __name__ == "__main__":
    main()
