#!/usr/bin/env python3
"""Generate the theme-aware GitHub signal cards used in the profile README.

Data comes from the GitHub GraphQL API. The script only needs the standard
library; it renders four SVGs (desktop/mobile x dark/light) into assets/stats.

Usage:
    GITHUB_TOKEN=... python scripts/generate_stats.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from generate_hero import FONT_CSS, esc

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "stats"
LOGIN = "nestchao"
API = "https://api.github.com/graphql"

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    followers { totalCount }
    following { totalCount }
    repoCount: repositories(privacy: PUBLIC, ownerAffiliations: OWNER) { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""

REPOS_QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    repos: repositories(
      first: 100
      after: $after
      privacy: PUBLIC
      ownerAffiliations: OWNER
      isFork: false
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

THEMES = {
    "dark": {
        "bg": "#0A0F16",
        "bg2": "#0C121B",
        "text": "#F4F1E8",
        "muted": "#9AA4B2",
        "dim": "#606B7A",
        "accent": "#F2B84B",
        "accent2": "#63E6C4",
        "accent3": "#7AA2F7",
        "accent4": "#F78C6C",
        "line": "#FFFFFF",
        "line_opacity": "0.10",
        "grid_opacity": "0.035",
        "empty_opacity": "0.06",
        "border_opacity": "0.10",
        "glow": "0.12",
        "langs": ["#F2B84B", "#63E6C4", "#7AA2F7", "#F78C6C", "#C4A7E7", "#6B7280"],
    },
    "light": {
        "bg": "#F8F4EC",
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
        "grid_opacity": "0.045",
        "empty_opacity": "0.07",
        "border_opacity": "0.12",
        "glow": "0.10",
        "langs": ["#B8740F", "#0E8C78", "#2F5FD0", "#C2410C", "#7C3AED", "#6B7280"],
    },
}

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


@dataclass
class Day:
    day: date
    count: int


@dataclass
class Language:
    name: str
    size: int
    percent: float
    color: str


@dataclass
class Stats:
    login: str
    contributions: int
    commits: int
    issues: int
    pull_requests: int
    reviews: int
    restricted: int
    followers: int
    following: int
    repos: int
    stars: int
    days: list[Day]
    languages: list[Language]
    current_streak: int
    longest_streak: int
    best_day: int
    best_day_date: date | None
    active_days: int
    synced: str


def graphql(query: str, variables: dict[str, object]) -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN (or GH_TOKEN) is required to fetch GitHub data.")
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "nestchao-profile-stats",
            "Accept": "application/vnd.github+json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API returned HTTP {error.code}: {detail}") from error
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
    return payload["data"]


def compute_streaks(days: list[Day]) -> tuple[int, int]:
    longest = 0
    run = 0
    for day in days:
        if day.count > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    index = len(days) - 1
    if index >= 0 and days[index].count == 0:
        index -= 1
    current = 0
    while index >= 0 and days[index].count > 0:
        current += 1
        index -= 1
    return current, longest


def fetch_stats() -> Stats:
    profile = graphql(PROFILE_QUERY, {"login": LOGIN})["user"]
    collection = profile["contributionsCollection"]
    calendar = collection["contributionCalendar"]

    days: list[Day] = []
    for week in calendar["weeks"]:
        for item in week["contributionDays"]:
            days.append(Day(date.fromisoformat(item["date"]), int(item["contributionCount"])))
    days.sort(key=lambda item: item.day)

    repos: list[dict] = []
    after: str | None = None
    while True:
        data = graphql(REPOS_QUERY, {"login": LOGIN, "after": after})["user"]["repos"]
        repos.extend(data["nodes"])
        page_info = data["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    sizes: dict[str, int] = {}
    stars = 0
    for repo in repos:
        stars += int(repo["stargazerCount"])
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + int(edge["size"])

    total_size = sum(sizes.values()) or 1
    ranked = sorted(sizes.items(), key=lambda item: item[1], reverse=True)
    palette = THEMES["dark"]["langs"]
    languages: list[Language] = []
    for index, (name, size) in enumerate(ranked[:5]):
        languages.append(Language(name, size, size / total_size * 100, palette[index]))
    other_size = sum(size for _, size in ranked[5:])
    if other_size:
        languages.append(Language("Other", other_size, other_size / total_size * 100, palette[5]))

    current, longest = compute_streaks(days)
    best = max(days, key=lambda item: item.count, default=None)
    active = sum(1 for item in days if item.count > 0)
    synced = datetime.now(timezone.utc).strftime("%d %b %Y").upper()

    return Stats(
        login=profile["login"],
        contributions=int(calendar["totalContributions"]),
        commits=int(collection["totalCommitContributions"]),
        issues=int(collection["totalIssueContributions"]),
        pull_requests=int(collection["totalPullRequestContributions"]),
        reviews=int(collection["totalPullRequestReviewContributions"]),
        restricted=int(collection["restrictedContributionsCount"]),
        followers=int(profile["followers"]["totalCount"]),
        following=int(profile["following"]["totalCount"]),
        repos=int(profile["repoCount"]["totalCount"]),
        stars=stars,
        days=days,
        languages=languages,
        current_streak=current,
        longest_streak=longest,
        best_day=best.count if best else 0,
        best_day_date=best.day if best else None,
        active_days=active,
        synced=synced,
    )


def fmt(value: int) -> str:
    return f"{value:,}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def text(
    x: float,
    y: float,
    value: str,
    size: float,
    fill: str,
    *,
    family: str = "mono",
    weight: int = 400,
    anchor: str = "start",
    spacing: float | None = None,
    opacity: float | None = None,
) -> str:
    cls = "sans" if family == "sans" else "mono"
    attrs = [
        f'x="{x:.2f}"',
        f'y="{y:.2f}"',
        f'class="{cls}"',
        f'font-size="{size}"',
        f'font-weight="{weight}"',
        f'fill="{fill}"',
    ]
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity}"')
    return f"<text {' '.join(attrs)}>{esc(value)}</text>"


def defs(theme: dict[str, str], width: int, height: int) -> str:
    return f"""
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{width}" y2="{height}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{theme['bg']}"/>
      <stop offset="1" stop-color="{theme['bg2']}"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="{theme['accent']}" stop-opacity="{theme['glow']}"/>
      <stop offset="1" stop-color="{theme['accent']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow2" cx="50%" cy="50%" r="50%">
      <stop offset="0" stop-color="{theme['accent2']}" stop-opacity=".09"/>
      <stop offset="1" stop-color="{theme['accent2']}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M32 0H0V32" fill="none" stroke="{theme['line']}" stroke-opacity="{theme['grid_opacity']}" stroke-width="1"/>
    </pattern>
    <radialGradient id="grid-fade" cx="50%" cy="50%" r="70%">
      <stop offset="0" stop-color="#FFFFFF"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
    <mask id="grid-mask"><rect width="{width}" height="{height}" fill="url(#grid-fade)"/></mask>
    <clipPath id="card"><rect width="{width}" height="{height}" rx="24"/></clipPath>
  </defs>
