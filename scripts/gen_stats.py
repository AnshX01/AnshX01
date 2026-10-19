"""Builds arcade-stats-live.svg from public GitHub data for one user."""
import os, re, json, time, datetime as dt, urllib.request
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

USER = os.environ.get("GH_USER", "AnshX01")
PROFILE_REPO = USER
TOKEN = os.environ.get("GITHUB_TOKEN", "")
FONT = os.environ.get("FONT_PATH", "PressStart2P-Regular.ttf")
SLEEP = float(os.environ.get("API_SLEEP", "2.5"))
OUT = os.environ.get("OUT", "arcade-stats-live.svg")

def get(url, accept="application/vnd.github+json", raw=False):
    h = {"Accept": accept, "User-Agent": "arcade-stats"}
    if TOKEN and "api.github.com" in url:
        h["Authorization"] = "Bearer " + TOKEN
    for i in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40)
            b = r.read().decode()
            return b if raw else json.loads(b)
        except Exception as e:
            if i == 3: raise
            time.sleep(8)

def commit_count(q):
    time.sleep(SLEEP)
    return get("https://api.github.com/search/commits?q=" + q + "&per_page=1",
               accept="application/vnd.github.cloak-preview")["total_count"]

# ---- data (all public, signed-out) ----
today = dt.datetime.utcnow().date()
since = (today - dt.timedelta(days=365)).isoformat()
commits_all = commit_count(f"author:{USER}")
commits_365 = commit_count(f"author:{USER}+author-date:%3E{since}")

repos = [r for r in get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner") if not r["fork"]]
n_repos = len(repos)
per_repo = []
for r in repos:
    if r["name"].lower() == PROFILE_REPO.lower():
        continue
    per_repo.append((r["name"], commit_count(f"author:{USER}+repo:{USER}/{r['name']}")))
per_repo.sort(key=lambda x: -x[1])
per_repo = per_repo[:6]

langs = {}
for r in repos:
    for k, v in get(f"https://api.github.com/repos/{USER}/{r['name']}/languages").items():
        langs[k] = langs.get(k, 0) + v
langs.pop("Jupyter Notebook", None)
tot = sum(langs.values())
top = sorted(langs.items(), key=lambda x: -x[1])[:5]
other = tot - sum(v for _, v in top)
lang_rows = [(k, 100 * v / tot) for k, v in top] + [("Other", 100 * other / tot)]

html = get(f"https://github.com/users/{USER}/contributions", raw=True)
cells = re.findall(r'<td[^>]*data-date="(\d{4}-\d\d-\d\d)"[^>]*id="([^"]+)"[^>]*data-level="(\d)"', html)
tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html))
cal, lev = {}, {}
for date, i, l in cells:
    m = re.match(r"(\d+) contribution", tips.get(i, ""))
    cal[date] = int(m.group(1)) if m else 0
    lev[date] = l
assert len(cal) > 300, "calendar parse failed"
contribs = sum(cal.values())
active = sum(1 for v in cal.values() if v)
top_day = max(cal, key=cal.get)
td = dt.date.fromisoformat(top_day)
top_cap = "CONTRIBS, " + td.strftime("%b").upper() + " " + str(td.day)

# ---- drawing ----
F = TTFont(FONT)
GS = F.getGlyphSet(); CM = F.getBestCmap(); HM = F["hmtx"]; UPM = F["head"].unitsPerEm
def vpath(x, y, size, t, anchor="l"):
    sc = size / UPM; adv = 0; items = []
    for ch in t:
        g = CM.get(ord(ch)) or CM.get(ord("?")); items.append((g, adv)); adv += HM[g][0]
    W = adv * sc
    if anchor == "c": x -= W / 2
    elif anchor == "r": x -= W
    pen = SVGPathPen(GS, ntos=lambda v: f"{v:.1f}")
    for g, a in items:
        GS[g].draw(TransformPen(pen, (sc, 0, 0, -sc, x + a * sc, y)))
    return pen.getCommands(), W
o = []
def txt(x, y, size, t, fill, anchor="l"):
    d, _ = vpath(x, y, size, t, anchor); o.append(f'<path fill="{fill}" d="{d}"/>')
def panel(x, y, w, h):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#0b0b50" stroke="#2323d8" stroke-width="2"/>')
W = 640
y0 = 10
_, bw = vpath(0, 0, 12, "STAGE 3")
o.append(f'<rect x="16" y="{y0}" width="{bw+20:.0f}" height="30" fill="#f7c935"/>')
txt(26, y0 + 21, 12, "STAGE 3", "#3a2a00")
tx = 16 + bw + 36
d, w = vpath(tx, y0 + 22, 16, "HIGH SCORES"); o.append(f'<path fill="#ffffff" d="{d}"/>')
o.append(f'<line x1="{tx+w+12:.0f}" y1="{y0+15}" x2="624" y2="{y0+15}" stroke="#2323d8" stroke-width="3" stroke-dasharray="8 6"/>')
tiles = [("PUBLIC COMMITS", f"{commits_all}", "ALL TIME"), ("PUBLIC COMMITS", f"{commits_365}", "LAST 365 DAYS"),
         ("CONTRIBUTIONS", f"{contribs}", "LAST 365 DAYS"), ("ACTIVE DAYS", f"{active}", "LAST 365 DAYS"),
         ("OWN REPOS", f"{n_repos}", "NOT FORKS"), ("TOP DAY", f"{cal[top_day]}", top_cap)]
