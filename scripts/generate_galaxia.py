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
weeks_days = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in weeks]

# --- 2) Layout settings -----------------------------------------------------
CELL = 12
GAP = 3
PAD_L = 60
PAD_T = 75
PAD_R = 20
PAD_B = 30

weeks_count = len(weeks_days)
cols = weeks_count
rows = 7
width = PAD_L + cols * (CELL + GAP) - GAP + PAD_R
height = PAD_T + rows * (CELL + GAP) - GAP + PAD_B

# GitHub's actual contribution colors
palette_dark = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
palette_light = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

def level_for(count: int) -> int:
    if count <= 0: return 0
    if count < 4: return 1
    if count < 8: return 2
    if count < 13: return 3
    return 4

# --- 3) Build SVG -----------------------------------------------------------
rand = random.Random(42)

stars = []
for _ in range(40):
    x = rand.uniform(10, width - 10)
    y = rand.uniform(10, height - 10)
    r = rand.uniform(0.4, 1.2)
    dur = rand.uniform(2.0, 5.0)
    begin = rand.uniform(0, 3.0)
    lo = rand.uniform(0.1, 0.3)
    hi = rand.uniform(0.6, 1.0)
    stars.append(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" class="star">'
        f'<animate attributeName="opacity" values="{lo:.1f};{hi:.1f};{lo:.1f}" '
        f'dur="{dur:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite"/></circle>'
    )

header = "GALAXIA"
subtitle = f"commit activity · last {DAYS} days · {cal['totalContributions']} total"

months = []
for w_i, week in enumerate(weeks_days):
    for date_str, _ in week:
        d = dt.date.fromisoformat(date_str)
        if d.day == 1:
            x = PAD_L + w_i * (CELL + GAP)
            months.append((x, d.strftime("%b")))
        break

cells = []
for w_i, week in enumerate(weeks_days):
    for d_i, (date_str, count) in enumerate(week):
        x = PAD_L + w_i * (CELL + GAP)
        y = PAD_T + d_i * (CELL + GAP)
        lvl = level_for(count)
        href = f"https://github.com/{LOGIN}?tab=overview&from={date_str}"
        title = f"{date_str} · {count} commit{'s' if count!=1 else ''}"
        rect = (
            f'<a xlink:href="{href}" target="_blank" aria-label="{title}">'
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" '
            f'class="c c{lvl}" data-count="{count}"><title>{title}</title></rect></a>'
        )
        cells.append(rect)

legend = []
for i in range(5):
    lx = PAD_L + i * (CELL + GAP)
    ly = height - PAD_B + 6
    legend.append(f'<rect x="{lx}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" ry="2" class="c c{i}" />')
legend_labels = (
    f'<text x="{PAD_L - 10}" y="{height - PAD_B + CELL + 16}" text-anchor="end" class="label">Less</text>'
    f'<text x="{PAD_L + 5*(CELL+GAP) + 10}" y="{height - PAD_B + CELL + 16}" class="label">More</text>'
)

scanline = (
    f'<rect id="scan" x="{PAD_L}" y="{PAD_T - 8}" width="{cols * (CELL+GAP) - GAP}" height="4" class="scan" />'
)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">
  <title id="t">Galaxia — Aidan Tran commit activity</title>
  <desc id="d">Interactive SVG showing last {DAYS} days of GitHub contributions.</desc>
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="gradHeader" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1"/>
      <stop offset="50%" stop-color="#a78bfa"/>
      <stop offset="100%" stop-color="#6366f1"/>
    </linearGradient>
    <linearGradient id="scanGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0"/>
      <stop offset="50%" stop-color="#a78bfa" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    :root {{ --bg:#0d1117; --fg:#c9d1d9; --grid:#21262d; }}
    @media (prefers-color-scheme: light) {{ :root {{ --bg:#ffffff; --fg:#1f2328; --grid:#d1d9e0; }} }}
    .bg {{ fill: var(--bg); }}
    .fg {{ fill: var(--fg); }}
    .label {{ fill: var(--fg); font: 11px 'Segoe UI', system-ui, Helvetica, Arial, sans-serif; opacity: .7; }}
    .title {{ font: 700 24px 'Segoe UI', system-ui, Helvetica, Arial, sans-serif; fill: url(#gradHeader); filter:url(#glow); letter-spacing: 3px; }}
    .subtitle {{ font: 12px 'Segoe UI', system-ui, Helvetica, Arial, sans-serif; fill: var(--fg); opacity:.5; }}
    .grid {{ stroke: var(--grid); stroke-width:1; shape-rendering: crispEdges; }}
    .star {{ fill: var(--fg); }}
    .c {{ shape-rendering: geometricPrecision; }}
    .c.c0 {{ fill: {palette_dark[0]}; }}
    .c.c1 {{ fill: {palette_dark[1]}; }}
    .c.c2 {{ fill: {palette_dark[2]}; }}
    .c.c3 {{ fill: {palette_dark[3]}; }}
    .c.c4 {{ fill: {palette_dark[4]}; }}
    @media (prefers-color-scheme: light) {{
      .c.c0 {{ fill: {palette_light[0]}; }}
      .c.c1 {{ fill: {palette_light[1]}; }}
      .c.c2 {{ fill: {palette_light[2]}; }}
      .c.c3 {{ fill: {palette_light[3]}; }}
      .c.c4 {{ fill: {palette_light[4]}; }}
      .star {{ opacity: 0; }}
    }}
    .scan {{
      fill: url(#scanGrad);
      animation: sweep 8s ease-in-out infinite;
    }}
    @keyframes sweep {{
      0% {{ transform: translateY(0); opacity:0; }}
      10% {{ opacity:1; }}
      90% {{ opacity:1; }}
      100% {{ transform: translateY({rows * (CELL+GAP)}px); opacity:0; }}
    }}
  </style>

  <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="12"/>
  {''.join(stars)}

  <g transform="translate({PAD_L}, 30)">
    <text class="title">{header}</text>
    <text class="subtitle" y="20" x="2">{subtitle}</text>
  </g>

  <rect x="{PAD_L-4}" y="{PAD_T-6}" width="{cols*(CELL+GAP)-GAP+8}" height="{rows*(CELL+GAP)-GAP+12}" fill="none" class="grid" rx="6"/>

  <g class="labels">
    {''.join(f'<text class="label" x="{x}" y="{PAD_T-12}">{m}</text>' for x,m in months)}
    {''.join(f'<text class="label" x="{PAD_L-8}" y="{PAD_T + i*(CELL+GAP) + 9}" text-anchor="end">{d}</text>' for i,d in enumerate(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']))}
  </g>

  <g class="cells">
    {''.join(cells)}
  </g>

  {scanline}

  <g class="legend">
    {''.join(legend)}
    {legend_labels}
  </g>
</svg>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"Wrote {OUT} ({width}x{height}) for {LOGIN}. Total contributions: {cal['totalContributions']}")
