#!/usr/bin/env python3
"""Generate Galaxia SVG — arcade-style GitHub contribution visualization.

Fetches contribution data from GitHub's GraphQL API and renders an animated
retro space-shooter SVG. Falls back to sample data when no token is available.
"""
import os, sys, json, datetime as dt, random, textwrap, math, subprocess

LOGIN = os.getenv("GITHUB_LOGIN", "AidanHT")
TOKEN = os.getenv("GITHUB_TOKEN")
OUT = "docs/assets/galaxia.svg"
DAYS = 365

# Layout
CELL, GAP = 12, 3
PAD_L, PAD_T, PAD_R, PAD_B = 60, 78, 20, 120

# Animation timing
CYCLE = 14          # full animation cycle (seconds)
BALL_DUR = 0.7      # projectile travel time
NUM_TARGETS = 10    # cells to shoot

# Colors — GitHub's real contribution palette
DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]

utc = dt.timezone.utc
today = dt.datetime.now(tz=utc).date()
start_date = today - dt.timedelta(days=DAYS)

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def iso_z(d):
    return d.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_token():
    """Fetch via GITHUB_TOKEN env var."""
    import requests
    start_dt = dt.datetime.combine(start_date, dt.time.min, tzinfo=utc)
    end_dt = dt.datetime.combine(today, dt.time.max.replace(microsecond=0), tzinfo=utc)
    query = textwrap.dedent("""
        query($login:String!,$from:DateTime!,$to:DateTime!){
          user(login:$login){contributionsCollection(from:$from,to:$to){
            contributionCalendar{totalContributions weeks{
              contributionDays{date contributionCount}}}}}
        }""")
    resp = requests.post("https://api.github.com/graphql",
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
        json={"query": query, "variables": {"login": LOGIN, "from": iso_z(start_dt), "to": iso_z(end_dt)}})
    resp.raise_for_status()
    data = resp.json()
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    return (
        [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in weeks],
        cal["totalContributions"],
    )

def fetch_gh_cli():
    """Try gh CLI (local auth)."""
    start_dt = dt.datetime.combine(start_date, dt.time.min, tzinfo=utc)
    end_dt = dt.datetime.combine(today, dt.time.max.replace(microsecond=0), tzinfo=utc)
    query = (
        'query($login:String!,$from:DateTime!,$to:DateTime!){'
        'user(login:$login){contributionsCollection(from:$from,to:$to){'
        'contributionCalendar{totalContributions weeks{'
        'contributionDays{date contributionCount}}}}}}'
    )
    try:
        r = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}",
             "-f", f"login={LOGIN}", "-f", f"from={iso_z(start_dt)}", "-f", f"to={iso_z(end_dt)}"],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            data = json.loads(r.stdout)
            cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            return (
                [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]],
                cal["totalContributions"],
            )
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None

def generate_dummy():
    """Sample data for local dev."""
    rng = random.Random(42)
    weeks_days, total = [], 0
    cursor, week = start_date, []
    while cursor <= today:
        dow = cursor.weekday()
        count = rng.choices([0,1,2,3,5,8,13], weights=[3,4,3,2,1,1,0.5], k=1)[0] if dow < 5 \
            else rng.choices([0,1,2], weights=[5,3,1], k=1)[0]
        total += count
        week.append((cursor.isoformat(), count))
        if dow == 5:
            weeks_days.append(week); week = []
        cursor += dt.timedelta(days=1)
    if week:
        weeks_days.append(week)
    return weeks_days, total

# Try data sources in order
weeks_days = total = None
if TOKEN:
    weeks_days, total = fetch_token()
    print(f"Fetched real data via API token. Total: {total}")
else:
    result = fetch_gh_cli()
    if result:
        weeks_days, total = result
        print(f"Fetched real data via gh CLI. Total: {total}")
    else:
        weeks_days, total = generate_dummy()
        print("No token or gh CLI — using sample data.", file=sys.stderr)

