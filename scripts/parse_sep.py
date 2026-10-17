"""Pull the median fed funds projection out of each SEP projection table.

One PDF per FOMC meeting. Each yields one hair: as of the meeting date, the
median participant's projected fed funds rate at the end of each of the next
few calendar years, plus the longer-run value.

Two layout facts make this awkward. pdfplumber strips the spaces out of the
row labels in some vintages, so "Federal funds rate" arrives as
"Federalfundsrate". And the number of projection years changes over time, so
the year headers have to be read off the table rather than assumed.

The median column was only introduced with the September 2015 SEP. Earlier
tables carry the central tendency and range but no median, and the individual
dots live in a figure rather than in text, so those meetings come out empty.

Writes out/sep_medians.csv, tidy: one row per (meeting, projection year).
"""

import re
import sys
import warnings
from pathlib import Path

import pandas as pd
import pdfplumber

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw-data" / "sep"
OUT = ROOT / "out"

NUM = re.compile(r"^\d+\.\d$")


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def find_years(text: str) -> list[str]:
    """Projection years from the table header, in order, stopping at the repeat.

    The header lists the years once per statistic block (median, central
    tendency, range), so the first run before a repeat is the year list. Some
    vintages wrap the header, leaving "Variable" and "Longer" on one line and
    the years on the line above or below, so a failed line is retried against
    its neighbours joined together.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "Variable" not in line:
            continue
        for candidate in (
            line,
            " ".join(lines[max(0, i - 1): i + 2]),
            " ".join(lines[max(0, i - 2): i + 3]),
        ):
            years = re.findall(r"\b(20\d\d)\b", candidate)
            seen: list[str] = []
            for y in years:
                if y in seen:
                    break
                seen.append(y)
            if len(seen) >= 2:
                return seen
    return []


def median_row(text: str) -> list[float]:
    """The leading run of plain decimals on the fed funds row.

    Central tendency and range follow the medians on the same row but are
    written as en-dash ranges, so the first non-decimal token ends the run.
    Prose mentioning the fed funds rate is rejected by requiring at least
    three numbers.
    """
    for line in text.split("\n"):
        if not squash(line).lower().startswith("federalfundsrate"):
            continue
        vals: list[float] = []
        for t in line.split():
            if NUM.match(t):
                vals.append(float(t))
            elif vals:
                break
        if len(vals) >= 3:
            return vals
    return []


def parse_one(path: Path) -> tuple[list[str], list[float]]:
    """Best candidate across all pages. Never stops at the first page that
    merely mentions the fed funds rate, because the intro page always does."""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "fundsrate" not in squash(text).lower():
                continue
            vals = median_row(text)
            if not vals:
                continue
            years = find_years(text)
            if not years:
                continue
            # Years plus longer run. If the row is short, the table has no
            # longer-run median and the years themselves are all there is.
            want = min(len(years) + 1, len(vals))
            return years[: want - 1], vals[:want]
    return [], []


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    empty = []
    for path in sorted(SRC.glob("*.pdf")):
        meeting = pd.to_datetime(path.stem[-8:], format="%Y%m%d")
        years, vals = parse_one(path)
        if not vals:
            empty.append(meeting.strftime("%Y-%m-%d"))
            continue
        for y, v in zip(years, vals[:-1]):
            rows.append(
                {
                    "meeting_date": meeting,
                    "projection_year": int(y),
                    "horizon": "year_end",
                    "median_ffr": v,
                }
            )
        rows.append(
            {
                "meeting_date": meeting,
                "projection_year": pd.NA,
                "horizon": "longer_run",
                "median_ffr": vals[-1],
            }
        )

    df = pd.DataFrame(rows)
    path = OUT / "sep_medians.csv"
    df.to_csv(path, index=False)

    got = df["meeting_date"].nunique()
    print(f"parsed {got} meetings, {len(df):,} rows -> {path.name}")
    if got:
        print(f"  {df['meeting_date'].min():%Y-%m-%d} to "
              f"{df['meeting_date'].max():%Y-%m-%d}")
    print(f"\n{len(empty)} meetings with no median in the table "
          f"(expected for pre-September 2015):")
    print("  " + ", ".join(empty))

    if got:
        last = df[df["meeting_date"] == df["meeting_date"].max()]
        print(f"\nmost recent hair, {last['meeting_date'].iloc[0]:%Y-%m-%d}:")
        for _, r in last.iterrows():
            label = (
                f"{int(r['projection_year'])}"
                if pd.notna(r["projection_year"])
                else "longer run"
            )
            print(f"  {label:>10s}  {r['median_ffr']:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
