#!/usr/bin/env python3
import os, sys, json, datetime as dt, random, textwrap
import requests

LOGIN = os.getenv("GITHUB_LOGIN", "AidanHT")
TOKEN = os.getenv("GITHUB_TOKEN")
OUT = "docs/assets/galaxia.svg"
DAYS = 365

if not TOKEN:
    print("Missing GITHUB_TOKEN in env", file=sys.stderr)
    sys.exit(1)

# --- 1) Fetch contributions via GraphQL ------------------------------------
url = "https://api.github.com/graphql"
headers = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}

utc = dt.timezone.utc
today = dt.datetime.now(tz=utc).date()
# Use full DateTime range to satisfy GraphQL DateTime type
start_date = today - dt.timedelta(days=DAYS)
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
# Flatten into [[(date, count), ...] per week]
weeks_days = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in weeks]

# --- 2) Layout settings -----------------------------------------------------
CELL = 12          # px cell size
GAP = 3            # px gap
PAD_L = 60         # left padding for y-axis labels
PAD_T = 75         # top padding for header
PAD_R = 20
PAD_B = 30

weeks_count = len(weeks_days)
cols = weeks_count
rows = 7  # contributions calendar is always 7 rows
width = PAD_L + cols * (CELL + GAP) - GAP + PAD_R
height = PAD_T + rows * (CELL + GAP) - GAP + PAD_B

# Retro palette (dark default)
palette_dark = [
    "#0a0d1a",  # 0 (bg-ish)
    "#143357",
    "#1e6eb6",
    "#7f40ff",
    "#ff4bd8",  # max
]
# Light palette
palette_light = [
    "#f6f8fa",
    "#b8d1ff",
    "#78a6ff",
    "#6c47ff",
    "#ff67dc",
]

# Buckets for intensity → 5 levels
levels = [0, 1, 4, 8, 13]  # thresholds (≥)

def level_for(count: int) -> int:
    if count <= 0: return 0
    if count < 1: return 0
    if count < 4: return 1
    if count < 8: return 2
    if count < 13: return 3
    return 4

# --- 3) Build SVG -----------------------------------------------------------
rand = random.Random(42)

stars = []
for _ in range(120):
    x = PAD_L + rand.uniform(0, cols * (CELL + GAP))
    y = rand.uniform(0, height)
    r = rand.uniform(0.4, 1.3)
    o = rand.uniform(0.15, 0.8)
    stars.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" class="star" style="opacity:{o:.2f}"/>')

# Header text (neon glow)
header = f"GALAXIA"
subtitle = f"commit arcade — last {DAYS} days · total {cal['totalContributions']}"

# Month labels (approx — label the first Monday of each month in the range)
months = []
for w_i, week in enumerate(weeks_days):
    # pick first non-empty date in week
    for date_str, _ in week:
        d = dt.date.fromisoformat(date_str)
        if d.day == 1:
            x = PAD_L + w_i * (CELL + GAP)
            months.append((x, d.strftime("%b")))
        break

# Build cells
cells = []
for w_i, week in enumerate(weeks_days):
    for d_i, (date_str, count) in enumerate(week):
        x = PAD_L + w_i * (CELL + GAP)
        y = PAD_T + d_i * (CELL + GAP)
        lvl = level_for(count)
        # Link to your overview anchored by that date (month view)
        href = f"https://github.com/{LOGIN}?tab=overview&from={date_str}"
        title = f"{date_str} • {count} commit{'s' if count!=1 else ''}"
        rect = (
            f'<a xlink:href="{href}" target="_blank" aria-label="{title}">' 
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
            f'class="c c{lvl}" data-count="{count}"><title>{title}</title></rect></a>'
        )
        cells.append(rect)

# Legend samples
legend = []
for i in range(5):
    lx = PAD_L + i * (CELL + GAP)
    ly = height - PAD_B + 6
    legend.append(f'<rect x="{lx}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" ry="2" class="c c{i}" />')
legend_labels = (
    f'<text x="{PAD_L - 10}" y="{height - PAD_B + CELL + 16}" text-anchor="end" class="label">Less</text>'
    f'<text x="{PAD_L + 5*(CELL+GAP) + 10}" y="{height - PAD_B + CELL + 16}" class="label">More</text>'
)