tw_ = 196; g = 9
for i, (l, n, c) in enumerate(tiles):
    r, cc = divmod(i, 3); x = 16 + cc * (tw_ + g); y = 54 + r * 108
    panel(x, y, tw_, 98)
    txt(x + 14, y + 26, 10, l, "#9aa0ff"); txt(x + 14, y + 66, 28, n, "#f7c935"); txt(x + 14, y + 88, 10, c, "#ff7ac8")
y = 54 + 2 * 108 + 6
panel(16, y, 608, 176)
txt(30, y + 28, 12, "ACTIVITY HEATMAP", "#ffffff"); txt(610, y + 28, 10, "LAST 365 DAYS", "#ff7ac8", "r")
ds = sorted(lev); d0 = dt.date.fromisoformat(ds[0]); off = (d0.weekday() + 1) % 7
cols = {"0": "#17176a", "1": "#5a4a1a", "2": "#a8841f", "3": "#d9ab26", "4": "#ffd84a"}
cs = 9.6; gx = 30; gy = y + 46
for d_ in ds:
    idx = (dt.date.fromisoformat(d_) - d0).days + off; c, r = divmod(idx, 7)
    o.append(f'<rect x="{gx+c*(cs+1.0):.1f}" y="{gy+r*(cs+1.0):.1f}" width="{cs}" height="{cs}" fill="{cols[lev[d_]]}"/>')
txt(30, y + 160, 10, "LESS", "#9aa0ff")
for i in range(5): o.append(f'<rect x="{86+i*16}" y="{y+150}" width="12" height="12" fill="{cols[str(i)]}"/>')
txt(176, y + 160, 10, "MORE", "#9aa0ff"); txt(610, y + 160, 10, "CONTRIBUTIONS PER DAY", "#8a8aa8", "r")
y += 176 + 12
panel(16, y, 608, 40 + len(per_repo) * 30 + 18)
txt(30, y + 28, 12, "COMMITS BY PROJECT", "#ffffff"); txt(610, y + 28, 10, "PUBLIC, ALL TIME", "#ff7ac8", "r")
mx = max(1, per_repo[0][1])
for i, (n, c) in enumerate(per_repo):
    yy = y + 60 + i * 30
    txt(30, yy + 12, 11, n[:14], "#f7c935")
    o.append(f'<rect x="200" y="{yy}" width="330" height="14" fill="#23236a"/>')
    o.append(f'<rect x="200" y="{yy}" width="{max(3,c/mx*330):.0f}" height="14" fill="#f7c935"/>')
    txt(610, yy + 12, 11, str(c), "#ffffff", "r")
y += 40 + len(per_repo) * 30 + 18 + 12
panel(16, y, 608, 205)
txt(30, y + 28, 12, "LANGUAGES", "#ffffff"); txt(610, y + 28, 10, "BY CODE BYTES", "#ff7ac8", "r")
palette = ["#f7c935", "#ff7ac8", "#4fd8ff", "#5af0a0", "#9aa0ff", "#8a8aa8"]
x = 30
for (n, p), c in zip(lang_rows, palette):
    w = p / 100 * 580; o.append(f'<rect x="{x:.1f}" y="{y+44}" width="{w:.1f}" height="22" fill="{c}"/>'); x += w
for i, ((n, p), c) in enumerate(zip(lang_rows, palette)):
    r, cc = divmod(i, 2); lx = 30 + cc * 296; ly = y + 90 + r * 32
    o.append(f'<rect x="{lx}" y="{ly}" width="14" height="14" fill="{c}"/>')
    txt(lx + 24, ly + 12, 11, n[:12].upper() if False else n[:12], "#ffffff"); txt(lx + 270, ly + 12, 11, f"{p:.1f}%", "#f7c935", "r")
txt(30, y + 192, 10, "OWN PUBLIC REPOS, JUPYTER NB EXCLUDED", "#8a8aa8")
y += 205 + 14
txt(16, y + 10, 10, f"COMMITS: PUBLIC REPOS, DEFAULT BRANCH, AUTHOR {USER.upper()}", "#8a8aa8")
txt(16, y + 32, 10, f"CONTRIBUTIONS: PUBLIC ONLY. UPDATED {today.isoformat()} UTC", "#8a8aa8")
y += 22
H = int(y + 30)
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="#04041a"/>' + "\n".join(o) + "</svg>"
open(OUT, "w").write(svg)
print("ok", len(svg), H, commits_all, commits_365, contribs, active, per_repo, lang_rows)
