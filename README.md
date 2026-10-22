<p align="center">
  <img src="docs/assets/overview.png" alt="Hermes Window Monitor: one horse per chat window. Galloping means recent CPU activity; grazing means no recent activity." width="100%">
</p>

# Hermes Window Monitor

**See which Hermes window needs your attention.**

A small, always-on-top Windows companion for people running several
[Hermes](https://github.com/NousResearch/hermes-agent) chat sessions. One horse
per classic console window: it gallops when background CPU activity is detected
and grazes when activity goes quiet. Click a horse to return to that terminal.

[中文说明](README.zh-CN.md) · [Quick start](#quick-start) ·
[How it works](docs/architecture.md) · [Report a bug](https://github.com/RollinsLy/hermes-window-monitor/issues/new/choose)

![Windows checks](https://github.com/RollinsLy/hermes-window-monitor/actions/workflows/checks.yml/badge.svg)
![Python 3.10+ recommended](https://img.shields.io/badge/Python-3.10%2B_recommended-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D4)
![MIT license](https://img.shields.io/badge/License-MIT-6E8655)

## A glance instead of another round of Alt+Tab

When several agents live in separate terminals, their windows look similar and
their state is easy to lose track of. This bar keeps a compact, visible cue for
each window, without reading conversations or integrating with a model API.

| Cue | Meaning | Action |
| --- | --- | --- |
| Galloping horse | CPU activity was recently observed in a background session | Let it work |
| Grazing horse | No recent activity was observed | Check whether it needs you |
| Hover | Profile, window title, process IDs, and current inferred state | Identify the session |
| Click | Restore and focus the corresponding terminal | Resume the conversation |

**Activity is a heuristic.** A quiet worker may be waiting for a model response
or may be stalled. Grazing does not prove task completion. A foreground
terminal does not refresh the activity timer, to reduce false positives from
interactive redraws.

## Quick start

Requires Windows, CPython with Tkinter, and `psutil`. Python 3.10+ is recommended
and checked in CI; the source uses Python 3.8-compatible syntax. Hermes must run
in separate **classic console windows** (`ConsoleWindowClass`) for live discovery.
Windows Terminal tabs and IDE terminals are not supported by the current scanner.

```powershell
git clone https://github.com/RollinsLy/hermes-window-monitor.git
cd hermes-window-monitor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe hermes_monitor.py --demo
```

The demo uses three clearly marked simulated sessions, shows the real horse
widgets, and changes activity every six seconds. It does not inspect processes
or focus other windows. Close it with **×**.

For live sessions, omit `--demo`:

```powershell
.\.venv\Scripts\python.exe hermes_monitor.py
```

Open Hermes in a supported console and its horse appears automatically. Drag
the **≡** handle to reposition the bar. Closing the bar leaves your Hermes
sessions running.

For a launch without an extra console window:

```powershell
.\.venv\Scripts\pythonw.exe hermes_monitor.py
```

`run.bat` is also available when `pythonw` on your PATH has the dependencies
installed. The explicit virtual-environment command above avoids interpreter
mismatches.

## Why one horse per window?

A Hermes chat can be a chain of launcher, environment shim, and worker
processes. The monitor walks their parents and groups them by the owning
terminal's window handle, so those processes produce one indicator. Two windows
using the same Hermes profile still receive separate horses.

The horse is a small nod to the Chinese nickname for Hermes, **爱马仕**:
running several sessions is playfully called **养马**, or raising horses.

## Local by design

No account, API key, or network service is required by the monitor. It reads
process metadata and CPU activity locally, and uses Windows APIs to identify
and focus console windows. It does not read chat history or terminal contents.
Command lines and window titles may still be sensitive; redact screenshots
before sharing them. See [security and privacy](SECURITY.md).

## Troubleshooting

| Problem | Check |
| --- | --- |
| `No module named psutil` | Install requirements with the same Python executable used to launch the app. |
| `no hermes windows` | Try `--demo`, then confirm Hermes is running in a classic console. Windows Terminal tabs, IDE terminals, WSL, and remote sessions are outside the current discovery path. |
| Horse grazes while work continues | CPU is only a proxy; network waits and foreground sessions can look idle. |
| Clicking does not focus a window | Keep Hermes and the monitor at the same privilege level. Windows can restrict foreground changes. |
| Several identical profile names | Each horse belongs to a different window. Hover for its title or click to identify it. |
| Silent startup from `pythonw` | Run with `python` in a terminal to see the error. Check that your CPython installation includes Tkinter. |

## Adjust the bar

Edit the constants near the top of `hermes_monitor.py`, then restart:

| Constant | Default | Purpose |
| --- | --- | --- |
| `CPU_ACTIVE_THRESHOLD` | `2.0` | CPU percentage treated as activity |
| `IDLE_SECONDS` | `3.0` | Activity hold time in seconds |
| `SCAN_INTERVAL_MS` | `1000` | Process discovery and CPU sampling interval |
| `ANIM_INTERVAL_MS` | `80` | Horse animation interval |
| `HORSE_SCALE` | `1.0` | Sprite size multiplier |
| `RUN_CYCLE_FRAMES` | `8` | Frames in a gallop cycle |
| `GRAZE_CYCLE_FRAMES` | `40` | Frames in a grazing cycle |

Horse, grass, background, and text colors are configurable in the same section.

## Development

```powershell
python -m unittest discover -s tests -v
```

Windows CI checks Python 3.10 and 3.13. Regression tests cover process grouping,
excluded commands, access-denied handling, cache cleanup, and demo isolation.
See [contributing](CONTRIBUTING.md), [architecture](docs/architecture.md), and
[changelog](CHANGELOG.md).

The project is small and early-stage. Useful next contributions include verified
terminal compatibility reports, more launcher-variant tests, and a more reliable
activity signal. Broader terminal support is a future direction, not a current
feature.

## License and affiliation

[MIT](LICENSE) · Maintained by [RollinsLy](https://github.com/RollinsLy).

An independent community utility; not an official Hermes, Nous Research, or
OpenAI product.
