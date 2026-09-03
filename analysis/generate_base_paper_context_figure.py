"""Replot published Fig. 6 as clearly attributed, approximate contextual evidence.

The source paper does not provide machine-readable values.  The values below were
manually digitized from its Figure 6 and therefore must never be described as new
experimental measurements from this project.
"""
from __future__ import annotations

from pathlib import Path


def generate(output: Path) -> tuple[Path, Path]:
    import matplotlib.pyplot as plt

    x = [50, 100, 150, 200, 250, 300]
    # Approximate visual digitization of Aslam et al., Vehicular Communications 52
    # (2025), Fig. 6. Exact source values were not released with the article.
    latency = {
        "Proposed (source paper)": [920.7, 1450, 1751.2, 2000, 2200, 2300],
        "[26]": [1300, 1700, 2000, 2350, 2650, 2997.6],
        "[27]": [2400, 2800, 3100, 3400, 3700, 4310.8],
        "[28]": [3100, 3750, 4100, 4400, 4700, 5200],
        "[29]": [3800, 4500, 4800, 5100, 5400, 5980.5],
    }
    throughput = {
        "Proposed (source paper)": [29, 38, 47, 51, 57, 68],
        "[26]": [15, 19, 21, 26, 26, 27],
        "[27]": [11, 11, 14, 16, 17, 19],
        "[28]": [9, 9, 11, 13, 14, 15],
        "[29]": [8, 8, 9, 11, 12, 14],
    }
    messages = {
        "Proposed (source paper)": [150, 350, 500, 700, 950, 1200],
        "[26]": [1000, 1500, 2000, 2600, 3100, 3400],
        "[27]": [1300, 1750, 2200, 2700, 3200, 3800],
        "[28]": [2000, 2500, 3000, 3400, 4000, 5500],
        "[29]": [2300, 3100, 3500, 4300, 5500, 6500],
    }
    security = {"Proposed": 100, "[26]": 95, "[27]": 80, "[28]": 75, "[29]": 70}
    styles = {
        "Proposed (source paper)": ("#117A37", "o"), "[26]": ("#D33F3F", "x"),
        "[27]": ("#1F67B1", "^"), "[28]": ("#E67E22", "o"), "[29]": ("#8E5CC7", "s"),
    }
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10, "legend.fontsize": 7.3})
    fig, axes = plt.subplots(2, 2, figsize=(10.4, 7.2), constrained_layout=True)

    def line_panel(axis, series, title, ylabel, scale=1.0):
        for name, values in series.items():
            colour, marker = styles[name]
            axis.plot(x, [scale * value for value in values], color=colour, marker=marker, linewidth=1.8, markersize=4, label=name)
        axis.set(title=title, xlabel="Number of CAVs", ylabel=ylabel, xlim=(45, 305))
        axis.set_xticks(x); axis.grid(alpha=.22); axis.legend(frameon=False, loc="upper left")

    line_panel(axes[0, 0], latency, "(a) End-to-end latency", "Latency (ms)")
    line_panel(axes[0, 1], throughput, "(b) Throughput", "Throughput (bps)")
    line_panel(axes[1, 0], messages, "(c) Communication overhead", "Messages (×10³)", scale=.001)
    bars = axes[1, 1].bar(list(security), list(security.values()), color=["#117A37", "#D97B2C", "#D97B2C", "#D97B2C", "#D97B2C"], edgecolor="#555", linewidth=.5)
    axes[1, 1].bar_label(bars, fmt="%.0f%%", padding=3, fontsize=8)
    axes[1, 1].set(title="(d) Security-level comparison", ylabel="Security level (%)", ylim=(0, 112))
    axes[1, 1].grid(axis="y", alpha=.22)
    for axis in axes.flat:
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Published baseline context: Kyber-based AGS-PBFT study", fontsize=13, fontweight="bold")
    fig.text(.5, .005, "Source: Aslam, Bhardwaj, and Chaudhary, Vehicular Communications 52 (2025), Fig. 6. Curves are visually digitized approximations; the security bars are source-reported feature scores. They are not results of this work and have no reported confidence intervals.", ha="center", wrap=True, fontsize=7.7, color="#4F6070")
    output.parent.mkdir(parents=True, exist_ok=True)
    svg, png = output.with_suffix(".svg"), output.with_suffix(".png")
    fig.savefig(svg, bbox_inches="tight"); fig.savefig(png, dpi=260, bbox_inches="tight"); plt.close(fig)
    return svg, png


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(); print(*generate(arguments.output), sep="\n")
