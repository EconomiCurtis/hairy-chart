#!/usr/bin/env python3
"""
Build the interactive hairy plot from data/, text.qmd and template.html.

    python3 interactive/_app/build.py && node interactive/_app/check.js

Inputs
    ../../data/fed_funds_rate.csv   the target rate, one row per day
    ../../data/hairs.csv            every hair, one row per point
    ../../data/nber_recessions.csv  NBER peaks and troughs, for the shading
    text.qmd                        the prose: plot title and subtitle, Notes
    template.html                   CSS, markup and the plotting script, with
                                    __PLACEHOLDER__ tokens filled in below

Outputs
    ../_hairy-app.html              the fragment interactive/index.qmd includes.
                                    Committed: the site build has no Python.
    preview.html                    the same fragment in a bare page, for a
                                    quick look without Quarto. Not committed.

Standard library only, plus the pandoc that ships with Quarto for the prose.
"""
import csv
import datetime as dt
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data"
QMD = HERE / "text.qmd"
TEMPLATE = HERE / "template.html"
SOURCES_MD = ROOT / "misc" / "SOURCES.md"
FRAGMENT = HERE.parent / "_hairy-app.html"
PREVIEW = HERE / "preview.html"

# The four series, in legend order. Labels, colors and source lines are the
# notebooks' own (src_label, pal, src_caption); misc/SOURCES.md documents the
# source lines and the build checks they still match it.
#   k      sets line opacity: k / (hairs on screen), clamped to 0.08-0.55, so
#          the full view matches the notebooks' combined plot and a zoomed
#          view with few hairs draws them more strongly.
#   width  line width in CSS pixels.
#   step   drawn as steps, each value held across its calendar quarter.
#   about  the line under the series name in the tooltip: what the numbers are.
SERIES = [
    dict(key="treasury_forward", label="Treasury Forward Curve", color="#2E7DBF",
         source="Federal Reserve Board, GSW nominal yield curve",
         about="Forward rates from the Treasury yield curve",
         k=66, width=1.0, step=False),
    dict(key="options_implied", label="Options-Implied (SOFR)", color="#C8102E",
         source="Federal Reserve Bank of Atlanta, Market Probability Tracker",
         about="Expected SOFR, averaged over three-month windows",
         k=80, width=1.0, step=False),
    dict(key="sep_median", label="FOMC Median Projection", color="#E08A1E",
         source="Federal Reserve Board, Summary of Economic Projections",
         about="Median projection for each year end",
         k=60, width=1.5, step=False),
    dict(key="spf_median", label="Professional Forecasters", color="#8C1A8C",
         source="Federal Reserve Bank of Philadelphia, Survey of Professional Forecasters",
         about="Median forecast of the three-month T-bill, by quarter",
         k=70, width=1.2, step=True),
]
TARGET = dict(label="Federal funds target rate", color="#0B1B4A",
              source="Federal Reserve Board via the St. Louis Fed's FRED (target rate)")
# Recession shading, the last legend item and off until switched on.
RECESSIONS = dict(label="Recessions",
                  source="National Bureau of Economic Research via the St. Louis Fed's FRED (recessions)")
# Back to front, as in the notebooks' combined plot. The target line goes on top.
DRAW_ORDER = ["spf_median", "treasury_forward", "options_implied", "sep_median"]

NOTES = "Notes"
KNOWN = (NOTES,)

EPOCH = dt.date(1970, 1, 1)


def die(msg):
    sys.exit(f"build.py: {msg}")


def day(s):
    """ISO date string to days since 1970-01-01, the unit the page works in."""
    return (dt.date.fromisoformat(s) - EPOCH).days


def bp(x):
    """Percent to whole basis points. A basis point is finer than any line or
    label on the page can show, and integers keep the payload small."""
    return round(float(x) * 100)


def build_rate():
    """The target as change points: [day, lo, hi] in percent, wherever either
    end moves.

    16,092 daily rows collapse to a couple of hundred. The page draws the
    midpoint as a step line and reads lo and hi for the tooltip. Kept exact,
    not rounded to basis points: the reconstructed 1980s targets move in
    sixteenths of a point, such as 8.5625.
    """
    rows = list(csv.DictReader(open(DATA / "fed_funds_rate.csv", encoding="utf-8")))
    if not rows:
        die("fed_funds_rate.csv is empty")
    days = [day(r["date"]) for r in rows]
    if days != list(range(days[0], days[0] + len(days))):
        die("fed_funds_rate.csv is not one row per calendar day")
    out, prev = [], None
    for d, r in zip(days, rows):
        cur = (float(r["target_lo"]), float(r["target_hi"]))
        if cur != prev:
            out.append([d, *cur])
            prev = cur
    return {"c": out, "end": days[-1]}