# Scanline (CSS animated gradient bar)
scanline = (
    f'<rect id="scan" x="{PAD_L}" y="{PAD_T - 8}" width="{cols * (CELL+GAP) - GAP}" height="6" class="scan" />'
)

svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">
  <title id="t">Galaxia — Aidan Tran commit arcade</title>
  <desc id="d">Interactive SVG showing last {DAYS} days of GitHub contributions with retro styling.</desc>
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <linearGradient id="gradHeader" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#7f40ff"/>
      <stop offset="50%" stop-color="#ff4bd8"/>
      <stop offset="100%" stop-color="#1e6eb6"/>
    </linearGradient>
  </defs>
  <style>
    :root {{ --bg:#0a0d1a; --fg:#c9d1d9; --grid:#101626; }}
    @media (prefers-color-scheme: light) {{ :root {{ --bg:#ffffff; --fg:#0b1521; --grid:#e6eaf1; }} }}
    .bg {{ fill: var(--bg); }}
    .fg {{ fill: var(--fg); }}
    .label {{ fill: var(--fg); font: 11px Verdana, DejaVu Sans, Arial, sans-serif; opacity: .85; }}
    .title {{ font: 700 28px Verdana, DejaVu Sans, Arial, sans-serif; fill: url(#gradHeader); filter:url(#glow); letter-spacing: 2px; }}
    .subtitle {{ font: 12px Verdana, DejaVu Sans, Arial, sans-serif; fill: var(--fg); opacity:.8; }}
    .grid {{ stroke: var(--grid); stroke-width:1; shape-rendering: crispEdges; }}
    .star {{ fill:#fff; }}
    .c {{ shape-rendering: geometricPrecision; }}
    /* Dark palette */
    .c.c0 {{ fill: {palette_dark[0]}; }}
    .c.c1 {{ fill: {palette_dark[1]}; }}
    .c.c2 {{ fill: {palette_dark[2]}; }}
    .c.c3 {{ fill: {palette_dark[3]}; }}
    .c.c4 {{ fill: {palette_dark[4]}; }}
    /* Light palette override */
    @media (prefers-color-scheme: light) {{
      .c.c0 {{ fill: {palette_light[0]}; }}
      .c.c1 {{ fill: {palette_light[1]}; }}
      .c.c2 {{ fill: {palette_light[2]}; }}
      .c.c3 {{ fill: {palette_light[3]}; }}
      .c.c4 {{ fill: {palette_light[4]}; }}
    }}
    .scan {{
      fill: none;
      stroke: #7f40ff; stroke-opacity:.7; stroke-width:2;
      stroke-dasharray: 6 6;
      animation: sweep 6.5s linear infinite;
    }}
    @keyframes sweep {{
      0% {{ transform: translateX(-{cols * (CELL+GAP)}px); opacity:0; }}
      10% {{ opacity:1; }}
      90% {{ opacity:1; }}
      100% {{ transform: translateX(0); opacity:0; }}
    }}
  </style>

  <!-- Background -->
  <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="16"/>
  {''.join(stars)}

  <!-- Header -->
  <g transform="translate({PAD_L}, 30)">
    <text class="title">{header}</text>
    <text class="subtitle" y="22" x="2">{subtitle}</text>
  </g>

  <!-- Vertical guide behind grid -->
  <rect x="{PAD_L-6}" y="{PAD_T-10}" width="{cols*(CELL+GAP)-GAP+12}" height="{rows*(CELL+GAP)-GAP+20}" fill="none" class="grid" rx="10"/>

  <!-- Month labels -->
  <g class="labels">
    {''.join(f'<text class="label" x="{x}" y="{PAD_T-14}">{m}</text>' for x,m in months)}
    {''.join(f'<text class="label" x="{PAD_L-8}" y="{PAD_T + i*(CELL+GAP) + 9}" text-anchor="end">{d}</text>' for i,d in enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']))}
  </g>

  <!-- Grid cells -->
  <g class="cells">
    {''.join(cells)}
  </g>

  <!-- Scanline embellishment -->
  {scanline}

  <!-- Legend -->
  <g class="legend">
    {''.join(legend)}
    {legend_labels}
  </g>
</svg>
"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Wrote {OUT} ({width}×{height}) for {LOGIN}. Total contributions: {cal['totalContributions']}")

