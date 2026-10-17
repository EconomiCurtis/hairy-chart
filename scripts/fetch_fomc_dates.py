"""Scrape FOMC meeting dates from the Fed's own calendar pages.

The hairs are drawn one per FOMC meeting, so the calendar is load-bearing
rather than decorative. Two page layouts: fomchistorical{YYYY}.htm for older
years, and fomccalendars.htm for the current handful.

Both carry links of the form monetary{YYYYMMDD}a.htm, which point at the
statement issued at the end of a meeting. That date is the one we want, since
a hair should be drawn from the moment the decision was public. Meetings with
no statement link fall back to the "Month D-D Meeting" heading text, which
gives the meeting's own dates.

Writes raw-data/fomc/fomc_meetings.csv.
"""

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "raw-data" / "fomc"
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
}

FIRST_YEAR = 1994  # statements only start being issued in 1994
CURRENT_PAGE = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
HIST_PAGE = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm"

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "January February March April May June July August September "
        "October November December".split()
    )
}


def get(url: str) -> str | None:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.text
        except Exception:  # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    print(f"  giving up on {url}")
    return None


def statement_dates(html: str) -> set[pd.Timestamp]:
    """Dates from monetary{YYYYMMDD}a.htm statement links."""
    out = set()
    for m in re.finditer(r"monetary(\d{8})a1?\.htm", html):
        try:
            out.add(pd.to_datetime(m.group(1), format="%Y%m%d"))
        except ValueError:
            continue
    return out


def heading_dates(html: str, year: int) -> set[pd.Timestamp]:
    """Dates from "January 30-31 Meeting" style headings.

    Takes the last day of a two-day meeting, to match the statement date.
    Handles meetings that straddle a month boundary.
    """
    out = set()
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    pat = (
        r"([A-Z][a-z]+)\s+(\d{1,2})(?:\s*-\s*(?:([A-Z][a-z]+)\s+)?(\d{1,2}))?"
        r"\s+Meeting"
    )
    for m in re.finditer(pat, text):
        m1, d1, m2, d2 = m.groups()
        if m1 not in MONTHS:
            continue
        month = MONTHS[m2] if m2 in MONTHS else MONTHS[m1]
        day = int(d2) if d2 else int(d1)
        try:
            out.add(pd.Timestamp(year=year, month=month, day=day))
        except ValueError:
            continue
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    this_year = pd.Timestamp.today().year

    found: dict[pd.Timestamp, str] = {}

    html = get(CURRENT_PAGE)
    if html:
        for d in statement_dates(html):
            found[d] = "statement_link"
        print(f"current calendar page: {len(found)} statement dates")

    for year in range(FIRST_YEAR, this_year + 1):
        html = get(HIST_PAGE.format(y=year))
        if html is None:
            continue
        s = statement_dates(html)
        h = heading_dates(html, year)
        # Prefer statement dates, fill gaps with headings.
        n_new = 0
        for d in s:
            if d not in found:
                found[d] = "statement_link"
                n_new += 1
        for d in h:
            if d not in found:
                found[d] = "meeting_heading"
                n_new += 1
        print(f"  {year}: {len(s)} statement, {len(h)} heading, {n_new} new")
        time.sleep(0.4)

    df = pd.DataFrame(
        {"meeting_date": sorted(found), "source": [found[d] for d in sorted(found)]}
    )
    # Statement links include non-meeting announcements. Real meetings are
    # spaced at least three weeks apart, so drop anything that crowds the
    # previous kept date.
    keep = []
    last = None
    for _, r in df.iterrows():
        if last is None or (r["meeting_date"] - last).days >= 21:
            keep.append(True)
            last = r["meeting_date"]
        else:
            keep.append(False)
    df["is_scheduled"] = keep

    path = OUT / "fomc_meetings.csv"
    df.to_csv(path, index=False)
    sched = df[df["is_scheduled"]]
    print(f"\nwrote {path.name}: {len(df)} dates, {len(sched)} scheduled")
    print(f"  {df['meeting_date'].min():%Y-%m-%d} to {df['meeting_date'].max():%Y-%m-%d}")
    per_year = sched.groupby(sched["meeting_date"].dt.year).size()
    odd = per_year[(per_year < 7) | (per_year > 9)]
    print(f"  scheduled meetings per year: median {per_year.median():.0f}")
    if len(odd):
        print(f"  years outside 7-9 meetings (check these): {dict(odd)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
