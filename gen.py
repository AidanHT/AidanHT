# -*- coding: utf-8 -*-
"""
Generator for Aidan Tran's GitHub profile README assets.
Produces self-contained animated SVGs (SMIL + CSS) in a minimalist
math / geometry dark theme. Real 3D wireframes are rotated frame-by-frame
and emitted as SMIL keyframe animations so they animate on GitHub (served
as <img>, the browser renders the animation).
"""
import math, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(OUT, exist_ok=True)

INK    = "#0a0e14"   # card background
INK2   = "#0c1219"
LINE   = "#1b2632"   # borders / grid
CHALK  = "#dfe7ef"   # primary wireframe / text
MUTE   = "#5b6b7d"   # muted text
ACCENT = "#64ffda"   # mint accent
ACC2   = "#4f9cf9"   # cool blue accent

def f1(v): return f"{v:.1f}"

# ----------------------------------------------------------------------------
# 3D helpers
# ----------------------------------------------------------------------------
def rot_y(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a)
    return (c*x + s*z, y, -s*x + c*z)

def rot_x(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a)
    return (x, c*y - s*z, s*y + c*z)

def project(p, size, scale, persp):
    x, y, z = p
    f = persp / (persp - z)
    return (size/2 + x*scale*f, size/2 - y*scale*f, z)

def wire3d(verts, edges, size, scale, persp, tilt, frames, dur, edge_w=1.3):
    """Return inner SVG for a rotating wireframe (depth-shaded)."""
    # precompute projected coords + z for every frame (frame 0 repeated at end)
    seq = []
    for i in range(frames):
        th = 2*math.pi*i/frames
        pr = [project(rot_x(rot_y(v, th), tilt), size, scale, persp) for v in verts]
        seq.append(pr)
    seq.append(seq[0])

    def depth_opacity(z):  # back -> faint, front -> bright
        t = (z + scale) / (2*scale)
        return 0.16 + 0.84*max(0.0, min(1.0, t))

    parts = []
    for (a, b) in edges:
        x1 = [seq[fr][a][0] for fr in range(frames+1)]
        y1 = [seq[fr][a][1] for fr in range(frames+1)]
        x2 = [seq[fr][b][0] for fr in range(frames+1)]
        y2 = [seq[fr][b][1] for fr in range(frames+1)]
        op = [depth_opacity((seq[fr][a][2]+seq[fr][b][2])/2) for fr in range(frames+1)]
        def vals(arr): return ";".join(f1(v) for v in arr)
        parts.append(
            f'<line x1="{f1(x1[0])}" y1="{f1(y1[0])}" x2="{f1(x2[0])}" y2="{f1(y2[0])}" '
            f'stroke="{CHALK}" stroke-width="{edge_w}" stroke-linecap="round" opacity="{f1(op[0])}">'
            f'<animate attributeName="x1" dur="{dur}s" repeatCount="indefinite" values="{vals(x1)}"/>'
            f'<animate attributeName="y1" dur="{dur}s" repeatCount="indefinite" values="{vals(y1)}"/>'
            f'<animate attributeName="x2" dur="{dur}s" repeatCount="indefinite" values="{vals(x2)}"/>'
            f'<animate attributeName="y2" dur="{dur}s" repeatCount="indefinite" values="{vals(y2)}"/>'
            f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="{vals(op)}"/>'
            f'</line>'
        )
    for vi in range(len(verts)):
        cx = [seq[fr][vi][0] for fr in range(frames+1)]
        cy = [seq[fr][vi][1] for fr in range(frames+1)]
        op = [depth_opacity(seq[fr][vi][2]) for fr in range(frames+1)]
        def vals(arr): return ";".join(f1(v) for v in arr)
        parts.append(
            f'<circle cx="{f1(cx[0])}" cy="{f1(cy[0])}" r="2.3" fill="{ACCENT}" opacity="{f1(op[0])}">'
            f'<animate attributeName="cx" dur="{dur}s" repeatCount="indefinite" values="{vals(cx)}"/>'
            f'<animate attributeName="cy" dur="{dur}s" repeatCount="indefinite" values="{vals(cy)}"/>'
            f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" values="{vals(op)}"/>'
            f'</circle>'
        )
    return "\n".join(parts)

# ----------------------------------------------------------------------------
# Shape data
# ----------------------------------------------------------------------------
def icosahedron():
    p = (1 + math.sqrt(5)) / 2
    v = [(0, 1, p), (0, 1, -p), (0, -1, p), (0, -1, -p),
         (1, p, 0), (1, -p, 0), (-1, p, 0), (-1, -p, 0),
         (p, 0, 1), (p, 0, -1), (-p, 0, 1), (-p, 0, -1)]
    e = []
    for i in range(len(v)):
        for j in range(i+1, len(v)):
            d2 = sum((v[i][k]-v[j][k])**2 for k in range(3))
            if abs(d2 - 4.0) < 1e-6:
                e.append((i, j))
    return v, e