# ---------------------------------------------------------------------------
# Layout computations
# ---------------------------------------------------------------------------

cols, rows = len(weeks_days), 7
grid_w = cols * (CELL + GAP) - GAP
grid_h = rows * (CELL + GAP) - GAP
width = PAD_L + grid_w + PAD_R
height = PAD_T + grid_h + PAD_B

grid_bottom = PAD_T + grid_h
ship_base_y = grid_bottom + 48
ship_xl = PAD_L + 15
ship_xr = PAD_L + grid_w - 45
ship_xm = (ship_xl + ship_xr) / 2
ship_amp = 10


def level_for(c):
    return 0 if c <= 0 else 1 if c < 4 else 2 if c < 8 else 3 if c < 13 else 4


def ship_pos(t):
    """Approximate ship position at time t in the cycle."""
    t %= CYCLE
    pts = [(ship_xl, ship_base_y), (ship_xm, ship_base_y - ship_amp),
           (ship_xr, ship_base_y), (ship_xm, ship_base_y + ship_amp),
           (ship_xl, ship_base_y)]
    seg_dur = CYCLE / 4
    seg = min(int(t / seg_dur), 3)
    f = (t - seg * seg_dur) / seg_dur
    return (pts[seg][0] + (pts[seg+1][0] - pts[seg][0]) * f,
            pts[seg][1] + (pts[seg+1][1] - pts[seg][1]) * f)


# ---------------------------------------------------------------------------
# Target selection (cells for projectiles to hit)
# ---------------------------------------------------------------------------

rand = random.Random(42)
all_nonzero = sorted(
    [(w_i, d_i, count, PAD_L + w_i*(CELL+GAP), PAD_T + d_i*(CELL+GAP))
     for w_i, week in enumerate(weeks_days)
     for d_i, (_, count) in enumerate(week) if count > 0],
    key=lambda c: c[0])

targets = []
if all_nonzero:
    band = max(1, len(all_nonzero) // NUM_TARGETS)
    for i in range(NUM_TARGETS):
        b = all_nonzero[i*band:(i+1)*band]
        if b:
            b.sort(key=lambda c: c[2], reverse=True)
            targets.append(b[0])

target_set = {(t[0], t[1]) for t in targets}
fire_times = [CYCLE * (i + 0.5) / max(len(targets), 1) for i in range(len(targets))]

# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------

# -- Stars --
stars = []
for _ in range(40):
    sx, sy = rand.uniform(10, width-10), rand.uniform(10, height-10)
    sr = rand.uniform(0.4, 1.2)
    dur, begin = rand.uniform(2.0, 5.0), rand.uniform(0, 3.0)
    lo, hi = rand.uniform(0.1, 0.3), rand.uniform(0.6, 1.0)
    stars.append(
        f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{sr:.1f}" fill="#8b949e">'
        f'<animate attributeName="opacity" values="{lo:.1f};{hi:.1f};{lo:.1f}" '
        f'dur="{dur:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite"/></circle>')

# -- Month labels --
months = []
for w_i, week in enumerate(weeks_days):
    for ds, _ in week:
        d = dt.date.fromisoformat(ds)
        if d.day == 1:
            months.append((PAD_L + w_i*(CELL+GAP), d.strftime("%b")))
        break

# -- Grid cells (with fade animation on target cells) --
cells = []
for w_i, week in enumerate(weeks_days):
    for d_i, (ds, count) in enumerate(week):
        x, y = PAD_L + w_i*(CELL+GAP), PAD_T + d_i*(CELL+GAP)
        lvl = level_for(count)
        tip = f"{ds} \u00b7 {count} commit{'s' if count != 1 else ''}"
        # Check if target
        tgt_i = None
        for ti, t in enumerate(targets):
            if t[0] == w_i and t[1] == d_i:
                tgt_i = ti; break
        if tgt_i is not None:
            ft = fire_times[tgt_i]
            be = BALL_DUR / CYCLE  # ball end fraction
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" class="c{lvl}">'
                f'<title>{tip}</title>'
                f'<animate attributeName="opacity" values="1;1;0.15;0.15;1" '
                f'keyTimes="0;{be:.4f};{be+0.003:.4f};0.7;1" '
                f'dur="{CYCLE}s" begin="{ft:.1f}s" repeatCount="indefinite"/></rect>')
        else:
            cells.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" class="c{lvl}">'
                f'<title>{tip}</title></rect>')

