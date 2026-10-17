# Source documentation

What each series in `out/trunk.csv` and `out/hairs.csv` actually is, in the publisher's own words where possible, with citations. Quoted text is marked and attributed. Everything else is paraphrase.

Every source here is published by the Federal Reserve System: the Board of Governors, or the Reserve Banks of New York, Atlanta, Philadelphia and St. Louis. All of it is free and none of it requires an account.

Operational instructions for downloading are in [raw-data/getting-data.md](raw-data/getting-data.md). This file is about what the numbers mean.

---

## The trunk: the policy rate

### `effr` and `effr_ma1m`, the effective federal funds rate

**In one sentence:** the interest rate US banks actually charged each other for overnight loans yesterday, measured from every reported transaction and published each morning by the New York Fed, as opposed to the rate the Fed says it wants.

**What the publisher says.** The New York Fed describes the market as consisting of "domestic unsecured borrowings in U.S. dollars by depository institutions from other depository institutions and certain other entities, primarily government-sponsored enterprises". The rate itself "is calculated as a volume-weighted median of overnight federal funds transactions reported in the FR 2420 Report of Selected Money Market Rates", and the New York Fed "publishes the EFFR for the prior business day ... at approximately 9:00 a.m." Only genuinely overnight trades count: "overnight transactions are those settled on the same day as the trade date and maturing the following business day", and open-ended or longer transactions are excluded.

**A methodology break you must know about.** The Board's H.15 release states plainly: "As of March 1, 2016, the daily effective federal funds rate (EFFR) is a volume-weighted median of transaction-level data collected from depository institutions in the Report of Selected Money Market Rates (FR 2420). Prior to March 1, 2016, the EFFR was a volume-weighted mean of rates on brokered trades." So the series changes from a mean of brokered trades to a median of all reported trades partway through the sample. It is one series in FRED but two definitions.

**Technical detail.** FRED series `DFF`, daily, per cent per annum, from 1 July 1954. Weekends and holidays carry the previous business day's value forward, which is why the file has 26,356 rows rather than a count of business days. `effr_ma1m` is our own 30-calendar-day trailing mean, not a published series.

**Caveat that matters for this chart.** Before 2008 the Fed hit its target through open market operations rather than by paying interest on reserves, and the daily rate ran well away from target at month, quarter and year ends when banks squared their books. Across 1996 to 1999 the daily rate sits within half a point of target on 96.6 per cent of days, but the exceptions are large: 7.80 per cent on 1 July 1996 against a 5.25 target. See `out/trunk_comparison.png`. This is why JPMorgan's version of the hairy chart plots a one-month moving average.

**Citations.**
- <https://www.newyorkfed.org/markets/reference-rates/effr>
- <https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates>
- <https://www.federalreserve.gov/releases/h15/> (H.15 Selected Interest Rates, notes)
- <https://fred.stlouisfed.org/series/DFF>

### `target_lo`, `target_hi`, `target_mid`, the FOMC's target

**In one sentence:** the rate the Federal Open Market Committee announces it is aiming for, which is a single number until December 2008 and a quarter-point range from then on.

**What the publisher says.** The New York Fed: "The Federal Open Market Committee establishes the target rate, or range, for trading in the federal funds market."

**Technical detail.** FRED `DFEDTAR` is the single target, 1982 to 15 December 2008. `DFEDTARL` and `DFEDTARU` are the lower and upper limits of the range from 16 December 2008 onward, when the Committee cut to a 0 to 0.25 per cent range and has used a range ever since. Our loader fills the pre-2008 gap in the range columns with the single target, so `target_mid` is continuous across the break. Step changes only, so the series is flat between meetings.

**Citations.**
- <https://fred.stlouisfed.org/series/DFEDTARU>, <https://fred.stlouisfed.org/series/DFEDTARL>, <https://fred.stlouisfed.org/series/DFEDTAR>

---

## `treasury_forward`, the Treasury forward curve

**In one sentence:** what the Treasury bond market implies about future short-term interest rates, backed out daily from the prices of Treasury notes and bonds by Federal Reserve Board staff, using a smooth curve fitted through the whole maturity spectrum.