"""


def heatmap(
    stats: Stats,
    theme: dict[str, str],
    x: float,
    y: float,
    cell: float,
    gap: float,
    max_width: float,
    label_size: float,
) -> tuple[str, float, float]:
    step = cell + gap
    weeks = len(stats.days) // 7 + (1 if len(stats.days) % 7 else 0)
    # Use only the visible number of columns that fit the panel.
    columns = min(weeks, int((max_width + gap) // step))
    start_index = max(0, len(stats.days) - columns * 7)
    visible = stats.days[start_index:]

    out: list[str] = []
    for index, day in enumerate(visible):
        col = index // 7
        row = index % 7
        if day.count == 0:
            fill = theme["line"]
            opacity = theme["empty_opacity"]
        else:
            fill = theme["accent"]
            if day.count <= 2:
                opacity = "0.24"
            elif day.count <= 5:
                opacity = "0.42"
            elif day.count <= 10:
                opacity = "0.65"
            elif day.count <= 20:
                opacity = "0.85"
            else:
                opacity = "1"
        out.append(
            f'<rect x="{x + col * step:.2f}" y="{y + row * step:.2f}" width="{cell}" height="{cell}" rx="{max(1.2, cell * 0.22):.2f}" fill="{fill}" fill-opacity="{opacity}"/>'
        )

    # Month labels at the first week of each month. Mobile uses every other
    # month so the labels stay legible at a small render size.
    labels: list[str] = []
    last_x = -100.0
    seen: set[tuple[int, int]] = set()
    month_filter = 1 if max_width >= 450 else 2
    for index in range(0, len(visible), 7):
        week = visible[index : index + 7]
        if not week:
            continue
        month = (week[0].day.year, week[0].day.month)
        if month in seen or month[1] % month_filter != 1:
            continue
        seen.add(month)
        lx = x + (index // 7) * step
        if lx - last_x < label_size * 3.4:
            continue
        labels.append(
            text(
                lx,
                y - 8,
                MONTHS[week[0].day.month - 1],
                label_size,
                theme["dim"],
                spacing=0.7,
            )
        )
        last_x = lx

    width = min(columns, weeks) * step - gap
    height = 7 * step - gap
    return "\n".join(out + labels), width, height


def language_legend(
    stats: Stats,
    theme: dict[str, str],
    x: float,
    y: float,
    width: float,
    columns: int,
    row_gap: float,
    size: float,
) -> str:
    items = stats.languages
    column_width = width / columns
    out: list[str] = []
    for index, language in enumerate(items):
        col = index % columns
        row = index // columns
        ix = x + col * column_width
        iy = y + row * row_gap
        color = theme["langs"][index] if index < len(theme["langs"]) else theme["langs"][-1]
        out.append(f'<circle cx="{ix + 3:.2f}" cy="{iy - 3.5:.2f}" r="3" fill="{color}"/>')
        out.append(text(ix + 12, iy, language.name, size, theme["muted"], spacing=0.1))
        out.append(
            text(
                ix + column_width - 10,
                iy,
                pct(language.percent),
                size,
                theme["text"],
                anchor="end",
                spacing=0.1,
            )
        )
    return "\n".join(out)


def language_bar(
    stats: Stats,
    theme: dict[str, str],
    x: float,
    y: float,
    width: float,
    height: float,
) -> str:
    total = sum(item.size for item in stats.languages) or 1
    out = [
        f'<clipPath id="lang-bar-clip"><rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{height / 2}"/></clipPath>',
        '<g clip-path="url(#lang-bar-clip)">',
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{theme["line"]}" fill-opacity="{theme["empty_opacity"]}"/>',
    ]
    cursor = x
    for index, language in enumerate(stats.languages):
        segment = width * language.size / total
        color = theme["langs"][index] if index < len(theme["langs"]) else theme["langs"][-1]
        out.append(
            f'<rect x="{cursor:.2f}" y="{y}" width="{max(0, segment):.2f}" height="{height}" fill="{color}"/>'
        )
        cursor += segment
    out.append('</g>')
    return "\n".join(out)


def header(theme: dict[str, str], stats: Stats, width: float, right: str, mobile: bool = False) -> str:
    x = 32 if mobile else 48
    y = 46 if mobile else 52
    out = [
        f'<circle cx="{x + 4}" cy="{y - 4}" r="3.4" fill="{theme["accent2"]}" class="pulse"/>',
        f'<circle cx="{x + 4}" cy="{y - 4}" r="7" fill="none" stroke="{theme["accent2"]}" stroke-opacity=".20"/>',
        text(x + 18, y, "GITHUB / SIGNAL", 12 if mobile else 11, theme["accent2"], spacing=2.0),
        text(width - x, y, right, 9.5 if mobile else 9.5, theme["dim"], anchor="end", spacing=0.8),
    ]
    return "\n".join(out)


def build_desktop(stats: Stats, theme_name: str) -> str:
    t = THEMES[theme_name]
    W, H = 960, 340
    x_left = 48
    x_right = 400
    panel_width = W - x_right - 48

    heat, heat_w, heat_h = heatmap(stats, t, x_right, 116, 7.0, 2.0, panel_width, 8.0)
    legend = language_legend(stats, t, x_right, 244, panel_width, 3, 22, 9.5)
    bar = language_bar(stats, t, x_right, 214, panel_width, 10)

    stat_tiles = []
    values = [
        (fmt(stats.contributions), "CONTRIBUTIONS", t["accent"]),
        (fmt(stats.commits), "COMMITS", t["accent2"]),
        (fmt(stats.stars), "STARS EARNED", t["accent3"] if "accent3" in t else t["accent"]),
        (fmt(stats.repos), "PUBLIC REPOS", t["accent4"] if "accent4" in t else t["accent2"]),
    ]
    positions = [(48, 130), (238, 130), (48, 236), (238, 236)]
    for index, ((value, label, color), (x, y)) in enumerate(zip(values, positions)):
        stat_tiles.append(
            f'<rect x="{x}" y="{y - 30}" width="14" height="2" rx="1" fill="{color}" opacity=".9"/>'
        )
        stat_tiles.append(text(x, y, value, 40, t["text"], family="sans", weight=300, spacing=-0.5))
        stat_tiles.append(text(x, y + 24, label, 9.5, t["muted"], spacing=1.45))

    desc = (
        f"A GitHub signal card for {stats.login}: {fmt(stats.contributions)} contributions, "
        f"{fmt(stats.commits)} commits, {fmt(stats.stars)} stars earned, {fmt(stats.repos)} public repositories, "
        f"a 12-month contribution heatmap, and the top languages by bytes."
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-labelledby="stats-title stats-desc">
  <title id="stats-title">GitHub signal for {stats.login}</title>
  <desc id="stats-desc">{esc(desc)}</desc>
  <style>{FONT_CSS}</style>
  {defs(t, W, H)}
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#grid-mask)"/>
    <circle cx="890" cy="10" r="220" fill="url(#glow)"/>
    <circle cx="60" cy="340" r="180" fill="url(#glow2)"/>
    {header(t, stats, W, f"LAST 12 MONTHS · SYNCED {stats.synced}")}
    <line x1="{x_left}" y1="74" x2="{W - x_left}" y2="74" stroke="{t['line']}" stroke-opacity=".08"/>
    <line x1="210" y1="96" x2="210" y2="272" stroke="{t['line']}" stroke-opacity=".06"/>
    {''.join(stat_tiles)}
    {text(x_right, 94, "CONTRIBUTION SIGNAL", 9.5, t['muted'], spacing=1.55)}
    {text(W - 48, 94, "12 MONTHS", 8.5, t['dim'], anchor="end", spacing=1.1)}
    {heat}
    {text(x_right, 204, "LANGUAGES / BY BYTES", 9.5, t['muted'], spacing=1.5)}
    {bar}
    {legend}
    <line x1="{x_left}" y1="296" x2="{W - x_left}" y2="296" stroke="{t['line']}" stroke-opacity=".08"/>
    {text(x_left, 318, f"CURRENT STREAK {stats.current_streak} DAY{'S' if stats.current_streak != 1 else ''} · LONGEST {stats.longest_streak} DAYS · BEST DAY {stats.best_day}", 9.0, t['dim'], spacing=.45)}
    {text(W - 48, 318, f"{stats.active_days} ACTIVE DAYS · {stats.followers} FOLLOWERS", 9.0, t['dim'], anchor="end", spacing=.45)}
  </g>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="23.5" stroke="{t['line']}" stroke-opacity="{t['border_opacity']}"/>
</svg>
"""
    return svg


