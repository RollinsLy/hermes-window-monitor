# Changelog

## 0.2.0 — 2026-10-22

- Add `--demo` to preview three simulated sessions without running Hermes,
  inspecting processes, or focusing other windows.
- Add bilingual documentation, a visual overview, architecture notes,
  troubleshooting, contribution guidance, and issue templates.
- Add Windows CI and regression coverage for session discovery and demo isolation.
- Declare pointer-sized Win32 window-handle types explicitly for 64-bit Python.
- Clarify that CPU activity is a heuristic and document classic-console-only
  discovery and foreground-terminal behavior.

## Initial implementation — 2026-06-11

- Group Hermes workers by terminal window.
- Display galloping and grazing horse indicators with click-to-focus tooltips.
