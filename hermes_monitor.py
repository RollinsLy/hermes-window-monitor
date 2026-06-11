#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes Window Monitor
=====================

A tiny always-on-top indicator bar that shows one lamp per open Hermes
chat window (cmd.exe terminal hosting a `hermes ... chat` session).

  * GREEN  -> the session's worker process had CPU activity in the last
              few seconds (it is generating / running tools / printing).
  * RED    -> idle: the turn is finished, it is your move now.

Click any lamp to bring that terminal window to the foreground so you can
type into it.

Why lamps are grouped by window handle (HWND):
  Each Hermes chat window is actually a chain of processes
  (native hermes.exe launcher -> venv python -> uv cpython worker).
  They all share ONE owning cmd.exe window. We group every Hermes process
  by the HWND of its window-owning ancestor, so one terminal window = one
  lamp, regardless of how many python processes live inside it.

Requirements: Windows, Python 3.8+, psutil.
Standard library only otherwise (tkinter + ctypes).
"""

import ctypes
import math
import re
import sys
import time
from ctypes import wintypes

try:
    import psutil
except ImportError:
    sys.stderr.write("This tool needs psutil:  pip install psutil\n")
    sys.exit(1)

import tkinter as tk
import tkinter.font as tkfont


# --------------------------------------------------------------------------
# Tunables
# --------------------------------------------------------------------------
CPU_ACTIVE_THRESHOLD = 2.0   # process CPU% above this counts as "active"
IDLE_SECONDS = 3.0           # idle longer than this -> horse stops running
SCAN_INTERVAL_MS = 1000      # how often we rescan processes / sample CPU
ANIM_INTERVAL_MS = 80        # how often we advance the horse animation frame

# -- horse rendering --------------------------------------------------------
HORSE_W = 34                 # canvas width per horse (px)
HORSE_H = 22                 # canvas height per horse (px)
HORSE_SCALE = 1.0            # overall horse size multiplier
RUN_CYCLE_FRAMES = 8         # frames in one gallop stride
GRAZE_CYCLE_FRAMES = 40      # frames in one slow graze bob (head down/up)

COLOR_HORSE = "#d8a657"      # running horse body (warm tan)
COLOR_HORSE_IDLE = "#7a8a6a" # grazing horse body (calm muted green-brown)
COLOR_HORSE_MANE = "#3a2e1f" # mane / tail / hooves outline
COLOR_GROUND = "#3a3a3a"     # the little ground line under the horse
COLOR_GRASS = "#5fa83f"      # grass tufts the idle horse nibbles
COLOR_BG = "#1e1e1e"
COLOR_FG = "#dddddd"


# --------------------------------------------------------------------------
# Win32 plumbing
# --------------------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetClassNameW.restype = ctypes.c_int
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

SW_RESTORE = 9


def enum_visible_windows():
    """Return (pid_to_hwnd, hwnd_to_title) for visible, titled top-level windows."""
    windows = []

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        # Only enumerate real terminal windows.  During Alt+Tab Windows
        # briefly creates overlay / thumbnail windows that would cause
        # ghost lamps if we counted them.
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        if cls_buf.value != "ConsoleWindowClass":
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        windows.append((hwnd, pid.value, buf.value))
        return True

    user32.EnumWindows(EnumWindowsProc(_cb), 0)

    pid_to_hwnd = {}
    hwnd_to_title = {}
    for hwnd, pid, title in windows:
        hwnd_to_title[hwnd] = title
        # keep the first titled window we see for a pid
        pid_to_hwnd.setdefault(pid, hwnd)
    return pid_to_hwnd, hwnd_to_title


def bring_to_front(hwnd):
    """Restore + raise a window to the foreground as reliably as Windows allows."""
    user32.ShowWindow(hwnd, SW_RESTORE)
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    cur_thread = kernel32.GetCurrentThreadId()
    attached = False
    try:
        if fg_thread and fg_thread != cur_thread:
            user32.AttachThreadInput(cur_thread, fg_thread, True)
            attached = True
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(cur_thread, fg_thread, False)


# --------------------------------------------------------------------------
# Process scanning
# --------------------------------------------------------------------------
_PROFILE_RE = re.compile(r"(?:-p|--profile)\s+(\S+)")

# Only these process names can be part of a Hermes session. Reading cmdline on
# Windows is expensive (opens a handle, reads the PEB), so we never call it for
# the hundreds of unrelated processes on the system.
_HERMES_PROC_NAMES = {"hermes.exe", "python.exe", "pythonw.exe"}

# cmdline never changes over a pid's lifetime -> cache it once and reuse.
_cmdline_cache = {}


def _cmdline(proc):
    pid = proc.pid
    cached = _cmdline_cache.get(pid)
    if cached is not None:
        return cached
    try:
        cmd = " ".join(proc.cmdline() or [])
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        cmd = ""
    except Exception:
        cmd = ""
    _cmdline_cache[pid] = cmd
    return cmd


def _is_hermes_session_cmd(low):
    """True if this cmdline belongs to an interactive Hermes chat session.

    We deliberately do NOT require the literal word "chat": launching the bare
    `hermes` command drops you straight into a chat session, and its cmdline is
    just `...\\hermes.exe` with no subcommand. We only need to (a) confirm it is
    a Hermes invocation and (b) rule out the non-chat subcommands that also live
    under hermes.exe (gateway daemon, sandbox helpers, update, etc.).
    """
    if "hermes" not in low:
        return False
    # This very monitor runs as `pythonw hermes_monitor.py` -- its cmdline
    # contains "hermes" too. Never count ourselves as a session window.
    if "hermes_monitor" in low:
        return False
    for bad in ("gateway", "sandbox", " update", "curator", "config "):
        if bad in low:
            return False
    return True


def scan_sessions():
    """
    Discover Hermes chat windows.

    Returns a dict: hwnd -> {
        'hwnd': int,
        'title': str,
        'profile': str,
        'pids': set[int],   # every Hermes process living under this window
    }
    """
    pid_to_hwnd, hwnd_to_title = enum_visible_windows()

    # Cheap pass: names + ppids only, no cmdline yet.
    procs = {}
    for p in psutil.process_iter(["pid", "name", "ppid"]):
        procs[p.pid] = p

    # Drop cmdline cache entries for pids that no longer exist.
    live = set(procs)
    for dead in [pid for pid in _cmdline_cache if pid not in live]:
        _cmdline_cache.pop(dead, None)

    def ancestors(pid):
        chain = []
        cur = procs.get(pid)
        seen = set()
        while cur and cur.pid not in seen:
            seen.add(cur.pid)
            chain.append(cur.pid)
            try:
                pp = cur.ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            cur = procs.get(pp)
        return chain

    def owner_hwnd(pid):
        for anc in ancestors(pid):
            if anc in pid_to_hwnd:
                return pid_to_hwnd[anc]
        return None

    # Single pass over Hermes-named processes only. Reading cmdline for anything
    # else would be wasted (and slow) work.
    sessions = {}
    for p in list(procs.values()):
        name = (p.info.get("name") or "").lower()
        if name not in _HERMES_PROC_NAMES:
            continue
        cmd = _cmdline(p)
        low = cmd.lower()
        if not _is_hermes_session_cmd(low):
            continue
        hwnd = owner_hwnd(p.pid)
        if hwnd is None:
            continue
        # Skip processes whose only "window" is the desktop shell: these are
        # orphaned workers left behind when a terminal was closed with the X
        # button. They have no real console window to focus.
        title = hwnd_to_title.get(hwnd, "")
        if title == "Program Manager":
            continue
        sess = sessions.setdefault(
            hwnd,
            {"hwnd": hwnd, "title": title, "profile": None, "pids": set()},
        )
        sess["pids"].add(p.pid)
        if sess["profile"] is None:
            m = _PROFILE_RE.search(cmd)
            if m:
                sess["profile"] = m.group(1)

    for sess in sessions.values():
        if not sess["profile"]:
            sess["profile"] = "default"

    return sessions


# --------------------------------------------------------------------------
# Horse sprite  (爱马仕养马: working = galloping, idle = grazing)
# --------------------------------------------------------------------------
class HorseSprite:
    """A tiny side-view vector horse drawn on a Canvas.

    running=True  -> gallops in place (body bobs, four legs cycle)
    running=False -> grazes (head down nibbling grass, tail slow-sways)
    Coordinates are authored in a 34x22 box, then scaled by HORSE_SCALE.
    """

    def __init__(self, parent):
        self.w = int(HORSE_W * HORSE_SCALE)
        self.h = int(HORSE_H * HORSE_SCALE)
        self.canvas = tk.Canvas(parent, width=self.w, height=self.h,
                                bg=COLOR_BG, highlightthickness=0)
        self.running = False
        self.frame = 0

    def _s(self, *pts):
        """Scale a flat list of authored coords to canvas pixels."""
        return [p * HORSE_SCALE for p in pts]

    def set_running(self, running):
        self.running = running

    # -- per-frame redraw --------------------------------------------------
    def draw(self):
        self.frame += 1
        c = self.canvas
        c.delete("all")

        body_fill = COLOR_HORSE if self.running else COLOR_HORSE_IDLE
        ground_y = 20

        # ground line
        c.create_line(*self._s(1, ground_y + 1, 33, ground_y + 1),
                      fill=COLOR_GROUND, width=1)

        if self.running:
            self._draw_running(c, body_fill, ground_y)
        else:
            self._draw_grazing(c, body_fill, ground_y)

    # -- gallop ------------------------------------------------------------
    def _draw_running(self, c, fill, ground_y):
        phase = (self.frame % RUN_CYCLE_FRAMES) / RUN_CYCLE_FRAMES * 2 * math.pi
        bob = math.sin(phase * 2) * 1.3          # body vertical bounce
        cy = -bob                                # negative = up

        # legs (drawn first, behind body). hips: back x=10, front x=20
        leg_specs = [
            (10, 0.0),            # back-near
            (12, math.pi),        # back-far
            (19, math.pi / 2),    # front-near
            (21, 3 * math.pi / 2) # front-far
        ]
        for hip_x, off in leg_specs:
            swing = math.sin(phase + off)
            hoof_x = hip_x + 4.5 * swing
            lift = max(0.0, math.sin(phase + off + math.pi / 2)) * 3.5
            hoof_y = ground_y - lift
            c.create_line(*self._s(hip_x, 13 + cy, hoof_x, hoof_y),
                          fill=COLOR_HORSE_MANE, width=2)

        # body (rump left, chest right)
        c.create_polygon(
            *self._s(6, 11 + cy, 9, 8 + cy, 18, 8 + cy,
                     22, 10 + cy, 21, 14 + cy, 7, 14 + cy),
            fill=fill, outline=fill, smooth=True)

        # neck + head, raised forward
        c.create_polygon(
            *self._s(19, 9 + cy, 24, 4 + cy, 28, 3 + cy,
                     29, 6 + cy, 25, 8 + cy, 21, 11 + cy),
            fill=fill, outline=fill, smooth=True)
        # muzzle
        c.create_polygon(*self._s(27, 3 + cy, 32, 4 + cy, 30, 7 + cy, 26, 6 + cy),
                         fill=fill, outline=fill)
        # ear
        c.create_polygon(*self._s(24, 4 + cy, 25, 1 + cy, 26, 4 + cy),
                         fill=COLOR_HORSE_MANE, outline="")
        # mane streaming back
        c.create_line(*self._s(24, 4 + cy, 20, 6 + cy, 18, 8 + cy),
                      fill=COLOR_HORSE_MANE, width=2, smooth=True)
        # tail streaming back (flares with gallop)
        flare = math.sin(phase) * 2
        c.create_line(*self._s(6, 10 + cy, 2, 11 + cy + flare,
                               1, 15 + cy + flare),
                      fill=COLOR_HORSE_MANE, width=2, smooth=True)

    # -- graze -------------------------------------------------------------
    def _draw_grazing(self, c, fill, ground_y):
        gp = (self.frame % GRAZE_CYCLE_FRAMES) / GRAZE_CYCLE_FRAMES * 2 * math.pi
        nod = (math.sin(gp) + 1) / 2          # 0..1, head dip amount
        # grass tufts on the ground the horse nibbles at
        for gx in (27, 30, 32):
            c.create_line(*self._s(gx, ground_y + 1, gx - 1, ground_y - 3),
                          fill=COLOR_GRASS, width=1)
            c.create_line(*self._s(gx, ground_y + 1, gx + 1, ground_y - 2),
                          fill=COLOR_GRASS, width=1)

        # four legs planted straight on the ground
        for hip_x in (9, 11, 19, 21):
            c.create_line(*self._s(hip_x, 13, hip_x, ground_y),
                          fill=COLOR_HORSE_MANE, width=2)

        # body (standing calm)
        c.create_polygon(
            *self._s(6, 11, 9, 8, 18, 8, 22, 10, 21, 14, 7, 14),
            fill=fill, outline=fill, smooth=True)

        # neck + head dipping toward grass.  nod=1 -> muzzle at ground
        neck_x = 24 + 2 * nod
        head_y = 5 + 11 * nod                 # 5 (up) .. 16 (near ground)
        c.create_polygon(
            *self._s(19, 9, neck_x, 5 + 6 * nod, neck_x + 4, head_y,
                     neck_x + 3, head_y + 2, 23, 10 + 2 * nod, 21, 11),
            fill=fill, outline=fill, smooth=True)
        # muzzle reaching grass
        c.create_polygon(
            *self._s(neck_x + 3, head_y, neck_x + 7, head_y + 1,
                     neck_x + 6, head_y + 3, neck_x + 2, head_y + 2),
            fill=fill, outline=fill)
        # ear
        c.create_polygon(*self._s(neck_x, 5 + 6 * nod, neck_x + 1,
                                  2 + 6 * nod, neck_x + 2, 5 + 6 * nod),
                         fill=COLOR_HORSE_MANE, outline="")
        # tail slow sway
        sway = math.sin(gp * 1.5) * 2
        c.create_line(*self._s(6, 10, 3, 13 + sway, 2, 17 + sway),
                      fill=COLOR_HORSE_MANE, width=2, smooth=True)


# --------------------------------------------------------------------------
# Tooltip
# --------------------------------------------------------------------------
class Tooltip:
    def __init__(self, widget, text_getter):
        self.widget = widget
        self.text_getter = text_getter
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _evt=None):
        if self.tip:
            return
        text = self.text_getter()
        if not text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.attributes("-topmost", True)
        lbl = tk.Label(self.tip, text=text, justify="left",
                       bg="#000000", fg="#eeeeee",
                       relief="solid", borderwidth=1,
                       font=("Consolas", 8), padx=6, pady=3)
        lbl.pack()

    def _hide(self, _evt=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# --------------------------------------------------------------------------
# The lamp bar app
# --------------------------------------------------------------------------
class MonitorApp:
    def __init__(self):
        self.proc_cache = {}        # pid -> psutil.Process (keeps cpu_percent baseline)
        self.last_active = {}       # hwnd -> timestamp of last detected activity
        self.lamps = {}             # hwnd -> dict of widgets + state

        self.root = tk.Tk()
        self.root.title("Hermes Monitor")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=COLOR_BG)
        self.root.geometry("+12+12")

        self.font = tkfont.Font(family="Segoe UI", size=8)

        outer = tk.Frame(self.root, bg=COLOR_BG, highlightthickness=1,
                         highlightbackground="#444444")
        outer.pack()

        # drag handle (also doubles as the title) + close button
        self.handle = tk.Label(outer, text="≡", bg=COLOR_BG, fg="#888888",
                               font=("Segoe UI", 9), cursor="fleur", padx=4)
        self.handle.pack(side="left")
        self._make_draggable(self.handle)
        self._make_draggable(outer)

        self.bar = tk.Frame(outer, bg=COLOR_BG)
        self.bar.pack(side="left", padx=2, pady=3)

        self.empty_label = tk.Label(self.bar, text="no hermes windows",
                                    bg=COLOR_BG, fg="#666666", font=self.font)

        close = tk.Label(outer, text="✕", bg=COLOR_BG, fg="#888888",
                         font=("Segoe UI", 9), cursor="hand2", padx=5)
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self.root.destroy())

        self.tick()
        self.animate()

    # -- window dragging --------------------------------------------------
    def _make_draggable(self, widget):
        widget.bind("<Button-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_move, add="+")

    def _drag_start(self, evt):
        self._dx = evt.x_root - self.root.winfo_x()
        self._dy = evt.y_root - self.root.winfo_y()

    def _drag_move(self, evt):
        self.root.geometry(f"+{evt.x_root - self._dx}+{evt.y_root - self._dy}")

    # -- lamp widgets -----------------------------------------------------
    def _make_lamp(self, hwnd, sess):
        frame = tk.Frame(self.bar, bg=COLOR_BG, cursor="hand2")
        horse = HorseSprite(frame)
        horse.canvas.pack(side="left")
        horse.draw()
        label = tk.Label(frame, text=sess["profile"], bg=COLOR_BG, fg=COLOR_FG,
                         font=self.font)
        label.pack(side="left", padx=(2, 8))

        lamp = {"frame": frame, "horse": horse,
                "label": label, "state": "red", "sess": sess}

        def _click(_evt, h=hwnd):
            cur = self.lamps.get(h)
            if cur:
                bring_to_front(cur["sess"]["hwnd"])

        for w in (frame, horse.canvas, label):
            w.bind("<Button-1>", _click)

        Tooltip(frame, lambda h=hwnd: self._tooltip_text(h))
        return lamp

    def _tooltip_text(self, hwnd):
        lamp = self.lamps.get(hwnd)
        if not lamp:
            return ""
        sess = lamp["sess"]
        pids = ", ".join(str(p) for p in sorted(sess["pids"]))
        title = sess["title"] or "(no title)"
        horse_state = "running (working)" if lamp["state"] == "green" \
            else "grazing (idle)"
        return (f"profile: {sess['profile']}\n"
                f"state:   {horse_state}\n"
                f"title:   {title}\n"
                f"hwnd:    {sess['hwnd']}\n"
                f"pids:    {pids}\n"
                f"(click to focus this window)")

    def _set_state(self, lamp, state):
        lamp["state"] = state
        lamp["horse"].set_running(state == "green")

    # -- main loop --------------------------------------------------------
    def tick(self):
        try:
            self._refresh()
        except Exception as exc:  # never let the UI loop die silently
            sys.stderr.write(f"[scan error] {exc}\n")
        self.root.after(SCAN_INTERVAL_MS, self.tick)

    def animate(self):
        """Advance every horse one frame. Runs faster than the scan loop
        so the gallop / graze motion stays smooth."""
        try:
            for lamp in self.lamps.values():
                lamp["horse"].draw()
        except Exception as exc:
            sys.stderr.write(f"[anim error] {exc}\n")
        self.root.after(ANIM_INTERVAL_MS, self.animate)

    def _refresh(self):
        now = time.time()
        sessions = scan_sessions()

        # prune cached Process objects for pids that vanished
        live_pids = set()
        for s in sessions.values():
            live_pids |= s["pids"]
        for pid in list(self.proc_cache):
            if pid not in live_pids:
                self.proc_cache.pop(pid, None)

        # Get the current foreground window once per tick.
        fg_hwnd = user32.GetForegroundWindow()

        # sample CPU per session; any active worker keeps the window "alive"
        for hwnd, sess in sessions.items():
            active = False
            for pid in sess["pids"]:
                proc = self.proc_cache.get(pid)
                if proc is None:
                    try:
                        proc = psutil.Process(pid)
                        proc.cpu_percent(None)  # prime baseline; reads 0 first time
                        self.proc_cache[pid] = proc
                        continue
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                try:
                    if proc.cpu_percent(None) >= CPU_ACTIVE_THRESHOLD:
                        active = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    self.proc_cache.pop(pid, None)
            # Foreground exemption: when the user is actively looking at /
            # typing into a terminal, its CPU spikes come from TUI redraw,
            # not from the AI generating.  Don't count them — the user can
            # see the terminal directly and doesn't need the lamp.
            if active and hwnd != fg_hwnd:
                self.last_active[hwnd] = now

        # reconcile lamp widgets with current sessions
        current = set(sessions)
        existing = set(self.lamps)

        for hwnd in existing - current:          # window closed -> remove lamp
            self.lamps[hwnd]["frame"].destroy()
            del self.lamps[hwnd]
            self.last_active.pop(hwnd, None)

        for hwnd in current - existing:          # new window -> add lamp
            self.lamps[hwnd] = self._make_lamp(hwnd, sessions[hwnd])
            self.lamps[hwnd]["frame"].pack(side="left")

        for hwnd in current:                     # update color + cached session
            lamp = self.lamps[hwnd]
            lamp["sess"] = sessions[hwnd]
            lamp["label"].config(text=sessions[hwnd]["profile"])
            idle = now - self.last_active.get(hwnd, 0)
            self._set_state(lamp, "green" if idle < IDLE_SECONDS else "red")

        # show / hide the empty placeholder
        if not self.lamps:
            self.empty_label.pack(side="left", padx=4)
        else:
            self.empty_label.pack_forget()

    def run(self):
        self.root.mainloop()


def main():
    if not sys.platform.startswith("win"):
        sys.stderr.write("Hermes Window Monitor only runs on Windows.\n")
        sys.exit(1)
    MonitorApp().run()


if __name__ == "__main__":
    main()
