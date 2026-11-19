
import pyautogui
import random
import time
import math
import ctypes
import threading
import platform
from pynput import keyboard


# ==========================================
# CONFIGURATION
# ==========================================

RUN_DURATION = 24 * 60 * 60 * 10  # 24 hours

MIN_MOVE_DURATION = 1.5
MAX_MOVE_DURATION = 4.5

MIN_IDLE_TIME = 2.0
MAX_IDLE_TIME = 6.0

MARGIN = 80

# Windows execution-state constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# Shared application controls
stop_event = threading.Event()
pause_event = threading.Event()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


# ==========================================
# WINDOWS POWER MANAGEMENT
# ==========================================

def keep_computer_awake():
    """Prevent Windows from automatically sleeping."""

    if platform.system() != "Windows":
        raise RuntimeError("This application requires Windows.")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    set_execution_state = kernel32.SetThreadExecutionState
    set_execution_state.argtypes = [ctypes.c_uint]
    set_execution_state.restype = ctypes.c_uint

    result = set_execution_state(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    )

    if result == 0:
        raise ctypes.WinError(ctypes.get_last_error())

    print("[POWER] Windows sleep prevention enabled.")

    return set_execution_state


def restore_power_settings(set_execution_state):
    """Restore normal Windows power-management behavior."""

    if set_execution_state:
        set_execution_state(ES_CONTINUOUS)

    print("[POWER] Normal power management restored.")


# ==========================================
# SCREEN COORDINATES
# ==========================================

def get_random_position():

    width, height = pyautogui.size()

    margin_x = min(MARGIN, max(0, width // 10))
    margin_y = min(MARGIN, max(0, height // 10))

    x = random.randint(margin_x, width - 1 - margin_x)
    y = random.randint(margin_y, height - 1 - margin_y)

    return x, y


# ==========================================
# NATURAL CURSOR MOVEMENT
# ==========================================

def move_naturally(start, end):

    x1, y1 = start
    x2, y2 = end

    distance = math.hypot(x2 - x1, y2 - y1)

    # Determine movement duration
    duration = random.uniform(
        MIN_MOVE_DURATION,
        MAX_MOVE_DURATION
    )

    # More distance means more intermediate points
    steps = max(25, min(180, int(distance / 8)))

    # Generate a curved path using a quadratic Bezier curve
    midpoint_x = (x1 + x2) / 2
    midpoint_y = (y1 + y2) / 2

    # Perpendicular offset creates a natural curved trajectory
    if distance > 0:
        perpendicular_x = -(y2 - y1) / distance
        perpendicular_y = (x2 - x1) / distance
    else:
        perpendicular_x = 0
        perpendicular_y = 0

    curve_strength = random.uniform(-180, 180)

    control_x = midpoint_x + perpendicular_x * curve_strength
    control_y = midpoint_y + perpendicular_y * curve_strength

    for step in range(1, steps + 1):

        if stop_event.is_set():
            return

        # Respect pause requests
        wait_while_paused()

        if stop_event.is_set():
            return

        t = step / steps

        # Smooth acceleration and deceleration
        smooth_t = t * t * (3 - 2 * t)

        # Quadratic Bezier interpolation
        one_minus_t = 1 - smooth_t

        x = (
            one_minus_t ** 2 * x1
            + 2 * one_minus_t * smooth_t * control_x
            + smooth_t ** 2 * x2
        )

        y = (
            one_minus_t ** 2 * y1
            + 2 * one_minus_t * smooth_t * control_y
            + smooth_t ** 2 * y2
        )

        # Very small trajectory variation
        variation = math.sin(t * math.pi) * 1.2

        x += random.uniform(-variation, variation)
        y += random.uniform(-variation, variation)

        pyautogui.moveTo(
            int(x),
            int(y),
            duration=0
        )

        # Small delay between intermediate points
        if stop_event.wait(duration / steps):
            return


# ==========================================
# PAUSE / RESUME HANDLING
# ==========================================

def wait_while_paused():

    while pause_event.is_set() and not stop_event.is_set():
        stop_event.wait(0.2)


def toggle_pause():

    if stop_event.is_set():
        return

    if pause_event.is_set():

        pause_event.clear()
        print("\n[RESUMED] Cursor movement restarted.")

    else:

        pause_event.set()
        print("\n[PAUSED] Cursor movement suspended.")


# ==========================================
# STOP HANDLING
# ==========================================

def stop_application():

    if not stop_event.is_set():

        print("\n[STOP] Stop command received.")
        stop_event.set()


# ==========================================
# KEYBOARD SHORTCUTS
# ==========================================

def start_keyboard_listener():

    hotkeys = keyboard.GlobalHotKeys({

        '<ctrl>+<alt>+p': toggle_pause,

        '<ctrl>+<alt>+s': stop_application

    })

    hotkeys.start()

    print("[KEYBOARD] Shortcuts activated.")

    return hotkeys


# ==========================================
# MAIN APPLICATION
# ==========================================

def main():

    if platform.system() != "Windows":
        raise RuntimeError("Run this program on Windows 11.")

    set_execution_state = None
    listener = None

    start_time = time.monotonic()
    end_time = start_time + RUN_DURATION

    try:

        print("=" * 50)
        print("       ADVANCED PYTHON MOUSE MOVER")
        print("=" * 50)

        print("Operating duration: 24 hours")
        print("Movement: Natural curved trajectories")
        print("Power protection: Enabled")
        print("Startup: Manual")

        print("\nKeyboard shortcuts:")
        print("CTRL + ALT + P : Pause / Resume")
        print("CTRL + ALT + S : Stop")

        print("\nStarting application...\n")

        # Prevent system sleep
        set_execution_state = keep_computer_awake()

        # Start global keyboard listener
        listener = start_keyboard_listener()

        current_position = pyautogui.position()

        print("[RUNNING] Mouse movement active.")

        while not stop_event.is_set():

            # Check the 24-hour deadline
            remaining = end_time - time.monotonic()

            if remaining <= 0:
                print("\n[COMPLETE] 24-hour duration reached.")
                break

            wait_while_paused()

            if stop_event.is_set():
                break

            # Select next destination
            destination = get_random_position()

            # Move along a curved trajectory
            move_naturally(
                current_position,
                destination
            )

            if stop_event.is_set():
                break

            current_position = destination

            # Random interval between movements
            idle_time = random.uniform(
                MIN_IDLE_TIME,
                MAX_IDLE_TIME
            )

            # Wait in small increments so stop remains responsive
            stop_event.wait(min(idle_time, remaining))

    except KeyboardInterrupt:

        print("\n[INTERRUPT] Keyboard interruption received.")

    except pyautogui.FailSafeException:

        print("\n[FAILSAFE] Mouse moved to top-left corner.")

    except Exception as error:

        print(f"\n[ERROR] {error}")

    finally:

        stop_event.set()

        if listener:
            listener.stop()

        restore_power_settings(set_execution_state)

        elapsed = time.monotonic() - start_time

        print("\n" + "=" * 50)
        print("          APPLICATION TERMINATED")
        print("=" * 50)

        print(f"Runtime: {elapsed / 3600:.2f} hours")
        print("Mouse mover stopped.")
        print("Windows power management restored.")


if __name__ == "__main__":
    main()
