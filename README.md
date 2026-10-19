# The Hairy Chart

The US federal funds target rate, plotted with the paths that were expected for it at each past date. Four free sources of expected paths: the Treasury forward curve, options on SOFR futures, the FOMC's median projection, and the Survey of Professional Forecasters.

This folder is the blog post: the main write-up, an R notebook, a Python notebook and an interactive version, all reading the same small data files.

```
index.qmd        main write-up
imgs/            hairy charts published elsewhere, for the write-up's gallery
plots/           copies of the R notebook's figures that the write-up shows
r/               R notebook (ggplot2, gt)
python/          Python notebook (pandas, Altair, great_tables), same text as the R one
interactive/     interactive version: index.qmd includes _hairy-app.html, built by _app/
data/            the CSVs every version reads, about 2.5 MB
scripts/         Python pipeline that builds data/ from the original sources
misc/SOURCES.md  source notes, in the publisher's own words, with citations and plot source lines
```

## Rendering

Each page renders on its own and reads only `data/`.

The R notebook needs R with dplyr, readr, ggplot2, scales, gt and lubridate:

```bash
quarto render r/index.qmd
```

The Python notebook needs the packages in `python/requirements.txt`, here in a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r python/requirements.txt
QUARTO_PYTHON=.venv/bin/python quarto render python/index.qmd
```

The interactive page includes `interactive/_hairy-app.html`, which is committed, so rendering it needs nothing else. After changing `data/`, its prose in `interactive/_app/text.qmd`, or `interactive/_app/template.html`, rebuild and check the fragment first. Both scripts use only the standard library; `build.py` also needs Quarto on the path, for its pandoc.

```bash
python3 interactive/_app/build.py && node interactive/_app/check.js
quarto render interactive/index.qmd
```

`build.py` also writes `interactive/_app/preview.html`, the plot on a bare page that opens straight in a browser. It is not committed.

The write-up's figures in `plots/` are copies of the R notebook's, since rendered output is not committed. After re-rendering the R notebook, refresh them (macOS):

```bash
for f in target-rate:fig-ffr treasury-forward:fig-treasury options-implied:fig-options fomc-median:fig-sep professional-forecasters:fig-spf; do sips --resampleWidth 1650 "r/index_files/figure-html/${f#*:}-1.png" --out "plots/${f%%:*}.png"; done
```

Two images in `plots/` are not copies. The hero, `plots/hairy-plot.png` (also the listing image), is the notebook's combined plot redrawn with larger type so it reads at the size the page shows it; it needs Source Sans Pro installed. `plots/interactive.jpg` is a screenshot of the interactive, replaced by hand.

```bash
Rscript plots/hero.R
```

## Rebuilding the data

Not needed to render, since `data/` is committed. To rebuild it from the original sources, see [scripts/README.md](scripts/README.md). Downloads land in `raw-data/` and intermediate files in `out/`; neither is committed. The interactive embeds its data, so rebuild it afterwards.