# -- Legend --
legend = []
for i in range(5):
    lx = PAD_L + i*(CELL+GAP)
    ly = height - 22
    legend.append(f'<rect x="{lx}" y="{ly}" width="{CELL}" height="{CELL}" rx="2" ry="2" class="c{i}"/>')

# -- Projectiles + explosions --
balls = []
explosions = []
be_frac = BALL_DUR / CYCLE
for i, tgt in enumerate(targets):
    _, _, _, tx, ty = tgt
    ft = fire_times[i]
    sx, sy = ship_pos(ft)
    # Target center
    tcx, tcy = tx + CELL/2, ty + CELL/2
    balls.append(
        f'<g opacity="0">'
        f'<circle r="3.5" fill="#00FFFF"><animate attributeName="r" values="3.5;5;3.5" dur="0.2s" repeatCount="indefinite"/></circle>'
        f'<circle r="1.5" fill="#FFF" opacity="0.8"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{sx:.0f},{sy:.0f};{tcx:.0f},{tcy:.0f};{tcx:.0f},{tcy:.0f}" '
        f'keyTimes="0;{be_frac:.4f};1" dur="{CYCLE}s" begin="{ft:.1f}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;1;0;0" '
        f'keyTimes="0;{be_frac:.4f};{be_frac+0.003:.4f};1" dur="{CYCLE}s" begin="{ft:.1f}s" repeatCount="indefinite"/>'
        f'</g>')
    explosions.append(
        f'<circle cx="{tcx:.0f}" cy="{tcy:.0f}" r="6" fill="#00FFFF" opacity="0">'
        f'<animate attributeName="opacity" values="0;0;0.7;0;0" '
        f'keyTimes="0;{be_frac-0.001:.4f};{be_frac:.4f};{be_frac+0.03:.4f};1" '
        f'dur="{CYCLE}s" begin="{ft:.1f}s" repeatCount="indefinite"/>'
        f'<animate attributeName="r" values="6;6;6;18;18" '
        f'keyTimes="0;{be_frac-0.001:.4f};{be_frac:.4f};{be_frac+0.03:.4f};1" '
        f'dur="{CYCLE}s" begin="{ft:.1f}s" repeatCount="indefinite"/>'
        f'</circle>')

# -- Ship waypoints --
wp = (f"{ship_xl:.0f},{ship_base_y:.0f}; {ship_xm:.0f},{ship_base_y-ship_amp:.0f}; "
      f"{ship_xr:.0f},{ship_base_y:.0f}; {ship_xm:.0f},{ship_base_y+ship_amp:.0f}; "
      f"{ship_xl:.0f},{ship_base_y:.0f}")
spline = "0.4 0 0.6 1;" * 3 + "0.4 0 0.6 1"

# -- HUD --
score_str = f"{total:06d}"
hi_score = f"{max(total * 2, 5000):06d}"