def build_mobile(stats: Stats, theme_name: str) -> str:
    t = THEMES[theme_name]
    W, H = 480, 590
    x = 32
    panel_width = W - x * 2

    heat, heat_w, heat_h = heatmap(stats, t, x, 314, 5.5, 1.7, panel_width, 9.0)
    legend = language_legend(stats, t, x, 438, panel_width, 2, 24, 12.5)
    bar = language_bar(stats, t, x, 408, panel_width, 11)

    stat_tiles = []
    values = [
        (fmt(stats.contributions), "CONTRIBUTIONS", t["accent"]),
        (fmt(stats.commits), "COMMITS", t["accent2"]),
        (fmt(stats.stars), "STARS EARNED", t["accent"]),
        (fmt(stats.repos), "PUBLIC REPOS", t["accent2"]),
    ]
    positions = [(32, 118), (248, 118), (32, 220), (248, 220)]
    for index, ((value, label, color), (px, py)) in enumerate(zip(values, positions)):
        stat_tiles.append(
            f'<rect x="{px}" y="{py - 34}" width="14" height="2" rx="1" fill="{color}" opacity=".9"/>'
        )
        stat_tiles.append(text(px, py, value, 50, t["text"], family="sans", weight=300, spacing=-0.5))
        stat_tiles.append(text(px, py + 27, label, 16, t["muted"], spacing=0.85))

    desc = (
        f"A GitHub signal card for {stats.login}: {fmt(stats.contributions)} contributions, "
        f"{fmt(stats.commits)} commits, {fmt(stats.stars)} stars earned, {fmt(stats.repos)} public repositories, "
        f"a 12-month contribution heatmap, and the top languages by bytes."
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-labelledby="stats-title stats-desc">
  <title id="stats-title">GitHub signal for {stats.login}</title>
  <desc id="stats-desc">{esc(desc)}</desc>
  <style>{FONT_CSS}</style>
  {defs(t, W, H)}
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="url(#bg)"/>
    <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#grid-mask)"/>
    <circle cx="430" cy="20" r="160" fill="url(#glow)"/>
    <circle cx="30" cy="580" r="150" fill="url(#glow2)"/>
    {header(t, stats, W, f"SYNCED {stats.synced}", mobile=True)}
    <line x1="{x}" y1="64" x2="{W - x}" y2="64" stroke="{t['line']}" stroke-opacity=".08"/>
    {''.join(stat_tiles)}
    {text(x, 292, "CONTRIBUTION SIGNAL", 12, t['muted'], spacing=1.35)}
    {text(W - x, 292, "12 MONTHS", 10.0, t['dim'], anchor="end", spacing=0.9)}
    {heat}
    {text(x, 398, "LANGUAGES / BY BYTES", 12, t['muted'], spacing=1.3)}
    {bar}
    {legend}
    <line x1="{x}" y1="520" x2="{W - x}" y2="520" stroke="{t['line']}" stroke-opacity=".08"/>
    {text(x, 542, f"CURRENT STREAK {stats.current_streak} DAY{'S' if stats.current_streak != 1 else ''} · LONGEST {stats.longest_streak} DAYS", 12.5, t['dim'], spacing=.25)}
    {text(x, 562, f"BEST DAY {stats.best_day} · {stats.active_days} ACTIVE DAYS · {stats.followers} FOLLOWERS", 12.5, t['dim'], spacing=.25)}
  </g>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="23.5" stroke="{t['line']}" stroke-opacity="{t['border_opacity']}"/>
</svg>
"""
    return svg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = fetch_stats()
    for theme in THEMES:
        (OUT_DIR / f"stats-desktop-{theme}.svg").write_text(build_desktop(stats, theme), encoding="utf-8")
        (OUT_DIR / f"stats-mobile-{theme}.svg").write_text(build_mobile(stats, theme), encoding="utf-8")
    print(
        f"Wrote 4 SVG cards for {stats.login}: "
        f"{fmt(stats.contributions)} contributions, {fmt(stats.commits)} commits, "
        f"{fmt(stats.stars)} stars, {fmt(stats.repos)} repos."
    )


if __name__ == "__main__":
    main()
