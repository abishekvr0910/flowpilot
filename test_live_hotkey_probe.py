import time
import sys
from pynput import keyboard

print("Starting live keyboard hook probe for 10 seconds...")
print("Normalized keys will be printed to stdout...")

events_captured = []

def normalize_key(k):
    if k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        return "ctrl"
    if k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, getattr(keyboard.Key, 'alt_gr', None)):
        return "alt"
    if k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
        return "shift"
    if k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
        return "cmd"
    if k == keyboard.Key.space:
        return "space"
    if k == keyboard.Key.f8:
        return "f8"
    if k == keyboard.Key.f9:
        return "f9"
    return getattr(k, "char", str(k)).lower()

def on_press(key):
    k = normalize_key(key)
    events_captured.append(("press", k))
    print(f"[Probe DOWN] {k} (raw: {key})", flush=True)

def on_release(key):
    k = normalize_key(key)
    events_captured.append(("release", k))
    print(f"[Probe UP] {k}", flush=True)

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()
print("Listener thread started. Is alive:", listener.is_alive())

# Simulate a programmatic key press to verify if the hook catches it
import win32api
import win32con
time.sleep(1.0)
print("Simulating Win32 F9 key event...")
win32api.keybd_event(win32con.VK_F9, 0, 0, 0)
time.sleep(0.05)
win32api.keybd_event(win32con.VK_F9, 0, win32con.KEYEVENTF_KEYUP, 0)

time.sleep(2.0)
listener.stop()
print(f"Probe finished. Captured events: {events_captured}")
