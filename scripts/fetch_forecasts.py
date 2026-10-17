"""Download the forecast-based hair sources.

Three of them, none needing a key:

  SEP   the FOMC's own projection tables, one PDF per meeting from 2012. The
        meeting dates come from FEDTARMDLR in the FRED pull, so the calendar
        does not have to be scraped.
  SPF   Philadelphia Fed Survey of Professional Forecasters, median 3-month
        Treasury bill level. Quarterly back to 1981, the only survey that
        covers the late-1990s window.
  ACM   NY Fed Adrian-Crump-Moench term premium, needed to strip the term
        premium out of the Treasury forward curve.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw-data"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

SEP_URL = "https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl{d}.pdf"
SPF_URL = (
    "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/"
    "survey-of-professional-forecasters/data-files/files/median_tbill_level.xlsx"
)
ACM_URL = (
    "https://www.newyorkfed.org/medialibrary/media/research/"
    "data_indicators/ACMTermPremium.xls"
)


def get(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        r = requests.get(url, headers=UA, timeout=120)
        r.raise_for_status()
        if len(r.content) < 1000:
            print(f"  too small ({len(r.content)}b) {url}")
            return False
        dest.write_bytes(r.content)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {type(exc).__name__} {url}")
        return False


def sep_dates() -> list[str]:
    """SEP meeting dates, taken from the longer-run median dot series."""
    df = pd.read_csv(RAW / "fred" / "sep_latest.csv", parse_dates=["date"])
    dates = df.loc[df["FEDTARMDLR"].notna(), "date"]
    return [d.strftime("%Y%m%d") for d in dates]


def main() -> int:
    (RAW / "sep").mkdir(parents=True, exist_ok=True)
    (RAW / "spf").mkdir(parents=True, exist_ok=True)
    (RAW / "nyfed").mkdir(parents=True, exist_ok=True)

    dates = sep_dates()
    print(f"SEP: {len(dates)} meeting dates, {dates[0]} to {dates[-1]}")
    got = 0
    for d in dates:
        dest = RAW / "sep" / f"fomcprojtabl{d}.pdf"
        if get(SEP_URL.format(d=d), dest):
            got += 1
        else:
            print(f"  missing {d}")
        time.sleep(0.3)
    print(f"SEP: {got}/{len(dates)} downloaded\n")

    print("SPF median 3-month T-bill")
    ok_spf = get(SPF_URL, RAW / "spf" / "median_tbill_level.xlsx")
    print(f"  {'ok' if ok_spf else 'FAILED'}\n")

    print("NY Fed ACM term premium")
    ok_acm = get(ACM_URL, RAW / "nyfed" / "ACMTermPremium.xls")
    print(f"  {'ok' if ok_acm else 'FAILED'}")

    return 0 if (got == len(dates) and ok_spf and ok_acm) else 1


if __name__ == "__main__":
    sys.exit(main())