def build_hairs():
    """Each series as one flat integer array, delta-encoded.

    Per hair: as_of (days after the previous hair's as_of), the point count n,
    then n pairs of (days after the previous point, or after as_of for the
    first; basis points change from the previous point, or the level for the
    first). Small deltas are mostly one or two digits, which roughly halves
    the payload against absolute values.
    """
    groups = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(DATA / "hairs.csv", encoding="utf-8")):
        groups[r["source"]][day(r["as_of"])].append((day(r["target_date"]), bp(r["rate_pct"])))
    known = {s["key"] for s in SERIES}
    if set(groups) != known:
        die(f"hairs.csv sources {sorted(groups)} != {sorted(known)}")

    flat, counts = {}, {}
    for s in SERIES:
        arr, prev_asof = [], 0
        hairs = groups[s["key"]]
        for as_of in sorted(hairs):
            pts = sorted(hairs[as_of])
            if pts[0][0] < as_of:
                die(f"{s['key']} {as_of}: a point dated before its forecast date")
            arr += [as_of - prev_asof, len(pts)]
            prev_asof, px, py = as_of, as_of, 0
            for d, v in pts:
                arr += [d - px, v - py]
                px, py = d, v
        flat[s["key"]] = arr
        counts[s["key"]] = (len(hairs), sum(len(p) for p in hairs.values()))
    return flat, counts


def build_recessions():
    """NBER recessions as [peak day, trough day], shaded peak to trough as on
    FRED's graphs."""
    rows = list(csv.DictReader(open(DATA / "nber_recessions.csv", encoding="utf-8")))
    spells = [[day(r["peak"]), day(r["trough"])] for r in rows]
    if not spells or any(a >= b for a, b in spells):
        die("nber_recessions.csv is empty or has a peak on or after its trough")
    return spells


