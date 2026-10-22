# How the monitor works

The app has two independent loops: discovery samples sessions every 1,000 ms,
while the Tk canvas redraws horse sprites every 80 ms. These are default
intervals, configurable as constants in `hermes_monitor.py`.

```text
Visible classic console windows (ConsoleWindowClass)
                       |
Candidate Hermes / Python processes + cached command lines
                       |
Walk parent processes to the owning console HWND
                       |
Group all matching workers by that HWND
                       |
Sample CPU activity -> galloping / grazing horse
                       |
Click horse -> restore and focus the owning console
```

One Hermes session may contain a native launcher, a Python environment shim,
and a worker process. Grouping by the owning window prevents those processes
from appearing as several separate sessions. Repeated profile names can still
appear when different windows use the same profile.

Only `hermes.exe`, `python.exe`, and `pythonw.exe` candidates have their command
lines read. The monitor excludes itself and known non-chat commands such as
`gateway`, `sandbox`, `update`, `curator`, and `config`. This is heuristic
matching; launcher and CLI changes may need updates to discovery.

CPU readings use cached `psutil.Process` objects to retain their sampling
baseline. The first reading primes that baseline. Activity above 2% keeps a
background session marked active for three seconds. Foreground terminals do not
refresh that timer, reducing false activity from interactive redraws. A focused
session may therefore graze while work continues.

## Boundaries

- Low CPU can mean waiting for a model/network response, waiting for input, or a
  stalled worker. Grazing is not proof that an agent completed a task.
- Discovery only includes `ConsoleWindowClass` windows. Windows Terminal tabs,
  IDE terminals, WSL, and remote sessions are not supported by this discovery path.
- Command-line matching and parent walking cannot identify every customized
  Hermes launch method.
- Windows foreground restrictions can prevent focus changes, especially across
  privilege levels.
- Window APIs use explicit pointer-sized handle declarations for 64-bit Python.

## Demo path

`--demo` creates three synthetic sessions named `code`, `research`, and `review`.
It uses the production `HorseSprite` and bar widgets, swaps activity every six
seconds, skips process discovery, and disables window focusing. It does not
represent real agent activity or measured project adoption.
