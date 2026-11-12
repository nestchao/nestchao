# Profile asset generators

The profile uses hand-built SVG assets so the visual system stays consistent
without depending on a third-party card service.

## Hero banners

```bash
python scripts/generate_hero.py
```

Writes four responsive banners to `assets/hero/`:

- `hero-desktop-dark.svg` / `hero-desktop-light.svg`
- `hero-mobile-dark.svg` / `hero-mobile-light.svg`

Edit the copy and colours in `THEMES` / `build_desktop()` / `build_mobile()`.
The fonts are embedded as base64 so the SVGs render identically on GitHub.

## GitHub signal cards

```bash
GITHUB_TOKEN="$(gh auth token)" python scripts/generate_stats.py
```

Writes four cards to `assets/stats/`:

- `stats-desktop-dark.svg` / `stats-desktop-light.svg`
- `stats-mobile-dark.svg` / `stats-mobile-light.svg`

The script uses the GitHub GraphQL API (standard library only) and pulls:

- contributions, commits, stars earned, public repositories
- the last 12 months of contribution activity
- language bytes across non-fork public repositories
- current / longest streak, best day, active days, followers

In GitHub Actions the workflow supplies `METRICS_TOKEN` (falling back to
`GITHUB_TOKEN`) and commits the refreshed cards once a day.
