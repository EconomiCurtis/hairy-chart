---
title: "The Hairy Chart: Source Notes"
# The website renders every .md file and lists any page without this flag.
listed: false
draft: true
---

The source notes from the notebooks and the interactive, in one place: what each series is, in the publisher's own words where possible, with citations. How each file is downloaded and cleaned is in the [scripts README](https://github.com/EconomiCurtis/hairy-chart/tree/main/scripts).

Each section also gives the series' plot source line: the short credit printed under every plot, naming the publisher and, where the data came through someone else, the distributor. A plot lists the line for each series it shows, then the target rate's, as "Sources: …; …."

## Federal Funds Target Rate

The rate the Federal Open Market Committee announces it is aiming for. A single number until December 2008, a quarter-point range from then on. The New York Fed: "The Federal Open Market Committee establishes the target rate, or range, for trading in the federal funds market."

FRED `DFEDTAR` is the single target, 27 September 1982 to 15 December 2008. `DFEDTARL` and `DFEDTARU` are the lower and upper limits of the range from 16 December 2008, when the Committee cut to 0 to 0.25 per cent and has used a range ever since. Verified at the join: `DFEDTAR` ends 2008-12-15 at 1.00, `DFEDTARL`/`DFEDTARU` begin 2008-12-16 at 0.00/0.25.

Values before 1994 are a reconstruction: the FOMC began announcing its target decisions in February 1994, and FRED's series notes say the 1982 to 1993 values come from Thornton (2005), a Federal Reserve Bank of St. Louis working paper.

**Plot source line.** Federal Reserve Board via the St. Louis Fed's FRED (target rate)

**Citations.**

- <https://fred.stlouisfed.org/series/DFEDTAR>
- <https://fred.stlouisfed.org/series/DFEDTARU>
- <https://fred.stlouisfed.org/series/DFEDTARL>
- Thornton, Daniel L. (2005), "A New Federal Funds Rate Target Series: September 27, 1982 - December 31, 1993", Federal Reserve Bank of St. Louis
- <https://www.newyorkfed.org/markets/reference-rates/effr>

## Treasury Forward Curve: GSW Nominal Yield Curve

What the Treasury bond market implies about future short rates, backed out daily by Federal Reserve Board staff from a smooth curve fitted across the whole maturity spectrum.

The Board describes the dataset as "smoothed yields on hypothetical Treasury securities that can be easily compared across maturities and over time, from 1961 to the present". Its model "stipulates that the shape of the yield curve on any given date can be adequately captured by a set of six parameters", estimated "by minimizing the discrepancy between the fitted Svensson yield curve and observed market yields". Before 1980, "the Nelson-Siegel model—a model with fewer parameters—was used".

On what goes into the fit: "only the coupon securities (Treasury notes and bonds) are used"; "on-the-run and first-off-the-run Treasury notes and bonds are not used"; and "Treasury bills and Treasury floating rate notes (FRNs) are not used".

It is not an official statistic. The Board calls it "a staff research product and not an official statistical release". A forward rate is the expected future short rate *plus a term premium*, so they aren’t a pure expectations path (they might be a bit above or below). And because bills are excluded and the curve is a six-parameter analytic function, the hairs are smooth by construction: they cannot show the discrete steps at FOMC meetings that market data pricing individual meetings shows.

**Plot source line.** Federal Reserve Board, GSW nominal yield curve

**Citations.**

- <https://www.federalreserve.gov/data/nominal-yield-curve.htm>
- Gürkaynak, Sack and Wright (2006), FEDS 2006-28, <https://www.federalreserve.gov/pubs/feds/2006/200628/200628pap.pdf>
- Published in *Journal of Monetary Economics* 54(8), 2007, 2291-2304

## Options-Implied (SOFR): Atlanta Fed Market Probability Tracker

What options traders are collectively betting, as a full probability distribution over where the overnight rate will average in a future three-month window.

From the data dictionary shipped inside the file: "The Market Probability Tracker uses Chicago Mercantile Exchange (CME) 3-month SOFR options to estimate the probability ditributions implied by their prices and specified reference window." Their guide adds that it "transforms options on SOFR futures prices into probability distribution values".

Two fields are used. `reference_start` is the "Start date of the 3-month window referenced by CME 3-month SOFR contracts". `Rate: mean` is "The rate, in basis points, associated with the mean of the estimated distribution for a given reference window".