# -- Day labels --
day_labels = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ---------------------------------------------------------------------------
# Assemble SVG
# ---------------------------------------------------------------------------

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     role="img" aria-labelledby="gx-t gx-d">
  <title id="gx-t">Galaxia — {LOGIN} commit arcade</title>
  <desc id="gx-d">Retro arcade spaceship shooting a GitHub contribution grid. Last {DAYS} days.</desc>
  <defs>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="bglow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="xglow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#9BE9A8"/><stop offset="100%" stop-color="#39D353"/>
    </linearGradient>
    <linearGradient id="scanG" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0"/>
      <stop offset="50%" stop-color="#a78bfa" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#6366f1" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="rk-body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#E8F4FD"/><stop offset="50%" stop-color="#B8DCF2"/><stop offset="100%" stop-color="#4A90C2"/>
    </linearGradient>
    <linearGradient id="rk-nose" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#FF6B35"/><stop offset="100%" stop-color="#FFB366"/>
    </linearGradient>
    <linearGradient id="rk-wing" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#2EA043"/><stop offset="100%" stop-color="#9BE9A8"/>
    </linearGradient>
    <radialGradient id="space" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#0A0E1A"/><stop offset="100%" stop-color="#020305"/>
    </radialGradient>
  </defs>
  <style>
    .bg {{ fill: url(#space); }}
    .hud {{ fill: #9BE9A8; font: 11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .lbl {{ fill: #8b949e; font: 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .c0 {{ fill: {DARK[0]}; }} .c1 {{ fill: {DARK[1]}; }} .c2 {{ fill: {DARK[2]}; }}
    .c3 {{ fill: {DARK[3]}; }} .c4 {{ fill: {DARK[4]}; }}
    @media (prefers-color-scheme: light) {{
      .bg {{ fill: #ffffff; }}
      .hud {{ fill: #1f6feb; }}
      .lbl {{ fill: #656d76; }}
      .star {{ display: none; }}
      .c0 {{ fill: {LIGHT[0]}; }} .c1 {{ fill: {LIGHT[1]}; }} .c2 {{ fill: {LIGHT[2]}; }}
      .c3 {{ fill: {LIGHT[3]}; }} .c4 {{ fill: {LIGHT[4]}; }}
    }}
  </style>

  <!-- Background -->
  <rect class="bg" width="{width}" height="{height}" rx="12"/>

  <!-- Stars -->
  <g class="star">{''.join(stars)}</g>

  <!-- HUD top -->
  <g class="hud" opacity="0.9">
    <text x="20" y="18" filter="url(#glow)" fill="url(#hdr)" font-size="13" font-weight="700" letter-spacing="1">GALAXIA \u25b8 GITHUB GRID</text>
    <text x="20" y="34">SCORE {score_str} \u00b7 HI {hi_score}</text>
    <text x="20" y="48">FUEL <tspan fill="#3B82F6">\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2588</tspan><tspan fill="#1E3A8A">\u2591</tspan> \u00b7 AMMO \u221e</text>
    <circle cx="{width - 50}" cy="16" r="3" fill="#39D353">
      <animate attributeName="opacity" values="0.7;1;0.7" dur="2s" repeatCount="indefinite"/>
    </circle>
    <text x="{width - 42}" y="20" font-size="9">ONLINE</text>
  </g>

  <!-- Month labels -->
  <g class="lbl">{''.join(f'<text x="{x}" y="{PAD_T-12}">{m}</text>' for x, m in months)}</g>

  <!-- Day labels -->
  <g class="lbl">{''.join(f'<text x="{PAD_L-8}" y="{PAD_T+i*(CELL+GAP)+9}" text-anchor="end">{d}</text>' for i, d in enumerate(day_labels))}</g>

  <!-- Grid border -->
  <rect x="{PAD_L-4}" y="{PAD_T-6}" width="{grid_w+8}" height="{grid_h+12}" fill="none" stroke="#21262d" stroke-width="1" rx="6"/>

  <!-- Contribution cells -->
  <g>{''.join(cells)}</g>

  <!-- Scanline -->
  <rect x="{PAD_L}" y="{PAD_T-6}" width="{grid_w}" height="3" fill="url(#scanG)" opacity="0">
    <animate attributeName="y" values="{PAD_T-6};{grid_bottom+6}" dur="8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0;0.7;0.7;0" keyTimes="0;0.1;0.9;1" dur="8s" repeatCount="indefinite"/>
  </rect>

  <!-- Explosions (behind projectiles) -->
  <g filter="url(#xglow)">{''.join(explosions)}</g>

  <!-- Projectiles -->
  <g filter="url(#bglow)">{''.join(balls)}</g>

  <!-- Spaceship -->
  <g filter="url(#glow)">
    <animateTransform attributeName="transform" type="translate"
      values="{wp}" dur="{CYCLE}s" repeatCount="indefinite"
      calcMode="spline" keySplines="{spline}"/>
    <!-- Body -->
    <rect x="-18" y="-10" width="36" height="20" rx="3" fill="url(#rk-body)" stroke="#4A90C2" stroke-width="0.8"/>
    <!-- Nose -->
    <polygon points="18,-10 28,0 18,10" fill="url(#rk-nose)"/>
    <!-- Wings -->
    <polygon points="-10,-10 -18,-18 5,-10" fill="url(#rk-wing)"/>
    <polygon points="-10,10 -18,18 5,10" fill="url(#rk-wing)"/>
    <!-- Cockpit -->
    <ellipse cx="10" cy="0" rx="5" ry="4" fill="#87CEEB" opacity="0.8"/>
    <ellipse cx="12" cy="-1.5" rx="2" ry="1.5" fill="#FFF" opacity="0.5"/>
    <!-- Stripe details -->
    <rect x="-12" y="-6" width="2" height="12" fill="#FF8C42" opacity="0.6"/>
    <rect x="-6" y="-7" width="1.5" height="14" fill="#39D353" opacity="0.5"/>
    <!-- Thrusters -->
    <ellipse cx="-22" cy="-5" rx="5" ry="2.5" fill="#FF4500" opacity="0.8">
      <animate attributeName="rx" values="5;8;5" dur="0.15s" repeatCount="indefinite"/>
    </ellipse>
    <ellipse cx="-26" cy="-5" rx="7" ry="3.5" fill="#FFB347" opacity="0.4">
      <animate attributeName="rx" values="7;10;7" dur="0.12s" repeatCount="indefinite"/>
    </ellipse>
    <ellipse cx="-22" cy="5" rx="5" ry="2.5" fill="#FF4500" opacity="0.8">
      <animate attributeName="rx" values="5;8;5" dur="0.15s" repeatCount="indefinite"/>
    </ellipse>
    <ellipse cx="-26" cy="5" rx="7" ry="3.5" fill="#FFB347" opacity="0.4">
      <animate attributeName="rx" values="7;10;7" dur="0.12s" repeatCount="indefinite"/>
    </ellipse>
    <!-- Nav lights -->
    <circle cx="25" cy="0" r="1.5" fill="#00FF00">
      <animate attributeName="opacity" values="0.8;0.3;0.8" dur="1s" repeatCount="indefinite"/>
    </circle>
    <circle cx="-16" cy="-16" r="1" fill="#FF0000">
      <animate attributeName="opacity" values="0.8;0.3;0.8" dur="1.2s" repeatCount="indefinite"/>
    </circle>
    <circle cx="-16" cy="16" r="1" fill="#FF0000">
      <animate attributeName="opacity" values="0.8;0.3;0.8" dur="1.4s" repeatCount="indefinite"/>
    </circle>
  </g>

  <!-- HUD bottom -->
  <g class="hud" opacity="0.5">
    <text x="20" y="{height-8}" font-size="9">MISSION: DEPLOY ENERGY WEAPONS \u00b7 TARGET: GITHUB GRID</text>
    <text x="{width/2:.0f}" y="{height-8}" font-size="9">ENERGY CANNON: ACTIVE \u00b7 TRACKING: ENABLED</text>
  </g>

  <!-- Legend -->
  <g>
    {''.join(legend)}
    <text x="{PAD_L-10}" y="{height-8}" text-anchor="end" class="lbl">Less</text>
    <text x="{PAD_L+5*(CELL+GAP)+10}" y="{height-8}" class="lbl">More</text>
  </g>
</svg>"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"Wrote {OUT} ({width}x{height}) for {LOGIN}. Total: {total}")