**What the publisher says.** The Board describes the dataset as "smoothed yields on hypothetical Treasury securities that can be easily compared across maturities and over time, from 1961 to the present". On the model: "The shape of the yield curve on any given date can be adequately captured by a set of six parameters", and those parameters "can be estimated by minimizing the discrepancy between the fitted Svensson yield curve and observed market yields". Before 1980 "the Nelson-Siegel model, a model with fewer parameters, was used".

**What goes into the fit, and what does not.** This is the important part for us. Per the Board: "Only the coupon securities (Treasury notes and bonds) are used." Furthermore "on-the-run and first-off-the-run Treasury notes and bonds are not used", because their liquidity premiums distort the fit, and "Treasury bills and Treasury floating rate notes (FRNs) are not used".

**Technical detail.** The file `feds200628.csv` carries, for every business day since 14 June 1961, the six Svensson parameters `BETA0` to `BETA3`, `TAU1` and `TAU2`, plus pre-computed yields and forward rates at whole-year maturities. The instantaneous forward rate at horizon `n` years, continuously compounded, is

```
f(n) = BETA0 + BETA1*exp(-n/TAU1) + BETA2*(n/TAU1)*exp(-n/TAU1) + BETA3*(n/TAU2)*exp(-n/TAU2)
```

We evaluate this at monthly horizons out to 60 months, because the published `SVENF01` to `SVENF30` columns only give whole years and the hairy chart lives in the first three. Our recomputation reproduces the published whole-year columns to under 0.001 percentage points across 16,262 curve-days, which is the rounding in the published file. Values are converted from continuous to annual compounding for plotting.

Updated roughly weekly: the Board says it will "generally try to post the updated series once per week; typically, updated series data will be posted on Tuesday".

**Three caveats, all of which belong in the chart notes.**

It is not an official statistic. The Board labels it "a staff research product and not an official statistical release", "subject to delay, revision, or methodological changes without advance notice".

A forward rate is not an expectation. It is the expected future short rate plus a term premium, so these hairs sit above a pure expectations path, more so before 2008 than after. `raw-data/nyfed/ACMTermPremium.xls` is downloaded and can strip this out, but that adjustment is not yet applied.

**The hairs are smooth by construction and cannot be otherwise.** Because bills are excluded and the curve is a six-parameter analytic function of maturity, the short end is an extrapolation from the note and bond curve, and the forward curve is infinitely differentiable. It therefore cannot show the discrete steps at FOMC meeting dates that a fed funds futures strip shows. That is a property of the instrument, not of our processing. We check the extrapolation by comparing the one-month forward against the actual overnight rate: mean gap ranges from +0.03 to +0.31 percentage points by era, standard deviation 0.14 to 0.36, so it anchors well, but it is still an extrapolation.

**Citations.**
- <https://www.federalreserve.gov/data/nominal-yield-curve.htm>
- Gürkaynak, Refet S., Brian Sack, and Jonathan H. Wright (2006), "The U.S. Treasury Yield Curve: 1961 to the Present," Finance and Economics Discussion Series 2006-28, <https://www.federalreserve.gov/pubs/feds/2006/200628/200628pap.pdf>
- Published as *Journal of Monetary Economics* 54(8), 2007, 2291-2304.

---

## `options_implied`, the Atlanta Fed Market Probability Tracker

**In one sentence:** what options traders are collectively betting, expressed as a full probability distribution over where the overnight rate will average in a future three-month window, computed daily by the Atlanta Fed from the prices of options traded on the CME.

**What the publisher says.** The data dictionary shipped inside the file itself: "The Market Probability Tracker uses Chicago Mercantile Exchange (CME) 3-month SOFR options to estimate the probability ditributions implied by their prices and specified reference window." (The typo is in the original.) The Atlanta Fed's guide adds that the tool "uses prices of options (or financial contracts) to estimate the probability distribution for where the three-month compounded average Secured Overnight Financing Rate (SOFR), a reference rate for overnight borrowing, is headed in the future", and that it "transforms options on SOFR futures prices into probability distribution values".

**Field definitions, verbatim from the file's DICTIONARY sheet.**

