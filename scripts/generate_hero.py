#!/usr/bin/env python3
"""Generate the responsive hero banners for the profile README.

The SVGs are committed to the repository so GitHub serves them directly.
Run from the repository root:

    python scripts/generate_hero.py
"""

from __future__ import annotations

import base64
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
OUT_DIR = ROOT / "assets" / "hero"


def font_data(name: str) -> str:
    return base64.b64encode((FONT_DIR / name).read_bytes()).decode("ascii")


SPACE = font_data("space-grotesk-latin.woff2")
MONO = font_data("jetbrains-mono-latin.woff2")

THEMES = {
    "dark": {
        "bg": "#070A10",
        "bg2": "#0B1119",
        "text": "#F4F1E8",
        "muted": "#9AA4B2",
        "dim": "#606B7A",
        "accent": "#F2B84B",
        "accent2": "#63E6C4",
        "accent3": "#7AA2F7",
        "accent4": "#F78C6C",
        "line": "#FFFFFF",
        "line_opacity": "0.10",
        "grid_opacity": "0.045",
        "glow_a": "0.17",
        "glow_b": "0.12",
        "pill_fill": "0.08",
        "pill_stroke": "0.28",
    },
    "light": {
        "bg": "#F6F1E7",
        "bg2": "#FCF9F3",
        "text": "#12161D",
        "muted": "#5E6675",
        "dim": "#8A909B",
        "accent": "#B8740F",
        "accent2": "#0E8C78",
        "accent3": "#2F5FD0",
        "accent4": "#C2410C",
        "line": "#12161D",
        "line_opacity": "0.12",
        "grid_opacity": "0.055",
        "glow_a": "0.13",
        "glow_b": "0.10",
        "pill_fill": "0.08",
        "pill_stroke": "0.26",
    },
}

FONT_CSS = f"""
@font-face {{
  font-family: 'Space Grotesk';
  src: url(data:font/woff2;base64,{SPACE}) format('woff2');
  font-style: normal;
  font-weight: 300;
  font-display: swap;
}}
@font-face {{
  font-family: 'JetBrains Mono';
  src: url(data:font/woff2;base64,{MONO}) format('woff2');
  font-style: normal;
  font-weight: 400;
  font-display: swap;
}}
.sans {{ font-family: 'Space Grotesk', 'Segoe UI', Helvetica, Arial, sans-serif; }}
.mono {{ font-family: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace; }}
.spin-slow {{
  transform-box: view-box;
  animation: hero-spin 52s linear infinite;
}}
.spin-reverse {{
  transform-box: view-box;
  animation: hero-spin-reverse 74s linear infinite;
}}
.pulse {{
  transform-box: fill-box;
  transform-origin: center;
  animation: hero-pulse 3.6s ease-in-out infinite;
}}
.twinkle {{
  animation: hero-twinkle 6s ease-in-out infinite;
}}
@keyframes hero-spin {{ to {{ transform: rotate(360deg); }} }}
@keyframes hero-spin-reverse {{ to {{ transform: rotate(-360deg); }} }}
@keyframes hero-pulse {{
  0%, 100% {{ opacity: .42; transform: scale(.86); }}
  50% {{ opacity: 1; transform: scale(1.15); }}
}}
@keyframes hero-twinkle {{
  0%, 100% {{ opacity: .18; }}
  50% {{ opacity: .62; }}
}}
@media (prefers-reduced-motion: reduce) {{
  .spin-slow, .spin-reverse, .pulse, .twinkle {{ animation: none !important; }}
}}
"""


def esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def defs(theme: dict[str, str], width: int) -> str:
    return f"""
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{width}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{theme['bg']}"/>
      <stop offset="1" stop-color="{theme['bg2']}"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" fill="none" stroke="{theme['line']}" stroke-opacity="{theme['grid_opacity']}" stroke-width="1"/>
    </pattern>
    <radialGradient id="grid-fade" cx="50%" cy="50%" r="72%">
      <stop offset="0" stop-color="#FFFFFF"/>
      <stop offset=".62" stop-color="#FFFFFF" stop-opacity=".62"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
    <mask id="grid-mask"><rect width="{width}" height="100%" fill="url(#grid-fade)"/></mask>
    <radialGradient id="glow-accent" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="{theme['accent']}" stop-opacity="{theme['glow_a']}"/>
      <stop offset="1" stop-color="{theme['accent']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow-mint" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="{theme['accent2']}" stop-opacity="{theme['glow_b']}"/>
      <stop offset="1" stop-color="{theme['accent2']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="mono-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="{theme['accent2']}" stop-opacity=".14"/>
      <stop offset="1" stop-color="{theme['accent2']}" stop-opacity="0"/>
    </radialGradient>
    <clipPath id="card-clip">
      <rect width="{width}" height="100%" rx="26"/>
    </clipPath>
  </defs>
"""


