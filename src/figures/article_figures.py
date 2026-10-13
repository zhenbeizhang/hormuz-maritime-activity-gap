"""Deterministic analytical verification plots from publication source tables.

These plots verify the data carried by Main Figures 3 and 4.  They are not
pixel-identical copies of the journal layout, which includes editorial
composition and third-party image panels that are not redistributed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE = "#0072B2"
ORANGE = "#D55E00"
TEAL = "#009E73"
GREY = "#5B6570"


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
        }
    )


def load_sources(article_data: Path) -> dict[str, pd.DataFrame]:
    paths = {
        "figure3": article_data / "main_figures/Figure_3_source_data.csv",
        "figure4": article_data / "main_figures/Figure_4_source_data.csv",
        "supplementary1": article_data
        / "supplementary_figures/Supplementary_Figure_1_source_data.csv",
        "supplementary4": article_data
        / "supplementary_figures/Supplementary_Figure_4_source_data.csv",
    }
    frames = {name: pd.read_csv(path) for name, path in paths.items()}
    expected_rows = {"figure3": 32, "figure4": 1436, "supplementary1": 55, "supplementary4": 33}
    for name, expected in expected_rows.items():
        if len(frames[name]) != expected:
            raise ValueError(f"{name} has {len(frames[name])} rows; expected {expected}")
    return frames


def render_figure3(source: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.2), constrained_layout=True)
    contrasts = source[source["panel"].eq("a")].dropna(subset=["point_estimate"])
    y = np.arange(len(contrasts))
    axes[0].errorbar(
        contrasts["point_estimate"],
        y,
        xerr=np.vstack(
            [
                contrasts["point_estimate"] - contrasts["interval_lower"],
                contrasts["interval_upper"] - contrasts["point_estimate"],
            ]
        ),
        fmt="o",
        color=BLUE,
        ecolor=GREY,
        capsize=3,
    )
    axes[0].axvline(0, color="black", linewidth=0.8)
    axes[0].set_yticks(y, [item.replace("_", " ") for item in contrasts["contrast"]])
    axes[0].set_title("a  Port-call contrasts", loc="left", fontweight="bold")
    dates = source[source["panel"].eq("b")].dropna(subset=["utc_date"]).copy()
    dates["utc_date"] = pd.to_datetime(dates["utc_date"])
    axes[1].plot(dates["utc_date"], dates["density_per_100_km2"], "o-", color=ORANGE)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axes[1].tick_params(axis="x", rotation=35)
    axes[1].set_ylabel("Detections per 100 km²")
    axes[1].set_title("b  Five March acquisitions", loc="left", fontweight="bold")
    checks = source[source["panel"].eq("c")].dropna(subset=["event_percent_change"])
    axes[2].scatter(np.arange(len(checks)), checks["event_percent_change"], s=20, color=TEAL)
    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].set_ylabel("SAR change (%)")
    axes[2].set_xlabel("Prespecified check")
    axes[2].set_title("c  Sparse-acquisition robustness", loc="left", fontweight="bold")
    for suffix in ("png", "pdf"):
        fig.savefig(output.with_suffix(f".{suffix}"), dpi=300)
    plt.close(fig)


def render_figure4(source: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.2), constrained_layout=True)
    port = source[source["record_type"].eq("port_daily")].copy()
    port["utc_date"] = pd.to_datetime(port["utc_date"])
    axes[0, 0].plot(port["utc_date"], port["current_7d"], color=BLUE, label="2026")
    axes[0, 0].plot(port["utc_date"], port["history_7d"], color=GREY, label="2022–2025")
    axes[0, 0].legend(frameon=False)
    axes[0, 0].set_title("a  Port calls", loc="left", fontweight="bold")
    sar = source[source["record_type"].eq("sar_scene")].copy()
    sar["utc_date"] = pd.to_datetime(sar["utc_date"])
    axes[0, 1].scatter(sar["utc_date"], sar["sar_current_density_per_100_km2"], s=14, color=ORANGE)
    axes[0, 1].set_ylabel("Detections per 100 km²")
    axes[0, 1].set_title("b  Adjacent-water SAR", loc="left", fontweight="bold")
    no2 = source[source["record_type"].eq("no2_daily")].copy()
    no2["utc_date"] = pd.to_datetime(no2["utc_date"])
    for series, group in no2.groupby("series", dropna=True):
        axes[1, 0].plot(group["utc_date"], group["rolling_7d"], label=str(series), linewidth=1.2)
    axes[1, 0].axhline(0, color="black", linewidth=0.8)
    axes[1, 0].set_ylabel(r"NO$_2$ anomaly (mol m$^{-2}$)")
    axes[1, 0].set_title(r"c  Population-weighted NO$_2$", loc="left", fontweight="bold")
    intervals = source[source["record_type"].eq("no2_interval")].dropna(subset=["buffer_km"])
    x = intervals["buffer_km"].to_numpy(float)
    point = intervals["no2_change_vs_historical_mol_m2"].to_numpy(float)
    lower = intervals["no2_change_vs_historical_bootstrap_ci95_lower"].to_numpy(float)
    upper = intervals["no2_change_vs_historical_bootstrap_ci95_upper"].to_numpy(float)
    axes[1, 1].errorbar(x, point, yerr=np.vstack([point - lower, upper - point]), fmt="o", color=TEAL, capsize=3)
    axes[1, 1].axhline(0, color="black", linewidth=0.8)
    axes[1, 1].set_xlabel("Buffer (km)")
    axes[1, 1].set_ylabel(r"Difference (mol m$^{-2}$)")
    axes[1, 1].set_title("d  Full-refit intervals", loc="left", fontweight="bold")
    for axis in axes.ravel():
        if axis.has_data():
            axis.tick_params(axis="x", rotation=30)
    for suffix in ("png", "pdf"):
        fig.savefig(output.with_suffix(f".{suffix}"), dpi=300)
    plt.close(fig)


def run(article_data: Path, output_root: Path) -> dict[str, object]:
    setup_style()
    frames = load_sources(article_data)
    output_root.mkdir(parents=True, exist_ok=True)
    render_figure3(frames["figure3"], output_root / "Figure_3_verification")
    render_figure4(frames["figure4"], output_root / "Figure_4_verification")
    report = {
        "status": "PASS",
        "source_rows": {name: int(len(frame)) for name, frame in frames.items()},
        "outputs": [
            "Figure_3_verification.png",
            "Figure_3_verification.pdf",
            "Figure_4_verification.png",
            "Figure_4_verification.pdf",
        ],
        "scope": "analytical verification renders; not journal-layout facsimiles",
    }
    (output_root / "figure_validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    repository = Path(__file__).resolve().parents[2]
    parser.add_argument("--article-data", type=Path, default=repository / "article_data")
    parser.add_argument("--output-root", type=Path, default=repository / "reproduced_outputs/figures")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    print(json.dumps(run(args.article_data.resolve(), args.output_root.resolve()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

