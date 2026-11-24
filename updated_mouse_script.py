import pyautogui
import random
import time
import math
import ctypes
import threading
from ctypes import wintypes
from pynput import keyboard


# ============================================================
# CONFIGURATION
# ============================================================

RUN_DURATION = 24 * 60 * 60 * 30

IDLE_MIN = 2
IDLE_MAX = 20

CLICK_INTERVAL = 120
CLICK_INTERVAL_VARIATION = 5
CLICK_DELAY = 2

MARGIN = 80

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


# ============================================================
# WINDOWS API
# ============================================================

if not hasattr(ctypes, "WinDLL"):
    raise RuntimeError("This script requires Windows.")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Standard Windows cursor identifiers
SYSTEM_CURSORS = [
    32512, # OCR_NORMAL
    32513, # OCR_IBEAM
    32514, # OCR_WAIT
    32515, # OCR_CROSS
    32516, # OCR_UP
    32640, # OCR_SIZE
    32641, # OCR_ICON
    32642, # OCR_SIZENWSE
    32643, # OCR_SIZENESW
    32644, # OCR_SIZEWE
    32645, # OCR_SIZENS
    32646, # OCR_SIZEALL
    32648, # OCR_NO
    32649, # OCR_HAND
    32650, # OCR_APPSTARTING
    32651, # OCR_HELP
]

SM_CXCURSOR = 13
SM_CYCURSOR = 14

# API declarations
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
kernel32.SetThreadExecutionState.restype = wintypes.DWORD

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.LoadCursorW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p
]
user32.LoadCursorW.restype = ctypes.c_void_p

user32.CopyIcon.argtypes = [ctypes.c_void_p]
user32.CopyIcon.restype = ctypes.c_void_p

user32.CreateCursor.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_void_p
]
user32.CreateCursor.restype = ctypes.c_void_p

user32.SetSystemCursor.argtypes = [
    ctypes.c_void_p,
    wintypes.UINT
]
user32.SetSystemCursor.restype = wintypes.BOOL

user32.DestroyCursor.argtypes = [ctypes.c_void_p]
user32.DestroyCursor.restype = wintypes.BOOL


# ============================================================
# SHARED STATE
# ============================================================

stop_event = threading.Event()
pause_event = threading.Event()

# Stores private copies of cursors that Windows can load.
original_cursors = {}

# Cursor IDs successfully replaced.
hidden_cursor_ids = []


# ============================================================
# TRANSPARENT CURSOR CREATION
# ============================================================