def stars(theme: dict[str, str], points: list[tuple[int, int, float, float]]) -> str:
    out = []
    for x, y, r, op in points:
        out.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{theme["text"]}" opacity="{op}"/>'
        )
    return "\n".join(out)


def emblem(theme: dict[str, str], cx: float, cy: float, r: float, mobile: bool = False) -> str:
    """A technical monogram: orbits, ticks, nodes, and a rotating ring."""
    accent = theme["accent"]
    accent2 = theme["accent2"]
    accent3 = theme["accent3"]
    accent4 = theme["accent4"]
    line = theme["line"]
    lo = theme["line_opacity"]
    text = theme["text"]
    muted = theme["muted"]
    dim = theme["dim"]

    ticks = []
    for i in range(36):
        angle = math.radians(i * 10)
        x1 = cx + math.cos(angle) * (r - (7 if i % 3 == 0 else 4))
        y1 = cy + math.sin(angle) * (r - (7 if i % 3 == 0 else 4))
        x2 = cx + math.cos(angle) * r
        y2 = cy + math.sin(angle) * r
        opacity = 0.18 if i % 3 == 0 else 0.09
        ticks.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{line}" stroke-opacity="{opacity}" stroke-width="1"/>'
        )

    nodes = []
    labels = []
    if not mobile:
        node_specs = [
            (-45, accent3, "LLM", 1),
            (-135, accent, "VISION", -1),
            (135, accent4, "AUTOMATION", -1),
            (45, accent2, "MOBILE", 1),
        ]
    else:
        node_specs = [
            (-45, accent3, "", 1),
            (-135, accent, "", -1),
            (135, accent4, "", -1),
            (45, accent2, "", 1),
        ]

    for deg, color, label, side in node_specs:
        a = math.radians(deg)
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        x_in = cx + math.cos(a) * (r - 34)
        y_in = cy + math.sin(a) * (r - 34)
        nodes.append(
            f'<line x1="{x_in:.2f}" y1="{y_in:.2f}" x2="{x:.2f}" y2="{y:.2f}" stroke="{color}" stroke-opacity=".28" stroke-width="1"/>'
        )
        nodes.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{7 if not mobile else 5.5}" fill="{theme["bg"]}" stroke="{color}" stroke-opacity=".7" stroke-width="1.2"/>'
        )
        nodes.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{3 if not mobile else 2.4}" fill="{color}"/>'
        )
        if label:
            lx = x + (14 * side)
            ly = y + 3.5
            anchor = "start" if side > 0 else "end"
            labels.append(
                f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}" class="mono" font-size="10" letter-spacing="1.5" fill="{muted}">{esc(label)}</text>'
            )

    cross = f"""
    <line x1="{cx - r - 34:.2f}" y1="{cy}" x2="{cx + r + 34:.2f}" y2="{cy}" stroke="{line}" stroke-opacity=".07" stroke-width="1"/>
    <line x1="{cx}" y1="{cy - r - 34:.2f}" x2="{cx}" y2="{cy + r + 34:.2f}" stroke="{line}" stroke-opacity=".07" stroke-width="1"/>
    """

    inner = f"""
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#mono-glow)"/>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{line}" stroke-opacity="{lo}" stroke-width="1"/>
    <circle cx="{cx}" cy="{cy}" r="{r - 28}" fill="none" stroke="{line}" stroke-opacity=".16" stroke-width="1"/>
    {''.join(ticks)}
    {cross}
    <g class="spin-slow" style="transform-origin:{cx}px {cy}px">
      <circle cx="{cx}" cy="{cy}" r="{r - 14}" fill="none" stroke="{accent}" stroke-opacity=".42" stroke-width="1" stroke-dasharray="1 11" stroke-linecap="round"/>
      <circle cx="{cx}" cy="{cy - r + 14}" r="3.2" fill="{accent}"/>
    </g>
    <g class="spin-reverse" style="transform-origin:{cx}px {cy}px">
      <circle cx="{cx}" cy="{cy}" r="{r - 42}" fill="none" stroke="{accent2}" stroke-opacity=".30" stroke-width="1" stroke-dasharray="2 15" stroke-linecap="round"/>
    </g>
    <circle cx="{cx}" cy="{cy}" r="{r - 28}" fill="none" stroke="{accent2}" stroke-opacity=".16" stroke-width="1">
      <animate attributeName="r" values="{r - 28};{r - 23};{r - 28}" dur="5s" repeatCount="indefinite"/>
      <animate attributeName="stroke-opacity" values=".10;.26;.10" dur="5s" repeatCount="indefinite"/>
    </circle>
    {''.join(nodes)}
    <text x="{cx}" y="{cy + (2 if not mobile else 1)}" text-anchor="middle" dominant-baseline="middle" class="sans" font-size="{76 if not mobile else 48}" font-weight="300" letter-spacing="-3" fill="{text}">NC</text>
    {"" if mobile else f'<text x="{cx}" y="{cy + 48}" text-anchor="middle" class="mono" font-size="8.5" letter-spacing="2.4" fill="{dim}">APPLIED SYSTEMS</text>'}
    {''.join(labels)}
    """
    return inner


