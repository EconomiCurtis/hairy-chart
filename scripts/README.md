# Getting the data

Where each source lives and how to rebuild `data/` from it. For what the numbers mean, who produces them and the caveats, see [misc/SOURCES.md](../misc/SOURCES.md).

Rendering the notebooks does not need any of this: `data/` is committed. Everything below downloads with no account, no API key and no payment. Downloads land in `raw-data/` and intermediate files in `out/`, about 100 MB together, and neither is committed.

## Rebuilding, from the repository root

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
```

Two files are downloaded by hand, once, because their servers refuse repeated scripted pulls:

```bash
mkdir -p raw-data/gsw raw-data/atlantafed
curl -L -A "Mozilla/5.0" https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv -o raw-data/gsw/feds200628.csv
curl -L -A "Mozilla/5.0" https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/market-probability-tracker/mpt_histdata.xlsx -o raw-data/atlantafed/mpt_histdata.xlsx
```

A plain `curl` with no user agent returns zero bytes from both. Then run the pipeline in order:

```bash
.venv/bin/python scripts/fetch_fred.py
.venv/bin/python scripts/fetch_forecasts.py
.venv/bin/python scripts/fetch_fomc_dates.py
.venv/bin/python scripts/parse_sep.py
.venv/bin/python scripts/build_gsw_hairs.py
.venv/bin/python scripts/build_dataset.py
.venv/bin/python scripts/build_long_hairs.py
```

The last two write everything in `data/`: `fed_funds_rate.csv`, `hairs.csv` and `treasury_forward_120m.csv`, which the notebooks read, and `nber_recessions.csv`, which only the interactive uses.

## 1. FRED, the policy rate and Treasury yields

`fetch_fred.py`, into `raw-data/fred/`. Uses the keyless `fredgraph.csv` endpoint, so no API key is involved.

Asking `fredgraph.csv` for several series at once returns a zip of per-frequency CSVs rather than a CSV whenever the series have different frequencies. The fetcher pulls one series at a time and merges, which sidesteps it.

| series | what | from |
|---|---|---|
| `DFEDTAR` | target rate, single value | 1982 to 2008 |
| `DFEDTARU`, `DFEDTARL` | target range, upper and lower | 2008 |
| `SOFR`, `IORB`, `OBFR` | the rates that now sit around fed funds | 2016 |
| `DGS1MO` to `DGS10` | Treasury constant maturity yields | 1962 |
| `DTB3`, `DTB6`, `DTB1YR` | Treasury bill secondary market | 1954 |
| `FEDTARMD`, `FEDTARMDLR` | FOMC median projection, latest vintage only | 2012 |
| `USREC` | NBER recession indicator, monthly | 1854 |

`USREC` is 1 in each month from the one after a business cycle peak through the trough. `build_dataset.py` turns each run of 1s back into a peak and a trough month, one row per recession in `data/nber_recessions.csv`, which match FRED's own list of recession-bar dates.

`FEDTARMDLR` does double duty. Its observation dates are the 59 FOMC meetings that produced a Summary of Economic Projections, which is how `fetch_forecasts.py` knows which SEP PDFs to ask for without scraping a calendar.

## 2. Federal Reserve Board, the Treasury yield curve (GSW)

The Gürkaynak, Sack and Wright fitted Treasury curve, <https://www.federalreserve.gov/data/nominal-yield-curve.htm>. Daily since June 1961, updated weekly, about 16 MB. Downloaded by hand, above.

What matters is not the published `SVENF01` to `SVENF30` forward columns, which only give whole years, but the six Svensson parameters `BETA0` to `BETA3`, `TAU1` and `TAU2` at the end of every row. `build_gsw_hairs.py` uses them to evaluate the forward curve at any horizon, including the sub-one-year part the published columns skip. It checks itself by recomputing the published whole-year forwards: the worst disagreement across 16,000 days is under 0.001 percentage points, which is rounding in the published file.

Before 1980 the Board fitted a four-parameter curve (Nelson-Siegel) rather than six (Svensson), so those rows leave `BETA3` and `TAU2` blank. Setting `BETA3` to 0 reduces the six-parameter formula to the four-parameter one.

## 3. FOMC meeting dates

`fetch_fomc_dates.py`, into `raw-data/fomc/`. Scrapes `fomchistorical{YYYY}.htm` for older years and `fomccalendars.htm` for current ones.

Prefers the `monetary{YYYYMMDD}a.htm` statement links, since a hair should start the moment a decision became public, and falls back to "January 30-31 Meeting" heading text for years before statements were issued. 269 dates from February 1994, a median of eight scheduled meetings a year.

federalreserve.gov intermittently drops connections when hit repeatedly. The fetcher retries three times with a backoff. If a year comes back empty, run it again.

## 4. FOMC Summary of Economic Projections

`fetch_forecasts.py` downloads, `parse_sep.py` extracts, into `raw-data/sep/` and `out/sep_medians.csv`.

59 PDFs at `federalreserve.gov/monetarypolicy/files/fomcprojtabl{YYYYMMDD}.pdf`, one per meeting that produced projections, January 2012 to now.

Only 44 of the 59 yield a median. The median column was introduced with the September 2015 SEP. Before that the table carries a central tendency and a range, and the individual dots live in a figure rather than in text.

Two layout quirks the parser handles. pdfplumber strips the spaces out of row labels in some vintages, so "Federal funds rate" arrives as "Federalfundsrate". And the header wraps in others, leaving "Variable" and "Longer" on one line and the projection years on the line above, so the year list is recovered from a window of neighbouring lines. The parse is checked against FRED: the most recent meeting's medians match `FEDTARMD` and `FEDTARMDLR` exactly.

## 5. Philadelphia Fed Survey of Professional Forecasters

`fetch_forecasts.py`, into `raw-data/spf/`. Median 3-month Treasury bill level, quarterly, back to 1981, from <https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/survey-of-professional-forecasters/data-files/files/median_tbill_level.xlsx>.

The horizon numbering is counterintuitive. `TBILL1` is the quarter before the survey, whose value the forecasters already know, so it is not a forecast and is dropped. `TBILL2` is the current quarter, and `TBILL3` to `TBILL6` are the four quarters after it. `TBILLA` to `TBILLD` are annual averages and are not used. See `misc/SOURCES.md` for the verbatim definition.

## 6. Atlanta Fed Market Probability Tracker

Probability distributions for the future policy rate, backed out of CME options on three-month SOFR futures, from <https://www.atlantafed.org/research-and-data/data/market-probability-tracker>. Daily, 2023 onward, about 300,000 rows. Downloaded by hand, above.

The `DATA` sheet is long: `date`, `reference_start`, `target_range`, `field`, `value`. `build_dataset.py` keeps `field == "Rate: mean"`, converts basis points to per cent, and dates each point at the midpoint of its three-month reference window, 45 days after `reference_start`.

## 7. NY Fed ACM term premium

`fetch_forecasts.py`, into `raw-data/nyfed/`, from <https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls>. Downloaded but not yet used. It would strip the term premium out of the Treasury forward hairs, the main known bias in that source.

## Not obtained: fed funds futures

The instrument most published versions of this chart use. Its history is not free; it is available through vendors such as Bloomberg, LSEG (Refinitiv), CME DataMine and Databento.