def create_transparent_cursor():

    width = user32.GetSystemMetrics(SM_CXCURSOR)
    height = user32.GetSystemMetrics(SM_CYCURSOR)

    if width <= 0 or height <= 0:
        raise RuntimeError("Could not determine cursor dimensions.")

    mask_size = ((width + 15) // 16) * 2 * height

    and_mask = (
        ctypes.c_ubyte * mask_size
    )(*([0xFF] * mask_size))

    xor_mask = (
        ctypes.c_ubyte * mask_size
    )(*([0x00] * mask_size))

    instance = kernel32.GetModuleHandleW(None)

    cursor = user32.CreateCursor(
        instance,
        0,
        0,
        width,
        height,
        ctypes.cast(and_mask, ctypes.c_void_p),
        ctypes.cast(xor_mask, ctypes.c_void_p)
    )

    if not cursor:
        raise ctypes.WinError(ctypes.get_last_error())

    return cursor


# ============================================================
# SAVE ORIGINAL SYSTEM CURSORS
# ============================================================

def save_original_cursors():

    print("[CURSOR] Checking available Windows cursors...")

    for cursor_id in SYSTEM_CURSORS:

        shared_cursor = user32.LoadCursorW(
            None,
            ctypes.c_void_p(cursor_id)
        )

        if not shared_cursor:
            print(
                f"[CURSOR] Skipping unavailable cursor ID: {cursor_id}"
            )
            continue

        saved_copy = user32.CopyIcon(shared_cursor)

        if not saved_copy:
            print(
                f"[CURSOR] Could not copy cursor ID: {cursor_id}"
            )
            continue

        original_cursors[cursor_id] = saved_copy

    if not original_cursors:
        raise RuntimeError(
            "Windows did not provide any system cursors to replace."
        )

    print(
        f"[CURSOR] Saved {len(original_cursors)} original cursors."
    )


# ============================================================
# HIDE SYSTEM CURSORS
# ============================================================

def hide_system_cursors():

    transparent_cursor = None

    try:

        save_original_cursors()

        print("[CURSOR] Creating transparent cursor...")

        transparent_cursor = create_transparent_cursor()

        print("[CURSOR] Replacing available system cursors...")

        for cursor_id in list(original_cursors.keys()):

            cursor_copy = user32.CopyIcon(transparent_cursor)

            if not cursor_copy:
                print(
                    f"[CURSOR] Could not create copy for ID {cursor_id}"
                )
                continue

            success = user32.SetSystemCursor(
                cursor_copy,
                cursor_id
            )

            if success:

                hidden_cursor_ids.append(cursor_id)

                print(
                    f"[CURSOR] Hidden cursor ID: {cursor_id}"
                )

            else:

                error_code = ctypes.get_last_error()

                user32.DestroyCursor(cursor_copy)

                print(
                    f"[CURSOR] Could not replace ID {cursor_id}: "
                    f"{ctypes.WinError(error_code)}"
                )

        if not hidden_cursor_ids:
            raise RuntimeError(
                "Windows did not allow any system cursors to be replaced."
            )

        print(
            f"[CURSOR] Successfully hidden "
            f"{len(hidden_cursor_ids)} system cursors."
        )

    except Exception:
        restore_system_cursors()
        raise

    finally:

        if transparent_cursor:
            user32.DestroyCursor(transparent_cursor)


# ============================================================
# RESTORE ORIGINAL SYSTEM CURSORS
# ============================================================

def restore_system_cursors():

    if not original_cursors:
        return

    print("[CURSOR] Restoring original Windows cursors...")

    for cursor_id, saved_cursor in list(original_cursors.items()):

        # Restore only cursors that were successfully replaced.
        if cursor_id in hidden_cursor_ids:

            cursor_copy = user32.CopyIcon(saved_cursor)

            if cursor_copy:

                success = user32.SetSystemCursor(
                    cursor_copy,
                    cursor_id
                )

                if not success:

                    error_code = ctypes.get_last_error()

                    user32.DestroyCursor(cursor_copy)

                    print(
                        f"[WARNING] Failed to restore cursor "
                        f"{cursor_id}: {ctypes.WinError(error_code)}"
                    )

            else:

                print(
                    f"[WARNING] Could not copy saved cursor {cursor_id}."
                )

        user32.DestroyCursor(saved_cursor)

    original_cursors.clear()
    hidden_cursor_ids.clear()

    print("[CURSOR] Cursor restoration completed.")


# ============================================================
# POWER MANAGEMENT
# ============================================================

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def prevent_sleep():

    result = kernel32.SetThreadExecutionState(
        ES_CONTINUOUS |
        ES_SYSTEM_REQUIRED |
        ES_DISPLAY_REQUIRED
    )

    if result:
        print("[POWER] Windows sleep prevention enabled.")
    else:
        print("[WARNING] Could not enable sleep prevention.")


def restore_power_settings():

    kernel32.SetThreadExecutionState(ES_CONTINUOUS)

    print("[POWER] Normal power management restored.")


# ============================================================
# NATURAL MOUSE MOVEMENT
# ============================================================

def bezier_point(p0, p1, p2, p3, t):
    """Return a point on a cubic Bézier curve."""
    one_minus_t = 1 - t

    x = (
        one_minus_t ** 3 * p0[0] +
        3 * one_minus_t ** 2 * t * p1[0] +
        3 * one_minus_t * t ** 2 * p2[0] +
        t ** 3 * p3[0]
    )

    y = (
        one_minus_t ** 3 * p0[1] +
        3 * one_minus_t ** 2 * t * p1[1] +
        3 * one_minus_t * t ** 2 * p2[1] +
        t ** 3 * p3[1]
    )

    return x, y


def move_mouse_naturally():
    """Move the pointer along a smooth, gently curved cubic Bézier path."""
    screen_width, screen_height = pyautogui.size()

    max_x = max(MARGIN, screen_width - MARGIN)
    max_y = max(MARGIN, screen_height - MARGIN)

    start_x, start_y = pyautogui.position()

    target_x = random.randint(MARGIN, max_x)
    target_y = random.randint(MARGIN, max_y)

    p0 = (start_x, start_y)
    p3 = (target_x, target_y)

    # Offset the control points from the direct path to create a natural curve.
    dx = target_x - start_x
    dy = target_y - start_y
    curve_scale = random.uniform(0.08, 0.22)

    p1 = (
        start_x + dx * 0.30 - dy * curve_scale + random.uniform(-35, 35),
        start_y + dy * 0.30 + dx * curve_scale + random.uniform(-35, 35)
    )
    p2 = (
        start_x + dx * 0.70 + dy * curve_scale + random.uniform(-35, 35),
        start_y + dy * 0.70 - dx * curve_scale + random.uniform(-35, 35)
    )

    distance = math.hypot(dx, dy)
    steps = max(24, min(120, int(distance / 10)))

    duration = random.uniform(0.6, 1.6)
    step_delay = duration / steps

    for i in range(steps + 1):
        if stop_event.is_set():
            return

        while pause_event.is_set() and not stop_event.is_set():
            time.sleep(0.2)

        if stop_event.is_set():
            return

        t = i / steps
        # Smooth acceleration and deceleration along the curved path.
        t = t * t * (3 - 2 * t)

        x, y = bezier_point(p0, p1, p2, p3, t)

        pyautogui.moveTo(int(x), int(y), duration=0)
        time.sleep(step_delay)


# ============================================================
# INTERRUPTIBLE SLEEP
# ============================================================

def interruptible_sleep(seconds):

    end_time = time.monotonic() + seconds

    while time.monotonic() < end_time:

        if stop_event.is_set():
            return False

        while pause_event.is_set() and not stop_event.is_set():
            time.sleep(0.2)

        if stop_event.is_set():
            return False

        remaining = end_time - time.monotonic()

        time.sleep(min(0.2, max(0, remaining)))

    return True


# ============================================================
# MOUSE CLICKING
# ============================================================

def perform_click_sequence():

    if stop_event.is_set():
        return

    print("[CLICK] Performing two left clicks...")

    pyautogui.click(button="left")

    if not interruptible_sleep(CLICK_DELAY):
        return

    pyautogui.click(button="left")

    print("[CLICK] Click sequence completed.")


# ============================================================
# KEYBOARD CONTROLS
# ============================================================

def toggle_pause():

    if stop_event.is_set():
        return

    if pause_event.is_set():

        pause_event.clear()
        print("[CONTROL] Resumed.")

    else:

        pause_event.set()
        print("[CONTROL] Paused.")


def stop_script():

    print("[CONTROL] Stop command received.")
    stop_event.set()


def start_keyboard_listener():

    hotkeys = keyboard.GlobalHotKeys({
        "<ctrl>+<alt>+p": toggle_pause,
        "<ctrl>+<alt>+s": stop_script
    })

    hotkeys.start()

    return hotkeys


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    start_time = time.monotonic()

    next_click_time = (
        start_time +
        CLICK_INTERVAL +
        random.uniform(
            -CLICK_INTERVAL_VARIATION,
            CLICK_INTERVAL_VARIATION
        )
    )

    listener = None

    print("=" * 55)
    print(" NATURAL MOUSE MOVER")
    print("=" * 55)
    print("Duration: 30 days")
    print("Cursor hiding: Transparent Windows cursors")
    print("CTRL + ALT + P : Pause / Resume")
    print("CTRL + ALT + S : Stop")
    print("=" * 55)

    try:

        prevent_sleep()

        hide_system_cursors()

        listener = start_keyboard_listener()

        print("[RUNNING] Mouse mover is active.")

        while (
            not stop_event.is_set() and
            time.monotonic() - start_time < RUN_DURATION
        ):

            while pause_event.is_set() and not stop_event.is_set():
                time.sleep(0.2)

            if stop_event.is_set():
                break

            if time.monotonic() >= next_click_time:

                perform_click_sequence()

                next_click_time = (
                    time.monotonic() +
                    CLICK_INTERVAL +
                    random.uniform(
                        -CLICK_INTERVAL_VARIATION,
                        CLICK_INTERVAL_VARIATION
                    )
                )

            if stop_event.is_set():
                break

            move_mouse_naturally()

            if stop_event.is_set():
                break

            idle_time = random.uniform(IDLE_MIN, IDLE_MAX)

            interruptible_sleep(idle_time)

        print("[INFO] Mouse mover finished.")

    except pyautogui.FailSafeException:

        print("[SAFETY] PyAutoGUI failsafe triggered.")

    except KeyboardInterrupt:

        print("[CONTROL] Keyboard interruption received.")

    except Exception as error:

        print(f"[ERROR] {error}")

    finally:

        stop_event.set()

        if listener:
            listener.stop()

        restore_system_cursors()

        restore_power_settings()

        print("[EXIT] Script stopped and cleanup completed.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()