def md(text):
    """Markdown to HTML with the pandoc bundled with Quarto."""
    if not text.strip():
        return ""
    try:
        r = subprocess.run(["quarto", "pandoc", "-f", "markdown", "-t", "html"],
                           input=text, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        die("quarto not found on PATH (needed for its pandoc)")
    except subprocess.CalledProcessError as e:
        die(f"pandoc failed: {e.stderr.strip()}")
    return r.stdout.strip()


def split_qmd(path):
    """(front matter dict, {## heading: markdown body}). A small YAML subset:
    `key: value` lines, which is all the front matter here uses."""
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        die(f"{path.name} has no front matter")
    meta = {}
    for line in m.group(1).split("\n"):
        if re.match(r"^\w[\w-]*:", line):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    body = re.sub(r"<!--.*?-->", "", m.group(2), flags=re.S)
    sections, title, buf = {}, None, []
    for line in body.split("\n"):
        h = re.match(r"^##\s+(?!#)(.*)$", line)
        if h:
            if title:
                sections[title] = "\n".join(buf).strip()
            title, buf = h.group(1).strip(), []
        elif title:
            buf.append(line)
    if title:
        sections[title] = "\n".join(buf).strip()
    return meta, sections


def check_sources_md():
    """Each source line should match its "Plot source line." in SOURCES.md.
    A warning rather than a failure: the page is still right, the docs are not."""
    if not SOURCES_MD.exists():
        print("  warning: misc/SOURCES.md not found; source lines not checked")
        return
    documented = set(re.findall(r"\*\*Plot source line\.\*\*\s*(.+)",
                                SOURCES_MD.read_text(encoding="utf-8")))
    for line in [s["source"] for s in SERIES] + [TARGET["source"], RECESSIONS["source"]]:
        if line.strip() not in {d.strip() for d in documented}:
            print(f"  warning: source line not in misc/SOURCES.md: {line!r}")


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def main():
    for p in (QMD, TEMPLATE, DATA / "fed_funds_rate.csv", DATA / "hairs.csv",
              DATA / "nber_recessions.csv"):
        if not p.exists():
            die(f"missing input: {p.relative_to(ROOT)}")

    meta, sections = split_qmd(QMD)
    for name in KNOWN:
        if name not in sections:
            die(f'{QMD.name} has no "## {name}" section (found: {", ".join(sections) or "none"})')
    unknown = [n for n in sections if n not in KNOWN]
    if unknown:
        die(f'{QMD.name} has "## " sections build.py does not use: {"; ".join(unknown)}. '
            f'Known: {"; ".join(KNOWN)}')
    for key in ("title", "subtitle"):
        if not meta.get(key):
            die(f"{QMD.name} front matter has no {key}")

    rate = build_rate()
    flat, counts = build_hairs()
    spells = build_recessions()
    payload = {
        "rate": rate,
        "drawOrder": DRAW_ORDER,
        "target": TARGET,
        "recessions": {**RECESSIONS, "spells": spells},
        "series": [{**s, "h": flat[s["key"]]} for s in SERIES],
    }
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")

    notes = md(sections[NOTES])
    for key in [s["key"] for s in SERIES] + ["target", "recessions"]:
        if f'data-series="{key}"' not in notes:
            print(f"  warning: Notes has no callout for {key}")

    legend = "\n".join(
        f'      <button type="button" class="ha-chip" data-s="{s["key"]}" aria-pressed="true" '
        f'style="--c:{s["color"]}"><span class="ha-box" aria-hidden="true"></span>'
        f'<span class="ha-name">{esc(s["label"])}</span></button>'
        for s in SERIES)
    legend += ('\n      <button type="button" class="ha-chip" data-rec aria-pressed="false">'
               '<span class="ha-box" aria-hidden="true"></span>'
               f'<span class="ha-name">{esc(RECESSIONS["label"])}</span></button>')
    series_css = "\n".join(
        f'#hairy-app .ha-callout[data-series="{s["key"]}"]{{--c:{s["color"]}}}'
        for s in SERIES) + (f'\n#hairy-app .ha-callout[data-series="target"]{{--c:{TARGET["color"]}}}'
                            '\n#hairy-app .ha-callout[data-series="recessions"]{--c:#9AA6B5}')

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    page = TEMPLATE.read_text(encoding="utf-8")
    for token, value in (("__SERIES_CSS__", series_css),
                         ("__TITLE__", esc(meta["title"])),
                         ("__SUBTITLE__", esc(meta["subtitle"])),
                         ("__LEGEND__", legend),
                         ("__NOTES__", notes),
                         ("__BUILD__", stamp),
                         ("__DATA__", data)):
        if token not in page:
            die(f"template.html has no {token} placeholder")
        page = page.replace(token, value, 1)
    leftover = sorted(set(re.findall(r"__[A-Z_]+__", page)))
    if leftover:
        die(f"unfilled placeholders: {', '.join(leftover)}")

    fragment = ("<!-- Generated by interactive/_app/build.py from template.html, text.qmd "
                "and data/. Do not edit: the next build overwrites it. -->\n" + page)
    FRAGMENT.write_text(fragment, encoding="utf-8")

    # The preview page imitates the site's article column: about 800px wide on
    # a white page. Quarto adds the real page around the fragment.
    preview = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(meta["title"])} (preview)</title>
<style>body{{margin:0;background:#fff;padding:24px 16px 60px}}
.page{{max-width:800px;margin:0 auto}}</style>
</head>
<body>
<div class="page">
{fragment}
</div>
</body>
</html>
"""
    PREVIEW.write_text(preview, encoding="utf-8")

    check_sources_md()
    kb = len(fragment.encode("utf-8")) / 1024
    print(f"wrote {FRAGMENT.relative_to(ROOT)}  {kb:.0f} KB (data {len(data) / 1024:.0f} KB)")
    print(f"wrote {PREVIEW.relative_to(ROOT)}")
    print(f"  target: {len(rate['c'])} change points to {EPOCH + dt.timedelta(days=rate['end'])}")
    print(f"  recessions: {len(spells)}, the latest from "
          f"{EPOCH + dt.timedelta(days=spells[-1][0])} to {EPOCH + dt.timedelta(days=spells[-1][1])}")
    for s in SERIES:
        n_h, n_p = counts[s["key"]]
        print(f"  {s['key']:18s} {n_h:>4} hairs  {n_p:>6,} points")


if __name__ == "__main__":
    main()