def build_desktop(theme_name: str) -> str:
    t = THEMES[theme_name]
    W, H = 1280, 420
    hero = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-labelledby="hero-title hero-desc">
  <title id="hero-title">Nest Chao — Applied AI, computer vision, and systems</title>
  <desc id="hero-desc">A dark editorial banner with the name Nest Chao, the line “I build systems that see, listen, and think,” and a technical NC monogram with orbit nodes for vision, LLM, mobile, and automation.</desc>
  <style>{FONT_CSS}</style>
  {defs(t, W)}
  <g clip-path="url(#card-clip)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#grid-mask)"/>
    <circle cx="1050" cy="76" r="360" fill="url(#glow-accent)"/>
    <circle cx="1190" cy="390" r="300" fill="url(#glow-mint)"/>
    {stars(t, [(150, 50, 1.4, .35), (236, 372, 1.2, .22), (410, 48, 1, .28), (790, 382, 1.4, .18), (1210, 44, 1.2, .30), (340, 112, 0.9, .22)])}
    <path d="M72 118C260 58 420 48 640 48" stroke="{t['accent']}" stroke-opacity=".18" stroke-width="1" stroke-dasharray="1 8"/>
    <g class="twinkle">
      <circle cx="1200" cy="54" r="2.2" fill="{t['accent']}"/>
    </g>

    <g transform="translate(72 78)">
      <rect x="0" y="-4" width="8" height="8" transform="rotate(45 4 0)" fill="{t['accent']}"/>
      <text x="22" y="4" class="mono" font-size="12" letter-spacing="2.2" fill="{t['muted']}">APPLIED AI / COMPUTER VISION / SYSTEMS</text>
    </g>

    <text x="71" y="190" class="sans" font-size="82" font-weight="300" letter-spacing="-2.8" fill="{t['text']}">NEST CHAO</text>
    <rect x="73" y="208" width="64" height="3" rx="1.5" fill="{t['accent']}"/>
    <text x="72" y="253" class="sans" font-size="24" font-weight="300" letter-spacing="-.2" fill="{t['muted']}">I build systems that see, listen, and think.</text>
    <text x="72" y="291" class="mono" font-size="14" letter-spacing="1.45" fill="{t['dim']}">ANDROID · WINDOWS · LOCAL AI · AUTOMATION</text>

    <g>
      <rect x="72" y="326" width="312" height="40" rx="20" fill="{t['accent2']}" fill-opacity="{t['pill_fill']}" stroke="{t['accent2']}" stroke-opacity="{t['pill_stroke']}"/>
      <circle cx="95" cy="346" r="4" fill="{t['accent2']}" class="pulse"/>
      <circle cx="95" cy="346" r="8.5" fill="none" stroke="{t['accent2']}" stroke-opacity=".22"/>
      <text x="112" y="350" class="mono" font-size="13" letter-spacing="1.05" fill="{t['accent2']}">CURRENTLY BUILDING — SONICBRIEF</text>
    </g>

    <text x="72" y="392" class="mono" font-size="12" letter-spacing=".6" fill="{t['dim']}">github.com/nestchao</text>
    <text x="1208" y="392" text-anchor="end" class="mono" font-size="12" letter-spacing=".6" fill="{t['dim']}">nestchao.github.io</text>

    {emblem(t, 1000, 210, 168)}
  </g>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="25.5" stroke="{t['line']}" stroke-opacity="{t['line_opacity']}"/>