The underlying rate is SOFR, published by the [Federal Reserve Bank of New York](https://www.newyorkfed.org/markets/reference-rates/sofr): a broad measure of the cost of borrowing cash overnight collateralized by U.S. Treasury securities. That makes it a secured rate, where the federal funds rate is unsecured lending between banks; the two are close but not identical. An option-implied distribution is risk-neutral, so it is what traders expect weighted by how much they care about being wrong each way, not literally what they expect. It starts in March 2023.

Each point comes from its own window's option prices rather than from one fitted curve, but as a three-month average weighted across possible outcomes it does not resolve individual FOMC meetings.

**Plot source line.** Federal Reserve Bank of Atlanta, Market Probability Tracker

**Citations.**

- <https://www.atlantafed.org/research-and-data/data/market-probability-tracker>
- <https://www.atlantafed.org/research-and-data/data/market-probability-tracker/what-to-know>
- <https://www.newyorkfed.org/markets/reference-rates/sofr>
- Estimation code published as `mpt_source.zip` on the tracker page

## FOMC Median Projection: The Summary of Economic Projections

Four times a year each of the Federal Reserve's senior policymakers writes down where they think the federal funds rate *should* be at the end of each of the next few years. This is the middle answer.

The table is titled "Economic projections of Federal Reserve Board members and Federal Reserve Bank presidents, under their individual assumptions of projected appropriate monetary policy": all 7 Governors plus all 12 Reserve Bank presidents. That is wider than the Committee's voting membership: the Board says the Committee "consists of twelve members", namely "the seven members of the Board of Governors of the Federal Reserve System; the president of the Federal Reserve Bank of New York; and four of the remaining eleven Reserve Bank presidents, who serve one-year terms on a rotating basis". Staff produce a separate forecast, the Tealbook, released only after five years.

From the table notes: "The projections for the federal funds rate are the value of the midpoint of the projected appropriate target range for the federal funds rate or the projected appropriate target level for the federal funds rate at the end of the specified calendar year or over the longer run." And: "For each period, the median is the middle projection when the projections are arranged from lowest to highest."

It is not a forecast. The row is labelled "Memo: Projected appropriate policy path", and projections rest on each participant's "assessment of appropriate monetary policy". Normative, conditional on each person's own outlook, and never voted on.

Only 44 of 59 releases give a median. The median column was introduced with the September 2015 SEP; before that the table shows a central tendency and range only, and the dots exist solely as a figure.

**Plot source line.** Federal Reserve Board, Summary of Economic Projections

**Citations.**

- `https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl{YYYYMMDD}.pdf`
- <https://www.federalreserve.gov/monetarypolicy/fomc.htm>
- <https://fred.stlouisfed.org/series/FEDTARMD>

## Professional Forecasters: Survey of Professional Forecasters

Every quarter the Philadelphia Fed asks a few dozen professional forecasters where the three-month Treasury bill rate will be over the next five quarters, and publishes the median.

The Philadelphia Fed describes it as "the oldest quarterly survey of macroeconomic forecasts in the United States. The survey began in 1968 and was conducted by the American Statistical Association and the National Bureau of Economic Research. The Federal Reserve Bank of Philadelphia took over the survey in 1990." Individual responses are "kept confidential by using identification numbers".

The survey asks about the bill rate, not the federal funds rate, but the two track each other closely: a three-month bill pays roughly what investors expect overnight rates to average over its three months. The bill normally sits a little below fed funds, so a forecast of the bill rate works as a rough forecast of the policy rate that runs slightly low.

**Plot source line.** Federal Reserve Bank of Philadelphia, Survey of Professional Forecasters

**Citations.**

- <https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters>
- Documentation PDF: variable definitions p.10, horizon numbering p.20, survey timing p.7

## Recessions: NBER Business Cycle Dates

The interactive can shade US recessions behind the plot, each from its business cycle peak to its trough. The notebooks do not use them.

The dates are the ones on FRED's graphs: "FRED uses business cycle turning points determined by the National Bureau of Economic Research (NBER) for recession shading on graphs." The turning points are months, and "The monthly dates for the peaks and troughs are represented as daily dates in the graphs regardless of the frequency of the plotted data."

They come from FRED `USREC`, titled "NBER based Recession Indicators for the United States from the Period following the Peak through the Trough". Each run of recession months gives one recession: the peak is the month before the run, the trough its last month. The 34 recessions this recovers match FRED's published list of recession-bar dates exactly.

**Plot source line.** National Bureau of Economic Research via the St. Louis Fed's FRED (recessions)

**Citations.**

- <https://fred.stlouisfed.org/help/data/understanding-the-data/recession-bars/>
- <https://fred.stlouisfed.org/series/USREC>
- <https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions>

## Other Sources

Other data on expected federal funds rates exist. The most direct are fed funds futures, exchange-traded contracts whose prices imply the market's expected average federal funds rate for each coming month, and overnight index swap (OIS) curves, which do the same through swap contracts. Both price individual FOMC meetings, so their paths step rather than move smoothly, and they are the usual basis for this plot in market commentary. These series are not free (which is why they aren't included in this notebook, I couldn't even find them in a spot where I could just steal the data): they require payment, through vendors such as Bloomberg, LSEG (Refinitiv), CME DataMine or Databento.

The four sources above are free stand-ins for them.
