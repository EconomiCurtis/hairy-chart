# The hairy chart

The US federal funds target rate, plotted with the paths that were expected for it at each past date. Four free sources of expected paths: the Treasury forward curve, options on SOFR futures, the FOMC's median projection, and the Survey of Professional Forecasters.

This folder is the blog post: the main write-up, an R notebook, a Python notebook and an interactive version, all reading the same small data files.

```
index.qmd        main write-up
r/               R notebook
python/          Python notebook (to come)
interactive/     interactive version (to come)
data/            the three CSVs every version reads, about 3 MB
scripts/         Python pipeline that builds data/ from the original sources
SOURCES.md       what each series is, in the publisher's own words, with citations
```

## Rendering

```bash
quarto render r/index.qmd
```

Needs R with dplyr, readr, ggplot2, scales, gt and lubridate. The notebook reads only `data/`.

## Rebuilding the data

Not needed to render, since `data/` is committed. To rebuild it from the original sources, see [scripts/README.md](scripts/README.md). Downloads land in `raw-data/` and intermediate files in `out/`; neither is committed.
