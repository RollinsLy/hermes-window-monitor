# Contributing

Small, focused fixes are welcome. This is an independent, Windows-only utility
for Hermes chat sessions, maintained by [RollinsLy](https://github.com/RollinsLy).

## Run locally

```powershell
git clone https://github.com/RollinsLy/hermes-window-monitor.git
cd hermes-window-monitor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe hermes_monitor.py --demo
```

Use `python -m unittest discover -s tests -v` to run regression checks on Windows.
The checks cover process grouping, exclusions, access-denied handling, cache
cleanup, and the demo's isolation from real sessions. They do not establish
compatibility with every terminal or Hermes version.

For changes to discovery or focus behavior, also test two real Hermes sessions
in separate classic console windows. Check that each has one indicator, a busy
background worker animates, closing a window removes its indicator, and clicking
the other indicator focuses the correct terminal. State the Windows, Python,
Hermes, and terminal versions in your pull request.

## Report an issue

Use the repository's bug-report template. Include steps to reproduce and expected
behavior. Redact window titles, profile names, file paths, and command-line
arguments that contain private information. Never attach API keys or chat logs.

## Good first contributions

- Reproduce terminal compatibility limitations with version details.
- Improve discovery tests for legitimate Hermes launcher variants.
- Improve Windows setup instructions or Chinese/English translations.
- Propose a documented, testable alternative to CPU-based activity inference.

Please discuss changes to the activity model or supported terminals in an issue
before a large refactor. Keep the dependency list small and preserve a local-only
monitoring path.
