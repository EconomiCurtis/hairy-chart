# The write-up's hero image: the R notebook's combined hairy plot, with larger
# text in Source Sans Pro so it reads at the size the page shows it. The plot
# itself is the notebook's; only the type changes.
#
#     Rscript plots/hero.R
#
# Writes plots/hairy-plot.png, which is also the post's listing image. Needs
# dplyr, readr, ggplot2, scales, lubridate and ragg, and Source Sans Pro
# installed on this machine.

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(ggplot2)
  library(scales)
})

# The post folder, from wherever the script is run.
args <- commandArgs(trailingOnly = FALSE)
root <- dirname(dirname(normalizePath(sub("^--file=", "", args[grep("^--file=", args)]))))

RATE <- "#0B1B4A"
INK <- "#1B3A6B"
INK_SOFT <- "#5C7599"
GRID <- "#C9D6E6"
BG <- "#FFFFFF"
FONT <- "Source Sans Pro"

pal <- c(
  treasury_forward = "#2E7DBF",
  options_implied  = "#C8102E",
  sep_median       = "#E08A1E",
  spf_median       = "#8C1A8C"
)
src_label <- c(
  treasury_forward = "Treasury Forward Curve",
  options_implied  = "Options-Implied (SOFR)",
  sep_median       = "FOMC Median Projection",
  spf_median       = "Professional Forecasters"
)

ffr <- read_csv(file.path(root, "data", "fed_funds_rate.csv"), show_col_types = FALSE)
hairs <- read_csv(file.path(root, "data", "hairs.csv"), show_col_types = FALSE) |>
  mutate(across(c(as_of, target_date), as.Date))

# Same paths as the notebook: each hair starts on the target line at its
# forecast date (the target read a day later), and forecaster values are held
# across their calendar quarter.
step_sources <- "spf_median"
hair_path <- function(h, src) {
  anchors <- h |>
    distinct(as_of) |>
    mutate(target_date = as_of, rate_pct = ffr$target_mid[match(as_of + 1, ffr$date)]) |>
    filter(!is.na(rate_pct))
  points <- h |> select(as_of, target_date, rate_pct)
  if (src %in% step_sources) {
    last <- points |> group_by(as_of) |> slice_max(target_date, n = 1) |> ungroup()
    points <- bind_rows(
      points |> mutate(target_date = pmax(lubridate::floor_date(target_date, "quarter"), as_of)),
      last |> mutate(target_date = lubridate::ceiling_date(target_date, "quarter"))
    )
  }
  bind_rows(anchors, points)
}
hair_layer <- function(src, alpha, linewidth) {
  geom <- if (src %in% step_sources) geom_step else geom_line
  args <- list(
    data = hair_path(hairs |> filter(source == src), src) |> mutate(source = src),
    mapping = aes(target_date, rate_pct, group = as_of, color = source),
    alpha = alpha, linewidth = linewidth, lineend = "round"
  )
  if (src %in% step_sources) args$direction <- "hv"
  do.call(geom, args)
}
years <- function(k) as.Date(sprintf("%d-01-01", seq(ceiling(1982 / k) * k, 2029, by = k)))

# Text sizes for an image 11 inches wide that the page shows about 800 pixels
# wide: a point here comes out at about a pixel there.
p <- ggplot() +
  hair_layer("spf_median", 0.40, 0.35) +
  hair_layer("treasury_forward", 0.25, 0.30) +
  hair_layer("options_implied", 0.09, 0.25) +
  hair_layer("sep_median", 0.55, 0.45) +
  geom_line(data = ffr, aes(date, target_mid), color = RATE, linewidth = 1.1, lineend = "round") +
  scale_color_manual(
    values = pal, labels = src_label, breaks = names(pal),
    guide = guide_legend(override.aes = list(alpha = 1, linewidth = 1.8))
  ) +
  scale_x_date(breaks = years(5), minor_breaks = years(1), labels = label_date("%Y"),
               guide = guide_axis(minor.ticks = TRUE)) +
  scale_y_continuous(labels = label_number(suffix = "%"), breaks = seq(0, 12, 2)) +
  coord_cartesian(xlim = as.Date(c("1982-01-01", "2029-12-31")), ylim = c(-0.3, 12)) +
  labs(
    title = "The Hairy Plot",
    subtitle = "US federal funds target rate, with expected rate paths",
    caption = paste(
      "Sources: Federal Reserve Board (GSW nominal yield curve; SEP; target rate, via the St. Louis Fed's FRED database);",
      "\nFederal Reserve Bank of Atlanta (Market Probability Tracker); Federal Reserve Bank of Philadelphia (SPF)."
    )
  ) +
  theme_minimal(base_size = 13, base_family = FONT) +
  theme(
    plot.background = element_rect(fill = BG, color = NA),
    panel.background = element_rect(fill = BG, color = NA),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    panel.grid.major.y = element_line(color = GRID, linewidth = 0.4),
    axis.text = element_text(color = INK_SOFT, size = 13),
    axis.ticks.x = element_line(color = INK_SOFT, linewidth = 0.3),
    axis.ticks.length.x = unit(5, "pt"),
    axis.minor.ticks.length.x = rel(0.5),
    axis.title = element_blank(),
    plot.title = element_text(color = INK, face = "bold", size = 20),
    plot.subtitle = element_text(color = INK_SOFT, size = 15, margin = margin(t = 2, b = 10)),
    plot.caption = element_text(color = INK_SOFT, size = 9, hjust = 0, margin = margin(t = 10)),
    legend.title = element_blank(),
    legend.text = element_text(color = INK, size = 14),
    legend.position = "inside",
    legend.position.inside = c(0.995, 0.985),
    legend.justification = c(1, 1),
    legend.background = element_rect(fill = BG, color = NA),
    legend.key.spacing.y = unit(2, "pt"),
    plot.margin = margin(12, 14, 8, 10)
  )

ggsave(file.path(root, "plots", "hairy-plot.png"), p, width = 11, height = 6.5, dpi = 150,
       device = ragg::agg_png, bg = BG)
cat("wrote plots/hairy-plot.png\n")