| field | definition |
|---|---|
| `date` | "Observation date" |
| `reference_start` | "Start date of the 3-month window referenced by CME 3-month SOFR contracts" |
| `target_range` | "FOMC federal funds rate target range on the indicated observation date" |
| `Rate: mean` | "The rate, in basis points, associated with the mean of the estimated distribution for a given reference window" |
| `Rate: mode` | "The rate, in basis points, associated with the mode of the estimated distribution for a given reference window" |
| `Prob: cut` | "The probability, in percent, average SOFR over the reference window will be below the FOMC's target range" |
| `Prob: hike` | "The probability, in percent, average SOFR over the reference window will be above the FOMC's target range" |

**Technical detail.** We take `field == "Rate: mean"`, divide by 100 to convert basis points to per cent, and place each point at the midpoint of its reference window, which is `reference_start` plus 45 days. Daily, 29 March 2023 to now, a median of 12 reference windows per day, longest horizon about 3.6 years. 857 hairs.

**Caveats.** The underlying rate is SOFR, not fed funds. They are close but not identical: SOFR is secured overnight Treasury repo, fed funds is unsecured interbank. Second, an option-implied distribution is risk-neutral, so it is not literally what traders think will happen, it is what they think weighted by how much they care about being wrong in each direction. Third, it only starts in 2023, so it cannot carry the historical part of the chart.

Unlike the Treasury curve, each point comes from that window's own option prices rather than from one fitted curve. Each point is still a three-month average and a probability-weighted mean across outcomes, so the hairs do not step at individual FOMC meetings the way fed funds futures do. In the notebook they are plotted at each window's midpoint and joined by lines.

**Citations.**
- <https://www.atlantafed.org/research-and-data/data/market-probability-tracker>
- <https://www.atlantafed.org/research-and-data/data/market-probability-tracker/what-to-know>
- Estimation code, R and C++, shipped as `mpt_source.zip` at the same location.
- Data dictionary: the `DICTIONARY` sheet of `mpt_histdata.xlsx`.

---

## `sep_median`, the FOMC dot plot median

**In one sentence:** four times a year, each of the 19 senior Federal Reserve policymakers writes down where they think the federal funds rate *should* be at the end of each of the next few years if policy goes as they think it ought to, and this is the middle answer.

**Who submits, precisely.** Not staff, and not only the voting members. The projection table is titled, verbatim, "Economic projections of Federal Reserve Board members and Federal Reserve Bank presidents, under their individual assumptions of projected appropriate monetary policy". That is all seven Governors plus all twelve Reserve Bank presidents, 19 people. The June 2026 table states: "Nineteen participants submitted information in conjunction with the March 17-18, 2026, meeting. Eighteen participants submitted information in conjunction with the June 16-17, 2026, meeting; one of these 18 participants did not submit projections for 2028."

This is a wider group than the FOMC's voting membership. The Board describes the Committee itself as consisting "of twelve members, the seven members of the Board of Governors of the Federal Reserve System; the president of the Federal Reserve Bank of New York; and four of the remaining eleven Reserve Bank presidents, who serve one-year terms on a rotating basis". So "participants" (19, all of whom submit projections) is not the same set as "members" (12, who vote). Fed staff produce a separate forecast, the Tealbook, which is not this and is released only after five years.

**What the number means, verbatim.** From the notes to the projection table: "The projections for the federal funds rate are the value of the midpoint of the projected appropriate target range for the federal funds rate or the projected appropriate target level for the federal funds rate at the end of the specified calendar year or over the longer run." And on the statistic: "For each period, the median is the middle projection when the projections are arranged from lowest to highest. When the number of projections is even, the median is the average of the two middle projections."

Note the word "appropriate". The table calls this row "Memo: Projected appropriate policy path", and the notes say "Each participant's projections are based on his or her assessment of appropriate monetary policy". These are normative, what each person thinks policy *should* do, conditional on their own economic forecast. They are not a committee forecast and the Committee does not vote on them.

**Technical detail.** Published with the March, June, September and December meetings, from January 2012. Values are per cent, referring to the end of the named calendar year, plus a "longer run" value. 43 usable meetings, 151 points.

