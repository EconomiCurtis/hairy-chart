"""Download the fed funds trunk series from FRED.

Uses the keyless fredgraph.csv endpoint, so no API key is needed. Writes one
tidy CSV per group into raw-data/fred/.
"""

import io
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "raw-data" / "fred"

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# Each group becomes one CSV. Series inside a group share an observation index.
GROUPS = {
    # The trunk. DFF is the effective rate back to 1954; DFEDTAR is the single
    # target through Dec 2008; DFEDTARU/L are the target range after that.
    "policy_rate_daily": ["DFF", "DFEDTAR", "DFEDTARU", "DFEDTARL"],
    "policy_rate_monthly": ["FEDFUNDS"],
    # Overnight rates that succeeded or sit alongside fed funds.
    "overnight_other": ["SOFR", "IORB", "OBFR"],
    # Treasury constant-maturity yields, for validating the GSW forward curve
    # and for the short end the hairs start from.
    "treasury_cmt": [
        "DGS1MO", "DGS3MO", "DGS6MO", "DGS1",
        "DGS2", "DGS3", "DGS5", "DGS7", "DGS10",
    ],
    "tbill_secondary": ["DTB3", "DTB6", "DTB1YR"],
    # The FOMC's own projections, latest vintage only. Historical vintages come
    # from the SEP PDFs instead: ALFRED is not reachable from here.
    "sep_latest": ["FEDTARMD", "FEDTARMDLR"],
}


def fetch_one(series_id: str, cosd: str) -> pd.DataFrame:
    """One series at a time. Asking for several at mixed frequencies makes FRED
    return a zip of per-frequency CSVs instead of a single CSV."""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    r = requests.get(
        url, params={"id": series_id, "cosd": cosd}, headers=UA, timeout=90
    )
    r.raise_for_status()
    if r.content[:2] == b"PK":
        raise ValueError(f"{series_id}: FRED returned a zip, not a CSV")
    df = pd.read_csv(io.StringIO(r.text))
    df = df.rename(columns={df.columns[0]: "date"})
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch(series: list[str], cosd: str = "1954-01-01") -> pd.DataFrame:
    out = None
    for sid in series:
        df = fetch_one(sid, cosd)
        out = df if out is None else out.merge(df, on="date", how="outer")
        time.sleep(0.5)
    return out.sort_values("date").reset_index(drop=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    failures = []
    for name, series in GROUPS.items():
        # SEP observations are projection years, so no start-date filter.
        cosd = "1900-01-01" if name.startswith("sep") else "1954-01-01"
        try:
            df = fetch(series, cosd=cosd)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            failures.append(name)
            continue
        path = OUT / f"{name}.csv"
        df.to_csv(path, index=False)
        span = f"{df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}"
        print(f"ok   {name:22s} {len(df):>7,} rows  {span}  -> {path.name}")
        time.sleep(1)

    if failures:
        print(f"\n{len(failures)} group(s) failed: {', '.join(failures)}")
        return 1
    print("\nall FRED groups downloaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
