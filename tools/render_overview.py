"""Build the README's illustrated SVG using the production horse drawing code.

Run on Windows: python tools/render_overview.py
The artwork uses simulated states, not captured user sessions.
"""
from html import escape
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hermes_monitor import HorseSprite  # noqa: E402


class SVGCanvas:
    def __init__(self):
        self.shapes = []

    def delete(self, _tag):
        self.shapes.clear()

    def create_line(self, *coords, **style):
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(coords[::2], coords[1::2]))
        self.shapes.append(
            f'<polyline points="{points}" fill="none" stroke="{style.get("fill", "black")}" '
            f'stroke-width="{style.get("width", 1)}" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    def create_polygon(self, *coords, **style):
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(coords[::2], coords[1::2]))
        self.shapes.append(f'<polygon points="{points}" fill="{style.get("fill", "black")}"/>')


def horse(running):
    sprite = HorseSprite.__new__(HorseSprite)
    sprite.canvas = SVGCanvas()
    sprite.running = running
    sprite.frame = 2 if running else 9
    sprite.draw()
    return "".join(sprite.canvas.shapes)


def build():
    cards = []
    for i, (profile, running, label) in enumerate((
        ("code", True, "RECENT ACTIVITY"),
        ("research", False, "QUIET / CHECK IN"),
        ("review", False, "QUIET / CHECK IN"),
    )):
        x = 74 + i * 354
        cards.append(f'''
        <g transform="translate({x},326)">
          <rect width="344" height="174" rx="14" fill="#1e1e1e"/>
          <text x="22" y="32" fill="#a7ada5" font-size="14" letter-spacing="1.5">{escape(profile.upper())}</text>
          <g transform="translate(24,57) scale(3.3)">{horse(running)}</g>
          <circle cx="182" cy="89" r="4" fill="{'#d8a657' if running else '#8ca47b'}"/>
          <text x="197" y="95" fill="#eeeee7" font-size="18">{'Galloping' if running else 'Grazing'}</text>
          <text x="22" y="151" fill="{'#d8a657' if running else '#a7ada5'}" font-size="11" letter-spacing="1.4">{label}</text>
        </g>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
      <title>Hermes Window Monitor — one window, one horse</title>
      <desc>Illustration of three simulated sessions. Code is active; research and review are quiet. CPU activity is an estimate, not a task completion event.</desc>
      <rect width="1200" height="630" fill="#f3f1e9"/>
      <path d="M0 0H1200V12H0Z" fill="#3e5944"/>
      <g font-family="Segoe UI,Arial,sans-serif">
        <rect x="74" y="58" width="32" height="32" rx="8" fill="#3e5944"/>
        <path d="M83 80V68M97 80V68M83 74H97" stroke="#f3f1e9" stroke-width="2"/>
        <text x="118" y="81" font-size="20" font-weight="600" fill="#263d2d">Hermes Window Monitor</text>
        <text x="1126" y="78" text-anchor="end" font-size="12" letter-spacing="2" fill="#5d6d5a">WINDOWS · MIT · LOCAL</text>
        <text x="74" y="160" font-size="12" letter-spacing="3" fill="#6b795f">ONE WINDOW. ONE HORSE.</text>
        <text x="70" y="224" font-size="54" font-weight="600" letter-spacing="-1.8" fill="#263d2d">Know when to jump back in.</text>
        <text x="74" y="269" font-size="21" fill="#61705e">A small companion for your herd of Hermes chat windows.</text>
        {''.join(cards)}
        <path d="M74 540H1126" stroke="#d8dcd0"/>
        <text x="74" y="574" font-size="15" fill="#40563f">Always on top</text>
        <text x="319" y="574" font-size="15" fill="#40563f">Click to focus</text>
        <text x="554" y="574" font-size="15" fill="#40563f">No account or API key</text>
        <text x="1126" y="574" text-anchor="end" font-size="11" fill="#74806d">ILLUSTRATED PREVIEW · SIMULATED STATES</text>
      </g>
    </svg>'''


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "docs" / "assets" / "overview.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(line.rstrip() for line in build().splitlines()) + "\n",
                      encoding="utf-8")
    print(target)