# ----------------------------------------------------------------------------
# common defs
# ----------------------------------------------------------------------------
def defs(glow_id="glow", grid_id="grid", grad_id="acc"):
    return f'''<defs>
    <linearGradient id="{grad_id}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{ACCENT}"/>
      <stop offset="1" stop-color="{ACC2}"/>
    </linearGradient>
    <filter id="{glow_id}" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <pattern id="{grid_id}" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M30 0H0V30" fill="none" stroke="{CHALK}" stroke-width="0.6" opacity="0.05"/>
    </pattern>
  </defs>'''

# ----------------------------------------------------------------------------
# POLYHEDRON  (hero 3D piece)
# ----------------------------------------------------------------------------
def build_polyhedron():
    S = 340
    v, e = icosahedron()
    wires = wire3d(v, e, size=S, scale=46, persp=6.0, tilt=0.46,
                   frames=60, dur=24, edge_w=1.25)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}" role="img" aria-label="Rotating wireframe icosahedron">
  {defs("g1","grid1","acc1")}
  <rect width="{S}" height="{S}" rx="18" fill="{INK}"/>
  <rect width="{S}" height="{S}" fill="url(#grid1)"/>
  <rect x="0.5" y="0.5" width="{S-1}" height="{S-1}" rx="18" fill="none" stroke="{LINE}"/>
  <circle cx="{S/2}" cy="{S/2}" r="118" fill="none" stroke="url(#acc1)" stroke-width="1" stroke-dasharray="2 8" opacity="0.35">
    <animateTransform attributeName="transform" type="rotate" from="0 {S/2} {S/2}" to="360 {S/2} {S/2}" dur="60s" repeatCount="indefinite"/>
  </circle>
  <circle cx="{S/2}" cy="{S/2}" r="92" fill="{ACCENT}" opacity="0.04"/>
  <g filter="url(#g1)">
  {wires}
  </g>
  <g fill="{MUTE}" font-family="ui-monospace,'SF Mono','JetBrains Mono',monospace" font-size="9" opacity="0.6">
    <text x="14" y="22">// icosahedron</text>
    <text x="14" y="{S-14}">V=12  E=30  F=20</text>
    <text x="{S-14}" y="{S-14}" text-anchor="end">χ = V − E + F = 2</text>
  </g>
</svg>'''
    open(os.path.join(OUT, "polyhedron.svg"), "w", encoding="utf-8").write(svg)

# ----------------------------------------------------------------------------
# GYROSCOPE / ATOM  (second 3D piece — pseudo-3D, lightweight)
# ----------------------------------------------------------------------------
def build_gyro():
    S = 300; cx = cy = S/2
    R = 96
    rings = []
    orbits = [(0, 8, ACCENT), (60, 9.5, ACC2), (120, 8.7, "#a78bfa")]
    for i, (deg, dur, col) in enumerate(orbits):
        # an ellipse whose horizontal radius "breathes" 0..R to fake depth rotation
        ring = f'''<g transform="rotate({deg} {cx} {cy})">
      <ellipse cx="{cx}" cy="{cy}" rx="{R}" ry="34" fill="none" stroke="{CHALK}" stroke-width="1" opacity="0.30">
        <animate attributeName="rx" values="{R};6;{R}" dur="{dur}s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.30;0.12;0.30" dur="{dur}s" repeatCount="indefinite"/>
      </ellipse>
      <circle r="4.5" fill="{col}">
        <animateMotion dur="{dur}s" repeatCount="indefinite"
          path="M {cx-R} {cy} a {R} 34 0 1 1 {2*R} 0 a {R} 34 0 1 1 {-2*R} 0"/>
      </circle>
    </g>'''
        rings.append(ring)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}" width="{S}" height="{S}" role="img" aria-label="Animated gyroscope">
  {defs("g2","grid2","acc2")}
  <rect width="{S}" height="{S}" rx="18" fill="{INK}"/>
  <rect width="{S}" height="{S}" fill="url(#grid2)"/>
  <rect x="0.5" y="0.5" width="{S-1}" height="{S-1}" rx="18" fill="none" stroke="{LINE}"/>
  <g filter="url(#g2)">
  {''.join(rings)}
  <circle cx="{cx}" cy="{cy}" r="6.5" fill="{ACCENT}">
    <animate attributeName="r" values="6.5;9;6.5" dur="3s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.55;1" dur="3s" repeatCount="indefinite"/>
  </circle>
  </g>
  <g fill="{MUTE}" font-family="ui-monospace,monospace" font-size="9" opacity="0.6">
    <text x="14" y="22">// state space</text>
    <text x="{S-14}" y="{S-14}" text-anchor="end">∮ orbit · dt</text>
  </g>
</svg>'''
    open(os.path.join(OUT, "gyro.svg"), "w", encoding="utf-8").write(svg)

