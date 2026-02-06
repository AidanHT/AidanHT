#!/usr/bin/env python3
"""Generate Galaxia SVG — GitHub contribution visualization.

Fetches contribution data from GitHub's GraphQL API and renders an
animated SVG commit grid. Falls back to sample data when GITHUB_TOKEN
is not set (useful for local development and initial placeholder).
"""
import os, sys, json, datetime as dt, random, textwrap

LOGIN = os.getenv("GITHUB_LOGIN", "AidanHT")
TOKEN = os.getenv("GITHUB_TOKEN")
OUT = "docs/assets/galaxia.svg"
DAYS = 365

utc = dt.timezone.utc
today = dt.datetime.now(tz=utc).date()
start_date = today - dt.timedelta(days=DAYS)

if TOKEN:
    import requests

    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}

    start_dt = dt.datetime.combine(start_date, dt.time.min, tzinfo=utc)
    end_dt = dt.datetime.combine(today, dt.time.max.replace(microsecond=0), tzinfo=utc)

    query = textwrap.dedent(
        """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
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
    )

    def iso_z(d: dt.datetime) -> str:
        return d.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    variables = {
        "login": LOGIN,
        "from": iso_z(start_dt),
        "to": iso_z(end_dt),
    }

    resp = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    resp.raise_for_status()
    data = resp.json()

    try:
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except Exception:
        print(json.dumps(data, indent=2))
        raise

    weeks = cal["weeks"]
    weeks_days = [
        [(d["date"], d["contributionCount"]) for d in w["contributionDays"]]
        for w in weeks
    ]
    total_contributions = cal["totalContributions"]

else:
    # No token — generate with sample data for local development
    print("No GITHUB_TOKEN — generating with sample data", file=sys.stderr)
    rng = random.Random(42)
    weeks_days = []
    total_contributions = 0
    cursor = start_date
    # Align to start of week (Monday=0 in Python, GitHub starts Sunday=0)
    # Walk through weeks
    week = []
    while cursor <= today:
        dow = cursor.weekday()  # 0=Mon ... 6=Sun
        # Higher activity on weekdays
        if dow < 5:
            count = rng.choices([0, 1, 2, 3, 5, 8, 13], weights=[3, 4, 3, 2, 1, 1, 0.5], k=1)[0]
        else:
            count = rng.choices([0, 1, 2], weights=[5, 3, 1], k=1)[0]
        total_contributions += count
        week.append((cursor.isoformat(), count))
        # GitHub weeks run Sun-Sat; Python weekday 6=Sun
        if dow == 5:  # Saturday = end of GitHub week
            weeks_days.append(week)
            week = []
        cursor += dt.timedelta(days=1)
    if week:
        weeks_days.append(week)

# --- Layout -----------------------------------------------------------------
CELL = 12
GAP = 3
PAD_L = 60
PAD_T = 75
PAD_R = 20
PAD_B = 30

cols = len(weeks_days)
rows = 7
width = PAD_L + cols * (CELL + GAP) - GAP + PAD_R
height = PAD_T + rows * (CELL + GAP) - GAP + PAD_B

# GitHub's actual contribution colors
DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]


def level_for(count: int) -> int:
    if count <= 0:
        return 0
    if count < 4:
        return 1
    if count < 8:
        return 2
    if count < 13:
        return 3
    return 4


# --- Build SVG elements -----------------------------------------------------
rand = random.Random(42)

# Twinkling stars (dark mode only, hidden in light mode via CSS)
stars_svg = []
for _ in range(40):
    sx = rand.uniform(10, width - 10)
    sy = rand.uniform(10, height - 10)
    sr = rand.uniform(0.4, 1.2)
    dur = rand.uniform(2.0, 5.0)
    begin = rand.uniform(0, 3.0)
    lo = rand.uniform(0.1, 0.3)
    hi = rand.uniform(0.6, 1.0)
    stars_svg.append(
        f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sr:.1f}" fill="#8b949e">'
        f'<animate attributeName="opacity" values="{lo:.1f};{hi:.1f};{lo:.1f}" '
        f'dur="{dur:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite"/></circle>'
    )

subtitle = f"commit activity \u00b7 last {DAYS} days \u00b7 {total_contributions} total"

# Month labels
months = []
for w_i, week in enumerate(weeks_days):
    for date_str, _ in week:
        d = dt.date.fromisoformat(date_str)
        if d.day == 1:
            x = PAD_L + w_i * (CELL + GAP)
            months.append((x, d.strftime("%b")))
        break

# Grid cells — no <a> wrapper (links don't work in <img>), just rects + titles
cells_svg = []
for w_i, week in enumerate(weeks_days):
    for d_i, (date_str, count) in enumerate(week):
        x = PAD_L + w_i * (CELL + GAP)
        y = PAD_T + d_i * (CELL + GAP)
        lvl = level_for(count)
        tip = f"{date_str} \u00b7 {count} commit{'s' if count != 1 else ''}"
        cells_svg.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
            f'rx="2" ry="2" class="c{lvl}"><title>{tip}</title></rect>'
        )

# Legend
legend_svg = []
for i in range(5):
    lx = PAD_L + i * (CELL + GAP)
    ly = height - PAD_B + 6
    legend_svg.append(
        f'<rect x="{lx}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" ry="2" class="c{i}"/>'
    )

# Day-of-week labels
day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Scanline vertical position range for SMIL animation
scan_y_start = PAD_T - 6
scan_y_end = PAD_T + rows * (CELL + GAP)

# --- Assemble SVG (no CSS variables — direct class styling) -----------------
svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     role="img" aria-labelledby="galaxia-title galaxia-desc">
  <title id="galaxia-title">Galaxia — {LOGIN} commit activity</title>
  <desc id="galaxia-desc">SVG showing last {DAYS} days of GitHub contributions.</desc>
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1"/>
      <stop offset="50%" stop-color="#a78bfa"/>
      <stop offset="100%" stop-color="#6366f1"/>
    </linearGradient>
    <linearGradient id="scanG" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0"/>
      <stop offset="50%" stop-color="#a78bfa" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    .bg {{ fill: #0d1117; }}
    .hdr {{ font: 700 24px 'Segoe UI', system-ui, Helvetica, Arial, sans-serif;
            letter-spacing: 3px; }}
    .sub {{ font: 12px 'Segoe UI', system-ui, Helvetica, Arial, sans-serif;
            fill: #8b949e; }}
    .lbl {{ fill: #8b949e; font: 11px 'Segoe UI', system-ui, Helvetica, Arial, sans-serif; }}
    .bdr {{ stroke: #21262d; stroke-width: 1; fill: none; shape-rendering: crispEdges; }}
    .c0 {{ fill: {DARK[0]}; }} .c1 {{ fill: {DARK[1]}; }} .c2 {{ fill: {DARK[2]}; }}
    .c3 {{ fill: {DARK[3]}; }} .c4 {{ fill: {DARK[4]}; }}
    @media (prefers-color-scheme: light) {{
      .bg  {{ fill: #ffffff; }}
      .sub {{ fill: #656d76; }}
      .lbl {{ fill: #656d76; }}
      .bdr {{ stroke: #d1d9e0; }}
      .star {{ display: none; }}
      .c0 {{ fill: {LIGHT[0]}; }} .c1 {{ fill: {LIGHT[1]}; }} .c2 {{ fill: {LIGHT[2]}; }}
      .c3 {{ fill: {LIGHT[3]}; }} .c4 {{ fill: {LIGHT[4]}; }}
    }}
  </style>

  <!-- Background -->
  <rect class="bg" width="{width}" height="{height}" rx="12"/>

  <!-- Stars (dark mode) -->
  <g class="star">
    {''.join(stars_svg)}
  </g>

  <!-- Header -->
  <text x="{PAD_L}" y="30" class="hdr" fill="url(#hdr)" filter="url(#glow)">GALAXIA</text>
  <text x="{PAD_L + 2}" y="50" class="sub">{subtitle}</text>

  <!-- Grid border -->
  <rect x="{PAD_L - 4}" y="{PAD_T - 6}"
        width="{cols * (CELL + GAP) - GAP + 8}" height="{rows * (CELL + GAP) - GAP + 12}"
        class="bdr" rx="6"/>

  <!-- Month labels -->
  <g class="lbl">
    {''.join(f'<text x="{x}" y="{PAD_T - 12}">{m}</text>' for x, m in months)}
  </g>

  <!-- Day-of-week labels -->
  <g class="lbl">
    {''.join(f'<text x="{PAD_L - 8}" y="{PAD_T + i * (CELL + GAP) + 9}" text-anchor="end">{d}</text>' for i, d in enumerate(day_labels))}
  </g>

  <!-- Contribution cells -->
  <g>
    {''.join(cells_svg)}
  </g>

  <!-- Scanline (SMIL animation — no CSS transform needed) -->
  <rect x="{PAD_L}" y="{scan_y_start}" width="{cols * (CELL + GAP) - GAP}" height="3"
        fill="url(#scanG)" opacity="0">
    <animate attributeName="y" values="{scan_y_start};{scan_y_end}" dur="8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;0.8;0.8;0" keyTimes="0;0.1;0.9;1" dur="8s" repeatCount="indefinite"/>
  </rect>

  <!-- Legend -->
  <g>
    {''.join(legend_svg)}
    <text x="{PAD_L - 10}" y="{height - PAD_B + CELL + 16}" text-anchor="end" class="lbl">Less</text>
    <text x="{PAD_L + 5 * (CELL + GAP) + 10}" y="{height - PAD_B + CELL + 16}" class="lbl">More</text>
  </g>
</svg>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Wrote {OUT} ({width}x{height}) for {LOGIN}. Total: {total_contributions}")