</svg>
"""
    return hero


def build_mobile(theme_name: str) -> str:
    t = THEMES[theme_name]
    W, H = 480, 540
    hero = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-labelledby="hero-title hero-desc">
  <title id="hero-title">Nest Chao — Applied AI, computer vision, and systems</title>
  <desc id="hero-desc">A mobile banner with the name Nest Chao, the line “I build systems that see, listen, and think,” and a technical NC monogram.</desc>
  <style>{FONT_CSS}</style>
  {defs(t, W)}
  <g clip-path="url(#card-clip)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#grid-mask)"/>
    <circle cx="390" cy="80" r="230" fill="url(#glow-accent)"/>
    <circle cx="80" cy="470" r="190" fill="url(#glow-mint)"/>
    {stars(t, [(64, 38, 1.2, .30), (420, 34, 1.0, .24), (448, 250, .9, .18), (32, 300, 1.0, .18)])}

    <g transform="translate(32 56)">
      <rect x="0" y="-4" width="7" height="7" transform="rotate(45 3.5 0)" fill="{t['accent']}"/>
      <text x="18" y="3.5" class="mono" font-size="10.5" letter-spacing="1.45" fill="{t['muted']}">APPLIED AI / VISION / SYSTEMS</text>
    </g>

    <text x="31" y="132" class="sans" font-size="60" font-weight="300" letter-spacing="-2.3" fill="{t['text']}">NEST CHAO</text>
    <rect x="33" y="150" width="48" height="3" rx="1.5" fill="{t['accent']}"/>
    <text x="32" y="196" class="sans" font-size="26" font-weight="300" fill="{t['muted']}">I build systems that</text>
    <text x="32" y="226" class="sans" font-size="26" font-weight="300" fill="{t['muted']}">see, listen, and think.</text>
    <text x="32" y="262" class="mono" font-size="12.5" letter-spacing="1.15" fill="{t['dim']}">ANDROID · WINDOWS · LOCAL AI</text>

    <g>
      <rect x="32" y="288" width="312" height="38" rx="19" fill="{t['accent2']}" fill-opacity="{t['pill_fill']}" stroke="{t['accent2']}" stroke-opacity="{t['pill_stroke']}"/>
      <circle cx="54" cy="307" r="3.8" fill="{t['accent2']}" class="pulse"/>
      <circle cx="54" cy="307" r="8" fill="none" stroke="{t['accent2']}" stroke-opacity=".22"/>
      <text x="70" y="311" class="mono" font-size="12.5" letter-spacing=".95" fill="{t['accent2']}">BUILDING SONICBRIEF</text>
    </g>

    {emblem(t, 240, 420, 82, mobile=True)}

    <line x1="32" y1="508" x2="448" y2="508" stroke="{t['line']}" stroke-opacity=".08"/>
    <text x="240" y="523" text-anchor="middle" class="mono" font-size="11.5" letter-spacing=".45" fill="{t['dim']}">github.com/nestchao  ·  nestchao.github.io</text>
  </g>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="25.5" stroke="{t['line']}" stroke-opacity="{t['line_opacity']}"/>
</svg>
"""
    return hero


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (OUT_DIR / f"hero-desktop-{theme}.svg").write_text(build_desktop(theme), encoding="utf-8")
        (OUT_DIR / f"hero-mobile-{theme}.svg").write_text(build_mobile(theme), encoding="utf-8")
    print(f"Wrote 4 hero SVGs to {OUT_DIR}")


if __name__ == "__main__":
    main()