# ----------------------------------------------------------------------------
# BANNER
# ----------------------------------------------------------------------------
def lissajous_path(cx, cy, A, B, a, b, delta, n=240):
    pts = []
    for i in range(n+1):
        t = 2*math.pi*i/n
        x = cx + A*math.sin(a*t + delta)
        y = cy + B*math.sin(b*t)
        pts.append((x, y))
    return "M " + " L ".join(f"{f1(x)} {f1(y)}" for x, y in pts)

def sine_path(x0, x1, y, amp, wl, step=4):
    pts = []
    x = x0
    while x <= x1:
        pts.append((x, y + amp*math.sin(2*math.pi*(x)/wl)))
        x += step
    return "M " + " L ".join(f"{f1(px)} {f1(py)}" for px, py in pts)

def build_banner():
    W, H = 900, 220
    ucx, ucy, ur = 132, H/2, 50           # unit circle (left)
    circ_path = f"M {ucx-ur} {ucy} a {ur} {ur} 0 1 1 {2*ur} 0 a {ur} {ur} 0 1 1 {-2*ur} 0"
    liss = lissajous_path(770, H/2, 70, 64, 3, 2, math.pi/2)
    base_sine = sine_path(-200, W+200, H-26, 6, 180, 4)

    glyphs = [("π", 250, 60), ("φ", 470, 168), ("∑", 600, 54),
              ("∫", 705, 178), ("∞", 360, 196), ("∂", 540, 96)]
    gtext = ""
    for i, (g, x, y) in enumerate(glyphs):
        dur = 7 + i
        gtext += (f'<text x="{x}" y="{y}" font-family="serif" font-size="22" fill="{CHALK}" opacity="0.07">{g}'
                  f'<animateTransform attributeName="transform" type="translate" '
                  f'values="0 0;0 -8;0 0" dur="{dur}s" repeatCount="indefinite"/></text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Aidan Tran">
  {defs("gb","gridb","accb")}
  <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="{INK}"/>
    <rect width="{W}" height="{H}" fill="url(#gridb)"/>
    <!-- travelling baseline wave -->
    <g opacity="0.5">
      <path d="{base_sine}" fill="none" stroke="url(#accb)" stroke-width="1.3">
        <animateTransform attributeName="transform" type="translate" from="0 0" to="-180 0" dur="6s" repeatCount="indefinite"/>
      </path>
    </g>
    {gtext}
    <!-- decorative lissajous -->
    <path d="{liss}" fill="none" stroke="{CHALK}" stroke-width="1" opacity="0.16" pathLength="1"
          stroke-dasharray="1" stroke-dashoffset="1">
      <animate attributeName="stroke-dashoffset" values="1;0;0;1" keyTimes="0;0.5;0.85;1" dur="11s" repeatCount="indefinite"/>
    </path>
    <!-- unit circle construction -->
    <circle cx="{ucx}" cy="{ucy}" r="{ur}" fill="none" stroke="{CHALK}" stroke-width="1" opacity="0.28"/>
    <line x1="{ucx-ur-8}" y1="{ucy}" x2="{ucx+ur+8}" y2="{ucy}" stroke="{CHALK}" stroke-width="0.6" opacity="0.18"/>
    <line x1="{ucx}" y1="{ucy-ur-8}" x2="{ucx}" y2="{ucy+ur+8}" stroke="{CHALK}" stroke-width="0.6" opacity="0.18"/>
    <g>
      <line x1="{ucx}" y1="{ucy}" x2="{ucx+ur}" y2="{ucy}" stroke="url(#accb)" stroke-width="1.4">
        <animateTransform attributeName="transform" type="rotate" from="0 {ucx} {ucy}" to="-360 {ucx} {ucy}" dur="9s" repeatCount="indefinite"/>
      </line>
    </g>
    <circle r="4" fill="{ACCENT}">
      <animateMotion dur="9s" repeatCount="indefinite" keyPoints="0;1" keyTimes="0;1" rotate="0" path="{circ_path}"/>
    </circle>
    <!-- title -->
    <g font-family="ui-sans-serif,system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif">
      <text x="232" y="106" font-size="50" font-weight="700" letter-spacing="7" fill="{CHALK}">AIDAN TRAN</text>
      <path d="M234 122 H520" stroke="url(#accb)" stroke-width="2" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">
        <animate attributeName="stroke-dashoffset" values="1;0" dur="2.2s" begin="0.3s" fill="freeze"/>
      </path>
    </g>
    <g font-family="ui-monospace,'SF Mono','JetBrains Mono',monospace" font-size="15">
      <text x="235" y="150" fill="{MUTE}">$ whoami<tspan fill="{ACCENT}"> → </tspan><tspan fill="{CHALK}">AI/ML · systems · full stack</tspan></text>
      <rect x="600" y="139" width="9" height="15" fill="{ACCENT}">
        <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.1s" repeatCount="indefinite"/>
      </rect>
    </g>
    <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{LINE}"/>
  </g>
</svg>'''
    open(os.path.join(OUT, "banner.svg"), "w", encoding="utf-8").write(svg)

# ----------------------------------------------------------------------------
# DIVIDER  (travelling wave)
# ----------------------------------------------------------------------------
def build_divider():
    W, H = 900, 36
    wave = sine_path(-200, W+200, H/2, 6, 180, 4)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="divider">
  {defs("gd","gridd","accd")}
  <clipPath id="dc"><rect width="{W}" height="{H}"/></clipPath>
  <g clip-path="url(#dc)">
    <line x1="0" y1="{H/2}" x2="{W}" y2="{H/2}" stroke="{LINE}" stroke-width="1" stroke-dasharray="2 6"/>
    <path d="{wave}" fill="none" stroke="url(#accd)" stroke-width="1.5" opacity="0.7">
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-180 0" dur="5s" repeatCount="indefinite"/>
    </path>
    <circle cx="{W/2}" cy="{H/2}" r="3.5" fill="{ACCENT}">
      <animate attributeName="opacity" values="1;0.3;1" dur="2.4s" repeatCount="indefinite"/>
    </circle>
  </g>
</svg>'''
    open(os.path.join(OUT, "divider.svg"), "w", encoding="utf-8").write(svg)

# ----------------------------------------------------------------------------
# BADGES (custom, on-theme, clickable via wrapping <a> in README)
# ----------------------------------------------------------------------------
def badge(name, label, icon_svg, accent):
    pad_left = 46
    w = pad_left + 10 + int(len(label) * 8.6) + 14
    h = 44
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="{INK2}" stroke="{LINE}"/>
  <rect x="0.5" y="0.5" width="3" height="{h-1}" rx="1.5" fill="{accent}"/>
  <g transform="translate(16,{h/2})">{icon_svg}</g>
  <line x1="{pad_left-8}" y1="9" x2="{pad_left-8}" y2="{h-9}" stroke="{LINE}"/>
  <text x="{pad_left}" y="{h/2+4.5}" font-family="ui-monospace,'SF Mono','JetBrains Mono',monospace" font-size="13" fill="{CHALK}">{label}</text>
  <circle cx="{w-13}" cy="{h/2}" r="2" fill="{accent}">
    <animate attributeName="opacity" values="1;0.25;1" dur="2.6s" repeatCount="indefinite"/>
  </circle>
</svg>'''
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(svg)

def build_badges():
    # website: small globe (circle + meridian arcs)
    web_icon = f'''<circle r="9" fill="none" stroke="{ACCENT}" stroke-width="1.4"/>
      <ellipse rx="4" ry="9" fill="none" stroke="{ACCENT}" stroke-width="1.2"/>
      <line x1="-9" y1="0" x2="9" y2="0" stroke="{ACCENT}" stroke-width="1.2"/>'''
    badge("badge_web.svg", "aidanht.me", web_icon, ACCENT)

    # linkedin: "in"
    li_icon = f'''<rect x="-9" y="-9" width="18" height="18" rx="3.5" fill="none" stroke="{ACC2}" stroke-width="1.4"/>
      <text x="0" y="4.5" text-anchor="middle" font-family="ui-sans-serif,Arial,sans-serif" font-size="11" font-weight="700" fill="{ACC2}">in</text>'''
    badge("badge_linkedin.svg", "in/aidantran120", li_icon, ACC2)

    # X: crossing strokes
    x_icon = f'''<line x1="-7" y1="-7" x2="7" y2="7" stroke="{CHALK}" stroke-width="1.8" stroke-linecap="round"/>
      <line x1="7" y1="-7" x2="-7" y2="7" stroke="{CHALK}" stroke-width="1.8" stroke-linecap="round"/>'''
    badge("badge_x.svg", "@AidanHTran", x_icon, CHALK)

# ----------------------------------------------------------------------------
build_polyhedron()
build_banner()
build_divider()
build_badges()
print("assets written:", ", ".join(sorted(os.listdir(OUT))))
for fn in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, fn)
    print(f"  {fn:20s} {os.path.getsize(p)/1024:6.1f} KB")
