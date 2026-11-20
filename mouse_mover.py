
import pyautogui
import random
import time
import math
import ctypes
import threading
import platform
from pynput import keyboard


# ==================================================
# CONFIGURATION
# ==================================================

RUN_DURATION = 24 * 60 * 60 * 10 # 24 hours

# Mouse movement
MIN_MOVE_DURATION = 1.5
MAX_MOVE_DURATION = 4.5

MIN_IDLE_TIME = 2.0
MAX_IDLE_TIME = 6.0

MARGIN = 80

# Double-click configuration
CLICK_ENABLED = True
CLICK_INTERVAL = 120          # 2 minutes
CLICK_RANDOMNESS = 5          # +/- 5 seconds
CLICKS_PER_CYCLE = 2
DOUBLE_CLICK_DELAY = 2        # 2 seconds apart

# Windows power management
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

# Application controls
stop_event = threading.Event()
pause_event = threading.Event()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


# ==================================================
# WINDOWS POWER MANAGEMENT
# ==================================================

def keep_computer_awake():

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

    if set_execution_state:
        set_execution_state(ES_CONTINUOUS)

    print("[POWER] Normal power management restored.")


# ==================================================
# SCREEN COORDINATES
# ==================================================

def get_random_position():

    width, height = pyautogui.size()

    margin_x = min(MARGIN, max(0, width // 10))
    margin_y = min(MARGIN, max(0, height // 10))

    x = random.randint(margin_x, width - 1 - margin_x)
    y = random.randint(margin_y, height - 1 - margin_y)

    return x, y


# ==================================================
# PAUSE / RESUME
# ==================================================

def wait_while_paused():

    while pause_event.is_set() and not stop_event.is_set():
        stop_event.wait(0.2)


def toggle_pause():

    if stop_event.is_set():
        return

    if pause_event.is_set():

        pause_event.clear()
        print("\n[RESUMED] Mouse movement restarted.")

    else:

        pause_event.set()
        print("\n[PAUSED] Mouse movement suspended.")


# ==================================================
# STOP APPLICATION
# ==================================================

def stop_application():

    if not stop_event.is_set():

        print("\n[STOP] Stop command received.")
        stop_event.set()


# ==================================================
# NATURAL CURSOR MOVEMENT
# ==================================================

def move_naturally(start, end):

    x1, y1 = start
    x2, y2 = end

    distance = math.hypot(x2 - x1, y2 - y1)

    duration = random.uniform(
        MIN_MOVE_DURATION,
        MAX_MOVE_DURATION
    )

    steps = max(25, min(180, int(distance / 8)))

    midpoint_x = (x1 + x2) / 2
    midpoint_y = (y1 + y2) / 2

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

        wait_while_paused()

        if stop_event.is_set():
            return

        t = step / steps

        # Smooth acceleration and deceleration
        smooth_t = t * t * (3 - 2 * t)

        one_minus_t = 1 - smooth_t

        # Quadratic Bezier curve
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

        variation = math.sin(t * math.pi) * 1.2

        x += random.uniform(-variation, variation)
        y += random.uniform(-variation, variation)

        pyautogui.moveTo(
            int(x),
            int(y),
            duration=0
        )

        if stop_event.wait(duration / steps):
            return


# ==================================================
# DOUBLE-CLICK FUNCTION
# ==================================================

def perform_periodic_click():

    if not CLICK_ENABLED or stop_event.is_set():
        return

    wait_while_paused()

    if stop_event.is_set():
        return

    # Capture current position for both clicks
    position = pyautogui.position()

    for click_number in range(1, CLICKS_PER_CYCLE + 1):

        wait_while_paused()

        if stop_event.is_set():
            return

        # Keep both clicks at the same position
        pyautogui.click(
            x=position.x,
            y=position.y,
            button="left"
        )

        print(
            f"[CLICK] Click {click_number}/{CLICKS_PER_CYCLE} "
            f"at {position} | {time.strftime('%H:%M:%S')}"
        )

        # Wait exactly 2 seconds between clicks
        if click_number < CLICKS_PER_CYCLE:

            wait_until = (
                time.monotonic() + DOUBLE_CLICK_DELAY
            )

            while time.monotonic() < wait_until:

                wait_while_paused()

                if stop_event.is_set():
                    return

                remaining = wait_until - time.monotonic()

                stop_event.wait(min(0.1, remaining))


# ==================================================
# KEYBOARD SHORTCUTS
# ==================================================

def start_keyboard_listener():

    hotkeys = keyboard.GlobalHotKeys({

        '<ctrl>+<alt>+p': toggle_pause,

        '<ctrl>+<alt>+s': stop_application

    })

    hotkeys.start()

    print("[KEYBOARD] Global shortcuts activated.")

    return hotkeys


# ==================================================
# MAIN APPLICATION
# ==================================================

def main():

    if platform.system() != "Windows":
        raise RuntimeError("Run this program on Windows 11.")

    set_execution_state = None
    listener = None

    start_time = time.monotonic()
    end_time = start_time + RUN_DURATION

    try:

        print("=" * 55)
        print("          ADVANCED PYTHON MOUSE MOVER")
        print("=" * 55)

        print("Operating duration : 24 hours")
        print("Movement           : Natural curved movement")
        print("Clicking           : Two left-clicks per cycle")
        print("Click interval     : Approximately 2 minutes")
        print("Time between clicks: 2 seconds")
        print("Power protection   : Enabled")
        print("Startup            : Manual")

        print("\nKEYBOARD SHORTCUTS")
        print("CTRL + ALT + P : Pause / Resume")
        print("CTRL + ALT + S : Stop")

        print("\nStarting application...\n")

        # Prevent Windows from automatically sleeping
        set_execution_state = keep_computer_awake()

        # Activate global keyboard shortcuts
        listener = start_keyboard_listener()

        current_position = pyautogui.position()

        # Schedule first double-click
        next_click_time = (
            time.monotonic() + CLICK_INTERVAL
        )

        print("[RUNNING] Mouse movement active.")

        while not stop_event.is_set():

            remaining = end_time - time.monotonic()

            if remaining <= 0:

                print("\n[COMPLETE] 24-hour duration reached.")
                break

            wait_while_paused()

            if stop_event.is_set():
                break

            # Check double-click schedule
            if time.monotonic() >= next_click_time:

                perform_periodic_click()

                next_click_time = (
                    time.monotonic()
                    + CLICK_INTERVAL
                    + random.uniform(
                        -CLICK_RANDOMNESS,
                        CLICK_RANDOMNESS
                    )
                )

            if stop_event.is_set():
                break

            # Generate next cursor destination
            destination = get_random_position()

            # Move cursor naturally
            move_naturally(
                current_position,
                destination
            )

            if stop_event.is_set():
                break

            current_position = destination

            # Short random idle period
            idle_time = random.uniform(
                MIN_IDLE_TIME,
                MAX_IDLE_TIME
            )

            stop_event.wait(
                min(idle_time, remaining, 1)
            )

    except KeyboardInterrupt:

        print("\n[INTERRUPT] Keyboard interruption received.")

    except pyautogui.FailSafeException:

        print("\n[FAILSAFE] Emergency mouse failsafe activated.")

    except Exception as error:

        print(f"\n[ERROR] {error}")

    finally:

        stop_event.set()

        if listener:

            listener.stop()
            listener.join(timeout=2)

        restore_power_settings(set_execution_state)

        elapsed = time.monotonic() - start_time

        print("\n" + "=" * 55)
        print("             APPLICATION TERMINATED")
        print("=" * 55)

        print(f"Runtime: {elapsed / 3600:.2f} hours")
        print("Mouse mover stopped.")
        print("Windows power management restored.")


# ==================================================
# APPLICATION ENTRY POINT
# ==================================================

if __name__ == "__main__":
    main()
