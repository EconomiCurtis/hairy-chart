"""Treasury forward hairs out to 120 months, for the hair-length comparison.

hairs.csv caps the Treasury forward hairs at 36 months for legibility. This
writes the same hairs uncapped to 120 months, so the notebook can show what
longer hairs would look like. Sampling matches build_dataset.py: scheduled
FOMC meetings, each snapped to the last curve date at or before it, and never
more than a week back. The first 36 months therefore match hairs.csv.

The curve is evaluated straight from the Svensson parameters, as in
build_gsw_hairs.py, because the parquet that script writes stops at 60 months.

Writes data/treasury_forward_120m.csv.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw-data"
DATA = ROOT / "data"

MAX_MONTHS = 120


def main() -> int:
    g = pd.read_csv(RAW / "gsw" / "feds200628.csv", skiprows=9, low_memory=False)
    g["Date"] = pd.to_datetime(g["Date"])
    for c in ("BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    # Pre-1980 rows are Nelson-Siegel; zeroing BETA3 collapses Svensson to it.
    g["BETA3"] = g["BETA3"].fillna(0.0)
    g["TAU2"] = g["TAU2"].fillna(1.0)
    g = g.dropna(subset=["BETA0", "BETA1", "BETA2", "TAU1"]).sort_values("Date")

    m = pd.read_csv(RAW / "fomc" / "fomc_meetings.csv", parse_dates=["meeting_date"])
    meetings = m.loc[m["is_scheduled"], "meeting_date"].sort_values().to_numpy()

    curve_dates = g["Date"].to_numpy()
    idx = np.searchsorted(curve_dates, meetings, side="right") - 1
    ok = idx >= 0
    snap = pd.DataFrame({"meeting": meetings[ok], "Date": curve_dates[idx[ok]]})
    snap = snap[(snap["meeting"] - snap["Date"]).dt.days.between(0, 7)]
    p = snap.merge(g, on="Date")

    frames = []
    for months in range(1, MAX_MONTHS + 1):
        n = months / 12.0
        x1, x2 = n / p["TAU1"], n / p["TAU2"]
        f = (p["BETA0"] + p["BETA1"] * np.exp(-x1) + p["BETA2"] * x1 * np.exp(-x1)
             + p["BETA3"] * x2 * np.exp(-x2))
        frames.append(pd.DataFrame({
            "as_of": p["meeting"].dt.date,
            "target_date": (p["meeting"] + pd.to_timedelta(months * 30.4375, unit="D")).dt.date,
            "horizon_months": months,
            # Continuous to annual compounding, as in build_gsw_hairs.py.
            "rate_pct": ((np.exp(f / 100.0) - 1.0) * 100.0).round(4),
        }))
    d = pd.concat(frames, ignore_index=True).sort_values(["as_of", "horizon_months"])

    path = OUT / "treasury_forward_120m.csv"
    d.to_csv(path, index=False)
    print(f"wrote {path.name}: {d['as_of'].nunique()} hairs, "
          f"{len(d):,} rows, horizons 1 to {MAX_MONTHS} months")
    return 0


if __name__ == "__main__":
    sys.exit(main())