**A real gap.** Only 43 of the 58 SEP releases give a median. The median column was introduced with the September 2015 SEP. Before that the table shows a central tendency and a range only, and the individual dots exist solely as a figure, which would have to be digitised to recover. So `sep_median` starts in September 2015, not January 2012.

**Validation.** Our PDF parse matches FRED's `FEDTARMD` and `FEDTARMDLR` exactly on the most recent meeting.

**Citations.**
- Projection tables, one per meeting: `https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl{YYYYMMDD}.pdf`
- <https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>
- <https://www.federalreserve.gov/monetarypolicy/fomc.htm> (Committee composition)
- <https://fred.stlouisfed.org/series/FEDTARMD>, <https://fred.stlouisfed.org/series/FEDTARMDLR>

---

## `spf_median`, the Survey of Professional Forecasters

**In one sentence:** every quarter the Philadelphia Fed mails a questionnaire to a few dozen professional economic forecasters at banks, consultancies and research houses, asks them where the three-month Treasury bill rate will be over the next five quarters, and publishes the middle answer.

**What the publisher says.** The Philadelphia Fed describes it as "the oldest quarterly survey of macroeconomic forecasts in the United States. The survey began in 1968 and was conducted by the American Statistical Association and the National Bureau of Economic Research. The Federal Reserve Bank of Philadelphia took over the survey in 1990." Individual responses are published but anonymised: they are "kept confidential by using identification numbers".

**What the variable is.** From the SPF documentation, `TBILL` is the three-month Treasury bill rate in percentage points, and "Quarterly forecasts are for the quarterly average of the underlying daily levels". So each point is a forecast of an average over a quarter, not a point-in-time rate.

**Horizon numbering, which is easy to get wrong.** The documentation is explicit: "The number '1' represents the 'forecast' for the quarter prior to the quarter in which the survey is conducted. The forecasters know the values of the variables for this quarter at the time they submit their projections." Then: "The number '2' represents the forecast for the current quarter, defined as the quarter in which the survey is conducted. The numbers '3' through '6' represent the forecasts for the four quarters after the current quarter."

So `TBILL1` is **not a forecast at all** and is dropped by our loader. The real forecast horizons are `TBILL2` at zero quarters ahead through `TBILL6` at four quarters ahead, giving each hair five points spanning about a year. Getting this wrong shifts every hair a quarter early, which is a mistake this project made and corrected.

**Timing.** Questionnaires go out at the end of the first month of each quarter and responses are due in the middle of the second month: mid-February, mid-May, mid-August, mid-November. We date each hair at the deadline, since that is when the forecaster's information set closes.

**Technical detail.** 181 hairs, 905 points, August 1981 to now. This is the longest-running hair source here and the only one covering the 1980s.

**Caveats.** The three-month Treasury bill is not the federal funds rate. It is a secured government rate at a three-month tenor, and it normally sits somewhat below fed funds, which shows up in our validation as a mean gap of -0.28 percentage points at the front of the hair. It is also a survey of forecasters rather than a price, so it carries no money and is not a market expectation in the sense the Economist chart means.

**Citations.**
- <https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters>
- Documentation PDF: <https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/survey-of-professional-forecasters/spf-documentation.pdf> (variable definitions p.10, horizon numbering p.20, survey timing p.7)
- Data file: `median_tbill_level.xlsx`, sheet `Median_Level`

---

## Supporting data

### FOMC meeting dates

Scraped from the Board's own calendars, preferring the `monetary{YYYYMMDD}a.htm` statement links, because a hair should start the moment a decision became public. 268 dates from February 1994, median eight scheduled meetings a year. Statements were not issued for every meeting before 1994, which is why the series starts there.

<https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm> and `fomchistorical{YYYY}.htm`.

### ACM term premium, downloaded but not yet used

The Adrian, Crump and Moench decomposition of Treasury yields into an expected-short-rate component and a term premium. Needed to convert `treasury_forward` from a forward rate into a risk-neutral expected path, which is the like-for-like comparison against futures.

<https://www.newyorkfed.org/research/data_indicators/term-premia-tabs>

---

## What is not here

Fed funds futures, the instrument The Economist, Apollo and BofA actually plotted, and OIS forward curves, which is what JPMorgan plotted. Both need a paid feed. `todo.md` lists five manual routes and what each would buy.
