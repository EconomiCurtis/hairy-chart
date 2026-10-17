"""Assemble the trunk and every hair source into two tidy tables.

Everything the notebooks and the interactive page read comes from here, so the
plotting code never touches raw-data/ and never has to know how a given source
was shaped.

  data/fed_funds_rate.csv   one row per day: the policy rate, in several forms
  data/hairs.csv            one row per (source, as_of, target_date): an
                            expected rate

Four hair sources, deliberately kept in one table with a `source` column so a
plot can color by it:

  treasury_forward  Treasury forward curve from the GSW Svensson parameters.
                    Daily since 1961, sampled here at FOMC meetings. Smooth by
                    construction, see SOURCES.md.
  options_implied   Atlanta Fed Market Probability Tracker, the mean of the
                    distribution implied by CME options on 3-month SOFR. 2023
                    onward only, but genuinely market-implied.
  sep_median        Median FOMC participant's projection, year-end values,
                    September 2015 onward.
  spf_median        Philadelphia Fed Survey of Professional Forecasters, median
                    3-month Treasury bill, current quarter to four quarters
                    ahead, back to the 1980s.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw-data"
OUT = ROOT / "out"    # intermediate files from parse_sep.py, build_gsw_hairs.py
DATA = ROOT / "data"  # what the notebooks read

HAIR_MONTHS = 36


def build_trunk() -> pd.DataFrame:
    pol = pd.read_csv(RAW / "fred" / "policy_rate_daily.csv", parse_dates=["date"])
    pol = pol.sort_values("date").reset_index(drop=True)

    t = pd.DataFrame({"date": pol["date"]})
    t["effr"] = pol["DFF"]
    # The daily effective rate spikes hard on month, quarter and year ends in
    # the pre-2008 regime, when the Fed hit its target through open market
    # operations rather than a floor system. Those spikes are real, not bad
    # data, but they swamp the trunk in the 1990s. JPMorgan's version of this
    # chart plots a 1-month moving average for exactly this reason.
    t["effr_ma1m"] = (
        pol.set_index("date")["DFF"].rolling("30D", min_periods=10).mean().to_numpy()
    )
    t["target_lo"] = pol["DFEDTARL"].fillna(pol["DFEDTAR"])
    t["target_hi"] = pol["DFEDTARU"].fillna(pol["DFEDTAR"])
    t["target_mid"] = (t["target_lo"] + t["target_hi"]) / 2
    return t


def hairs_treasury(meetings: pd.Series) -> pd.DataFrame:
    fw = pd.read_parquet(OUT / "gsw_forward_curves.parquet")
    fw = fw[fw["horizon_months"] <= HAIR_MONTHS]

    # A meeting date is not always a curve date (holidays, and the file lags a
    # few days). Snap each meeting to the last curve date at or before it.
    curve_dates = np.sort(fw["as_of"].unique())
    idx = np.searchsorted(curve_dates, meetings.to_numpy(), side="right") - 1
    ok = idx >= 0
    snap = pd.DataFrame(
        {"meeting_date": meetings.to_numpy()[ok], "as_of": curve_dates[idx[ok]]}
    )
    # Do not snap backwards by more than a week; that would be a different world.
    gap = (snap["meeting_date"] - snap["as_of"]).dt.days
    snap = snap[gap.between(0, 7)]

    out = fw.merge(snap, on="as_of", how="inner")
    return pd.DataFrame(
        {
            "source": "treasury_forward",
            "as_of": out["meeting_date"],
            "target_date": out["target_date"],
            "horizon_months": out["horizon_months"],
            "rate_pct": out["fwd_pct"],
        }
    )


def hairs_options() -> pd.DataFrame:
    d = pd.read_excel(RAW / "atlantafed" / "mpt_histdata.xlsx", sheet_name="DATA")
    d = d[d["field"] == "Rate: mean"].copy()
    d["as_of"] = pd.to_datetime(d["date"])
    # The reference window is three months long, so its midpoint is the date
    # the implied rate really speaks to.
    d["target_date"] = pd.to_datetime(d["reference_start"]) + pd.Timedelta(days=45)
    d["rate_pct"] = d["value"] / 100.0  # basis points to per cent
    d["horizon_months"] = (
        (d["target_date"] - d["as_of"]).dt.days / 30.4375
    ).round().astype(int)
    d = d[d["horizon_months"].between(0, HAIR_MONTHS)]
    return d[["as_of", "target_date", "horizon_months", "rate_pct"]].assign(
        source="options_implied"
    )


def hairs_sep() -> pd.DataFrame:
    s = pd.read_csv(OUT / "sep_medians.csv", parse_dates=["meeting_date"])
    s = s[s["horizon"] == "year_end"].copy()
    s["target_date"] = pd.to_datetime(
        s["projection_year"].astype(int).astype(str) + "-12-31"
    )
    s["horizon_months"] = (
        (s["target_date"] - s["meeting_date"]).dt.days / 30.4375
    ).round().astype(int)
    s = s[s["horizon_months"] >= 0]
    return pd.DataFrame(
        {
            "source": "sep_median",
            "as_of": s["meeting_date"],
            "target_date": s["target_date"],
            "horizon_months": s["horizon_months"],
            "rate_pct": s["median_ffr"],
        }
    )


def hairs_spf() -> pd.DataFrame:
    df = pd.read_excel(RAW / "spf" / "median_tbill_level.xlsx", sheet_name="Median_Level")
    cols = [f"TBILL{i}" for i in range(1, 7)]
    df = df.dropna(subset=cols, how="all")
    rows = []
    for _, r in df.iterrows():
        # Responses are due in the middle of the second month of the quarter:
        # mid-February, mid-May, mid-August, mid-November. That deadline, not
        # the mailing date, is when the forecaster's information set closes.
        as_of = pd.Timestamp(year=int(r["YEAR"]), month=int(r["QUARTER"]) * 3 - 1, day=15)
        for k, c in enumerate(cols):
            if pd.isna(r[c]):
                continue
            # The Philadelphia Fed numbers these from the quarter BEFORE the
            # survey: TBILL1 is the quarter already past, whose value the
            # forecasters already know, TBILL2 is the current quarter, and
            # TBILL3 to TBILL6 are the four quarters after it. So k=0 is not a
            # forecast at all and is dropped, and the real horizons run 0 to
            # +4 quarters.
            offset_q = k - 1
            if offset_q < 0:
                continue
            target = as_of + pd.DateOffset(months=3 * offset_q)
            rows.append(
                {
                    "source": "spf_median",
                    "as_of": as_of,
                    "target_date": target,
                    "horizon_months": 3 * offset_q,
                    "rate_pct": float(r[c]),
                }
            )
    return pd.DataFrame(rows)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)

    trunk = build_trunk()
    trunk.to_csv(DATA / "fed_funds_rate.csv", index=False)
    print(f"fed_funds_rate.csv  {len(trunk):,} days, "
          f"{trunk['date'].min():%Y-%m-%d} to {trunk['date'].max():%Y-%m-%d}")

    fomc = pd.read_csv(RAW / "fomc" / "fomc_meetings.csv", parse_dates=["meeting_date"])
    meetings = fomc.loc[fomc["is_scheduled"], "meeting_date"]

    parts = []
    for name, fn in [
        ("treasury_forward", lambda: hairs_treasury(meetings)),
        ("options_implied", hairs_options),
        ("sep_median", hairs_sep),
        ("spf_median", hairs_spf),
    ]:
        try:
            p = fn()
            parts.append(p)
            print(f"  {name:18s} {len(p):>8,} points, "
                  f"{p['as_of'].nunique():>4} hairs, "
                  f"{p['as_of'].min():%Y-%m} to {p['as_of'].max():%Y-%m}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {name:18s} FAILED {type(exc).__name__}: {exc}")

    hairs = pd.concat(parts, ignore_index=True)
    hairs = hairs[
        ["source", "as_of", "target_date", "horizon_months", "rate_pct"]
    ].sort_values(["source", "as_of", "horizon_months"])
    hairs.to_csv(DATA / "hairs.csv", index=False)

    print(f"\nhairs.csv  {len(hairs):,} points, "
          f"{hairs['as_of'].nunique():,} distinct hair dates, "
          f"{hairs['source'].nunique()} sources")

    # Sanity: a hair should start near the policy rate it branches off.
    print("\nsanity, front of hair vs trunk on the same day:")
    tr = trunk.set_index("date")["effr_ma1m"]
    for src, g in hairs.groupby("source"):
        front = g.sort_values("horizon_months").groupby("as_of").first()
        j = front.join(tr.rename("trunk"), how="inner").dropna()
        if len(j):
            d = j["rate_pct"] - j["trunk"]
            print(f"  {src:18s} n={len(j):>4}  mean gap {d.mean():+.2f}pp  "
                  f"sd {d.std():.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
