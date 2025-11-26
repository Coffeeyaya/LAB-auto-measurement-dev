import pyautogui
import time

try:
    while True:
        x, y = pyautogui.position()
        print(f"Cursor position: ({x}, {y})", end="\r")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopped.")
