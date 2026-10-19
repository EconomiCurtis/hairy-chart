"""Turn the GSW Svensson parameters into one forward curve per day.

The published feds200628.csv carries instantaneous forward rates only at whole
years (SVENF01 up), but it also carries the six Svensson parameters, and those
let us evaluate the curve at any horizon. The hairy chart needs the first three
years at monthly resolution, which is exactly the part the published columns
skip, so we recompute from the parameters and check ourselves against the
published columns where they overlap.

Svensson instantaneous forward, continuously compounded, horizon n in years:

    f(n) = b0 + b1*exp(-n/t1) + b2*(n/t1)*exp(-n/t1) + b3*(n/t2)*exp(-n/t2)

Writes out/gsw_forward_curves.parquet, tidy: one row per (as_of, horizon).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw-data" / "gsw" / "feds200628.csv"
OUT = ROOT / "out"

# Horizon grid, in years: monthly out to 5 years. Monthly matches the tenor of
# the fed funds futures contract this is standing in for.
HORIZONS = np.arange(1, 61) / 12.0

# The header sits under a nine-line preamble.
SKIPROWS = 9


def svensson_forward(p: pd.DataFrame, n: float) -> np.ndarray:
    """Instantaneous forward rate at horizon n years, continuously compounded."""
    x1 = n / p["TAU1"].to_numpy()
    x2 = n / p["TAU2"].to_numpy()
    return (
        p["BETA0"].to_numpy()
        + p["BETA1"].to_numpy() * np.exp(-x1)
        + p["BETA2"].to_numpy() * x1 * np.exp(-x1)
        + p["BETA3"].to_numpy() * x2 * np.exp(-x2)
    )


def load() -> pd.DataFrame:
    df = pd.read_csv(SRC, skiprows=SKIPROWS, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])
    # BETA3 and TAU2 are absent for the early years, when a four-parameter
    # Nelson-Siegel was fitted instead of the six-parameter Svensson. Zeroing
    # them collapses the formula to Nelson-Siegel, which is the right thing.
    for col in ("BETA3", "TAU2"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["BETA3"] = df["BETA3"].fillna(0.0)
    df["TAU2"] = df["TAU2"].fillna(1.0)
    for col in ("BETA0", "BETA1", "BETA2", "TAU1"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["BETA0", "BETA1", "BETA2", "TAU1"])


def validate(df: pd.DataFrame) -> None:
    """Recompute the published whole-year forwards and compare."""
    print("validation: recomputed vs published instantaneous forwards")
    worst = 0.0
    for yr in (1, 2, 5, 10):
        col = f"SVENF{yr:02d}"
        published = pd.to_numeric(df[col], errors="coerce").to_numpy()
        recomputed = svensson_forward(df, float(yr))
        ok = ~np.isnan(published)
        diff = np.abs(published[ok] - recomputed[ok])
        worst = max(worst, float(diff.max()))
        print(
            f"  {col}: n={ok.sum():>6,}  "
            f"max diff {diff.max():.6f}  mean diff {diff.mean():.8f}"
        )
    if worst > 1e-3:
        raise SystemExit(f"validation failed, max diff {worst:.6f} exceeds 1e-3")
    print(f"  all within 1e-3 (worst {worst:.6f})\n")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    print(f"loaded {len(df):,} curve-days, "
          f"{df['Date'].min():%Y-%m-%d} to {df['Date'].max():%Y-%m-%d}\n")

    validate(df)

    frames = []
    for n in HORIZONS:
        f = svensson_forward(df, float(n))
        frames.append(
            pd.DataFrame(
                {
                    "as_of": df["Date"].to_numpy(),
                    "horizon_months": int(round(n * 12)),
                    # Left continuously compounded. Fed funds is an overnight
                    # rate quoted as simple interest, which continuous
                    # compounding is close to; annual compounding would lift
                    # the hairs, by about 0.13 points at a 5% rate.
                    "fwd_pct": f,
                }
            )
        )
    tidy = pd.concat(frames, ignore_index=True)

    # The date each forward rate refers to, which is the hairy chart's x-axis.
    tidy["target_date"] = tidy["as_of"] + pd.to_timedelta(
        tidy["horizon_months"] * 30.4375, unit="D"
    )
    tidy = tidy.sort_values(["as_of", "horizon_months"]).reset_index(drop=True)

    path = OUT / "gsw_forward_curves.parquet"
    tidy.to_parquet(path, index=False)
    size = path.stat().st_size / 1e6
    print(f"wrote {path.name}: {len(tidy):,} rows, {size:.1f} MB")
    print(f"  as_of  {tidy['as_of'].min():%Y-%m-%d} to {tidy['as_of'].max():%Y-%m-%d}")
    print(f"  horizons {tidy['horizon_months'].min()} to "
          f"{tidy['horizon_months'].max()} months")

    # A quick look at one curve, to eyeball that it is shaped like a curve.
    sample = tidy[tidy["as_of"] == "2023-01-03"]
    if len(sample):
        pick = sample[sample["horizon_months"].isin([1, 6, 12, 24, 36, 60])]
        print("\n  sample curve, 2023-01-03:")
        for _, r in pick.iterrows():
            print(f"    {r['horizon_months']:>3d}m  {r['fwd_pct']:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
