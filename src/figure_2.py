"""Reproduce the focal Khor Fakkan evidence figure from packaged source data.

The figure is descriptive and domain-separated: provider-recorded port calls,
SAR-derived vessel-activity proxies and population-weighted tropospheric NO2
columns are never combined into a single index or interpreted as a causal chain.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from src.common import configure_style, copy_source, save_figure, sha256, write_json


BLACK = "#111111"
PORT_BLUE = "#0072B2"
SAR_ORANGE = "#D55E00"
SAR_AMBER = "#E69F00"
NO2_PURPLE = "#7851A9"
HISTORY_GREY = "#858D96"
LIGHT_GREY = "#C8CED4"
GRID = "#DCE1E5"
MARCH_SHADE = "#FBF1DE"
LATE_PHASE_SHADE = "#E9F3F7"

FIG_W = 180 / 25.4
FIG_H = (170 * 180 / 183) / 25.4


def configure() -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 6.7,
            "axes.titlesize": 7.0,
            "axes.labelsize": 6.7,
            "xtick.labelsize": 5.8,
            "ytick.labelsize": 5.8,
            "legend.fontsize": 5.5,
            "axes.linewidth": 0.55,
            "lines.linewidth": 0.9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "hormuz-main-figure-2",
            "savefig.facecolor": "white",
            "text.color": BLACK,
            "axes.labelcolor": BLACK,
            "xtick.color": BLACK,
            "ytick.color": BLACK,
        }
    )


def panel_label(
    ax: plt.Axes,
    letter: str,
    title: str,
    *,
    y: float = 1.045,
) -> None:
    # Keep panel headings close to the plotting area without changing their
    # shared baseline or hierarchy.
    y = 1.025 if y <= 1.050 else 1.040
    ax.text(
        -0.008,
        y,
        letter,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.2,
        fontweight="bold",
        color=BLACK,
        clip_on=False,
    )
    ax.text(
        0.017,
        y,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.1,
        fontweight="bold",
        color=BLACK,
        clip_on=False,
    )


def clean(ax: plt.Axes, grid: str | None = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    # Reference lines and phase shading carry the comparison structure; a
    # background grid adds visual clutter at the final print scale.
    ax.grid(False)


def _phase_shading(ax: plt.Axes, labels: bool = False) -> None:
    ax.axvspan(
        pd.Timestamp("2026-03-01", tz="UTC"),
        pd.Timestamp("2026-03-29", tz="UTC"),
        color=MARCH_SHADE,
        zorder=-3,
    )
    ax.axvspan(
        pd.Timestamp("2026-05-01", tz="UTC"),
        pd.Timestamp("2026-07-01", tz="UTC"),
        color=LATE_PHASE_SHADE,
        zorder=-3,
    )
    if labels:
        trans = ax.get_xaxis_transform()
        ax.text(
            pd.Timestamp("2026-03-15", tz="UTC"),
            1.015,
            "1–28 Mar",
            transform=trans,
            ha="center",
            va="bottom",
            fontsize=5.25,
            color=BLACK,
        )
        ax.text(
            pd.Timestamp("2026-05-31", tz="UTC"),
            1.015,
            "1 May–30 Jun",
            transform=trans,
            ha="center",
            va="bottom",
            fontsize=5.25,
            color=BLACK,
        )


def _validate_source(source: pd.DataFrame) -> dict[str, Any]:
    if source.shape != (240, 78):
        raise ValueError(f"Figure 2 packaged source shape changed: {source.shape}")
    counts = source["source_section"].value_counts().to_dict()
    if counts != {"retained_figure_content": 231, "acute_joint_extremeness": 9}:
        raise ValueError(f"Figure 2 source-section contract changed: {counts}")
    record_counts = source["record_type"].value_counts(dropna=False).to_dict()
    required = {
        "daily_port": 181,
        "sar_date_timeline": 45,
        "year_point": 5,
        "bootstrap_contrast": 4,
    }
    for key, expected in required.items():
        if int(record_counts.get(key, 0)) != expected:
            raise ValueError(f"Figure 2 {key} row count changed: {record_counts.get(key)}")
    eligible_sar = source.loc[
        source["record_type"].eq("sar_date_timeline")
        & source["primary_timeline_eligible"].eq(True)
    ]
    if len(eligible_sar) != 37:
        raise ValueError(f"Expected 37 eligible SAR dates, got {len(eligible_sar)}")
    return {
        "source_sections": counts,
        "record_type_counts": {
            str(k): int(v) for k, v in record_counts.items() if pd.notna(k)
        },
        "eligible_sar_dates": len(eligible_sar),
    }


def _draw_contrast_inset(ax: plt.Axes, source: pd.DataFrame) -> None:
    contrasts = source.loc[source["record_type"].eq("bootstrap_contrast")].set_index(
        "contrast_id"
    )
    rows = [
        ("Port calls", contrasts.loc["port_2026_minus_historical_min"], PORT_BLUE),
        ("SAR proxy", contrasts.loc["sar_2026_minus_historical_max"], SAR_AMBER),
    ]
    inset = ax.inset_axes([0.688, 0.645, 0.292, 0.280])
    inset.set_facecolor("#FBFBFA")
    inset.axvline(0, color=BLACK, lw=0.55, ls=(0, (2.2, 1.6)), zorder=0)
    for y, (label, row, color) in zip([1, 0], rows, strict=True):
        inset.hlines(y, row.q025, row.q975, color=color, lw=1.35, zorder=2)
        inset.plot(
            row.q500,
            y,
            marker="D",
            ms=3.5,
            mfc=color,
            mec="white",
            mew=0.35,
            zorder=3,
        )
    inset.set_yticks([1, 0], ["Port calls", "SAR proxy"])
    inset.set_xlim(-65, 45)
    inset.set_xticks([-50, 0, 25])
    inset.set_ylim(-0.55, 1.55)
    inset.tick_params(axis="both", labelsize=5.0, length=1.8, pad=1.2, colors=BLACK)
    inset.set_title(
        "2026 minus reselected historical extreme",
        fontsize=5.35,
        fontweight="bold",
        loc="left",
        pad=2.0,
        color=BLACK,
    )
    inset.set_xlabel("Difference (percentage points)", fontsize=5.0, labelpad=1.2)
    clean(inset, "x")
    for spine in inset.spines.values():
        spine.set_visible(True)
        spine.set_color("#B8C0C5")
        spine.set_linewidth(0.45)


def draw_panel_a(ax: plt.Axes, source: pd.DataFrame) -> None:
    panel_label(ax, "a", "Khor Fakkan: March port-call and SAR-proxy changes")
    points = source.loc[source["record_type"].eq("year_point")].sort_values("year")
    offsets = {
        2022: (2.6, -3.9),
        2023: (2.6, 2.5),
        2024: (2.6, 2.5),
        2025: (2.6, -3.9),
        2026: (3.5, 3.0),
    }
    for row in points.itertuples(index=False):
        year = int(row.year)
        focal = year == 2026
        color = SAR_ORANGE if focal else HISTORY_GREY
        marker = "D" if focal else "o"
        size = 7.0 if focal else 4.9
        ax.errorbar(
            row.port_percent_change,
            row.sar_percent_change,
            xerr=[
                [row.port_percent_change - row.port_ci95_lower],
                [row.port_ci95_upper - row.port_percent_change],
            ],
            yerr=[
                [row.sar_percent_change - row.sar_ci95_lower],
                [row.sar_ci95_upper - row.sar_percent_change],
            ],
            fmt=marker,
            ms=size,
            color=color,
            ecolor=color,
            elinewidth=1.05 if focal else 0.8,
            capsize=2.4,
            markeredgecolor="white",
            markeredgewidth=0.35,
            zorder=5 if focal else 3,
        )
        dx, dy = offsets[year]
        ax.text(
            row.port_percent_change + dx,
            row.sar_percent_change + dy,
            str(year),
            fontsize=5.75,
            color=BLACK,
            fontweight="bold" if focal else "normal",
            zorder=6,
        )

    ax.axhline(0, color=BLACK, lw=0.65, ls=(0, (3, 2)), zorder=1)
    ax.axvline(0, color=BLACK, lw=0.65, ls=(0, (3, 2)), zorder=1)
    ax.set_xlim(-112, 82)
    ax.set_ylim(-20, 58)
    ax.set_xticks([-100, -75, -50, -25, 0, 25, 50, 75])
    ax.set_yticks([-20, -10, 0, 10, 20, 30, 40, 50])
    ax.set_xlabel("Port-call change, 1–28 Mar vs 1 Jan–28 Feb (%)")
    ax.set_ylabel("SAR-proxy change, 1–28 Mar vs 1 Jan–28 Feb (%)")
    clean(ax, "both")
    _draw_contrast_inset(ax, source)


def _phase_rows(source: pd.DataFrame) -> pd.DataFrame:
    retained = source.loc[source["source_section"].eq("retained_figure_content")]
    phase = retained.loc[
        retained["phase"].isin(["baseline", "acute_full", "late_phase"])
        & retained["buffer_km"].eq(20)
    ].copy()
    phase = phase.drop_duplicates(
        subset=[
            "analysis_id",
            "buffer_km",
            "phase",
            "no2_mean_anomaly_mol_m2",
            "no2_equal_year_historical_mean_mol_m2",
            "no2_current_bootstrap_ci95_lower",
            "no2_current_bootstrap_ci95_upper",
        ]
    )
    if len(phase) != 3:
        raise ValueError(f"Expected three unique 20-km phase rows, got {len(phase)}")
    return phase


def draw_panel_b(container: plt.Axes, source: pd.DataFrame) -> None:
    container.set_axis_off()
    panel_label(
        container,
        "b",
        "Khor Fakkan activity and phase-level NO$_2$",
        y=1.075,
    )
    retained = source.loc[source["source_section"].eq("retained_figure_content")]
    daily = retained.loc[retained["record_type"].eq("daily_port")].copy()
    daily["date"] = pd.to_datetime(daily["utc_date"], utc=True)
    sar = retained.loc[
        retained["record_type"].eq("sar_date_timeline")
        & retained["primary_timeline_eligible"].eq(True)
    ].copy()
    sar["date"] = pd.to_datetime(sar["utc_date"], utc=True)
    phase = _phase_rows(source)
    axes = [
        container.inset_axes([0.000, 0.690, 0.975, 0.235]),
        container.inset_axes([0.000, 0.345, 0.975, 0.235]),
        container.inset_axes([0.000, 0.000, 0.975, 0.235]),
    ]

    # PortWatch: retain every daily observation and display the declared 7-day
    # rolling mean for legibility.  No model fit or interpolation is added.
    ax = axes[0]
    _phase_shading(ax, True)
    ax.scatter(
        daily.date,
        daily.portwatch_current_calls,
        s=5.0,
        color=PORT_BLUE,
        alpha=0.34,
        edgecolor="none",
        zorder=2,
    )
    current = (
        daily.set_index("date").portwatch_current_calls.rolling(7, center=True, min_periods=3).mean()
    )
    history = (
        daily.set_index("date")
        .portwatch_historical_same_calendar_mean.rolling(7, center=True, min_periods=3)
        .mean()
    )
    ax.plot(current.index, current, color=PORT_BLUE, lw=1.25, zorder=3)
    ax.plot(history.index, history, color=HISTORY_GREY, lw=0.9, ls=(0, (3, 2)), zorder=3)
    ax.text(
        0.0,
        1.025,
        "PortWatch calls per day",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.6,
        color=BLACK,
    )
    ax.set_ylim(-0.08, 4.25)
    clean(ax)
    ax.tick_params(axis="x", labelbottom=False)
    xlab = pd.Timestamp("2026-07-03", tz="UTC")
    ax.text(
        xlab,
        float(current.dropna().iloc[-1]) + 0.12,
        "2026, 7-d mean",
        fontsize=5.5,
        va="bottom",
        color=BLACK,
    )
    ax.text(
        xlab,
        float(history.dropna().iloc[-1]) - 0.10,
        "history, 7-d mean",
        fontsize=5.5,
        va="top",
        color=BLACK,
    )

    # SAR: paired current and orbit/date-matched historical densities on all 37
    # eligible dates.
    ax = axes[1]
    _phase_shading(ax)
    ax.vlines(
        sar.date,
        sar.sar_historical_matched_median_density_per_100_km2,
        sar.sar_current_density_per_100_km2,
        color=LIGHT_GREY,
        lw=0.65,
        zorder=1,
    )
    ax.scatter(
        sar.date,
        sar.sar_historical_matched_median_density_per_100_km2,
        s=10,
        facecolor="white",
        edgecolor=HISTORY_GREY,
        lw=0.65,
        zorder=2,
    )
    ax.scatter(
        sar.date,
        sar.sar_current_density_per_100_km2,
        s=11,
        color=SAR_AMBER,
        edgecolor=BLACK,
        lw=0.25,
        zorder=3,
    )
    ax.text(
        0.0,
        1.025,
        "SAR proxy per 100 km²",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.6,
        color=BLACK,
    )
    clean(ax)
    ax.tick_params(axis="x", labelbottom=False)
    last = sar.sort_values("date").iloc[-1]
    ax.text(
        last["date"] + pd.Timedelta(days=4),
        last["sar_current_density_per_100_km2"],
        "2026",
        fontsize=5.4,
        va="center",
        color=BLACK,
    )
    ax.text(
        last["date"] + pd.Timedelta(days=4),
        last["sar_historical_matched_median_density_per_100_km2"],
        "matched history",
        fontsize=5.4,
        va="center",
        color=BLACK,
    )

    # NO2: phase-level population-weighted anomalies, with current-year
    # bootstrap intervals and equal-year historical means kept separate.
    ax = axes[2]
    _phase_shading(ax)
    mids = {
        "baseline": pd.Timestamp("2026-01-30", tz="UTC"),
        "acute_full": pd.Timestamp("2026-03-15", tz="UTC"),
        "late_phase": pd.Timestamp("2026-05-31", tz="UTC"),
    }
    for row in phase.itertuples(index=False):
        x = mids[row.phase]
        lo = row.no2_current_bootstrap_ci95_lower * 1e5
        hi = row.no2_current_bootstrap_ci95_upper * 1e5
        current_value = row.no2_mean_anomaly_mol_m2 * 1e5
        history_value = row.no2_equal_year_historical_mean_mol_m2 * 1e5
        ax.vlines(x, lo, hi, color=NO2_PURPLE, lw=1.15, zorder=2)
        ax.scatter([x], [current_value], marker="D", s=18, color=NO2_PURPLE, edgecolor="white", lw=0.35, zorder=3)
        ax.scatter([x], [history_value], s=14, facecolor="white", edgecolor=HISTORY_GREY, lw=0.7, zorder=3)
        ax.text(
            x,
            hi + 0.35,
            f"{int(row.no2_valid_days_2026)}/{int(row.calendar_days_2026)} d",
            ha="center",
            va="bottom",
            fontsize=5.4,
            color=BLACK,
        )
    ax.axhline(0, color=BLACK, lw=0.6)
    ax.set_ylim(-1.8, 11.8)
    ax.text(
        0.0,
        1.025,
        "Population-weighted NO$_2$ anomaly (10$^{-5}$ mol m$^{-2}$)",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.6,
        color=BLACK,
    )
    clean(ax)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.set_xlabel("2026 (UTC)")
    late_phase = phase.loc[phase["phase"].eq("late_phase")].iloc[0]
    ax.text(
        pd.Timestamp("2026-06-08", tz="UTC"),
        late_phase["no2_mean_anomaly_mol_m2"] * 1e5,
        "2026 (95% CI)",
        fontsize=5.4,
        va="center",
        color=BLACK,
    )
    ax.text(
        pd.Timestamp("2026-06-08", tz="UTC"),
        late_phase["no2_equal_year_historical_mean_mol_m2"] * 1e5,
        "history",
        fontsize=5.4,
        va="center",
        color=BLACK,
    )

    for axis in axes:
        axis.set_xlim(
            pd.Timestamp("2026-01-01", tz="UTC"),
            pd.Timestamp("2026-07-15", tz="UTC"),
        )
        axis.tick_params(axis="both", labelsize=5.8, length=2, pad=1.2, colors=BLACK)


def _late_event_sensitivity(source: pd.DataFrame) -> pd.DataFrame:
    retained = source.loc[source["source_section"].eq("retained_figure_content")]
    sensitivity = retained.loc[
        retained["phase"].eq("late_phase") & retained["buffer_km"].isin([10, 20, 30])
    ].copy()
    sensitivity = sensitivity.drop_duplicates(
        subset=[
            "analysis_id",
            "buffer_km",
            "phase",
            "no2_change_vs_historical_mol_m2",
            "no2_change_vs_historical_bootstrap_ci95_lower",
            "no2_change_vs_historical_bootstrap_ci95_upper",
        ]
    ).sort_values("buffer_km", ascending=False)
    if len(sensitivity) != 3 or set(sensitivity["buffer_km"].astype(int)) != {10, 20, 30}:
        raise ValueError("Expected one May–June row for each 10, 20 and 30 km domain")
    return sensitivity


def draw_panel_c(ax: plt.Axes, source: pd.DataFrame) -> None:
    panel_label(ax, "c", "May–June NO$_2$ anomaly contrast", y=1.075)
    sensitivity = _late_event_sensitivity(source)
    y = np.arange(len(sensitivity))
    scale = 1e5
    x = sensitivity.no2_change_vs_historical_mol_m2.to_numpy(float) * scale
    lo = sensitivity.no2_change_vs_historical_bootstrap_ci95_lower.to_numpy(float) * scale
    hi = sensitivity.no2_change_vs_historical_bootstrap_ci95_upper.to_numpy(float) * scale

    ax.axvline(0, color=BLACK, lw=0.7)
    for yi, row in zip(y, sensitivity.itertuples(index=False), strict=True):
        primary = int(row.buffer_km) == 20
        ax.hlines(
            yi,
            row.no2_change_vs_historical_bootstrap_ci95_lower * scale,
            row.no2_change_vs_historical_bootstrap_ci95_upper * scale,
            color=NO2_PURPLE,
            lw=1.45 if primary else 1.0,
            zorder=2,
        )
        ax.scatter(
            row.no2_change_vs_historical_mol_m2 * scale,
            yi,
            marker="D" if primary else "o",
            color=NO2_PURPLE,
            s=22 if primary else 17,
            zorder=3,
            edgecolor="white",
            lw=0.4,
        )
        ax.text(
            row.no2_change_vs_historical_bootstrap_ci95_upper * scale + 0.08,
            yi,
            (
                f"{row.no2_change_vs_historical_mol_m2 * scale:+.2f} "
                f"[{row.no2_change_vs_historical_bootstrap_ci95_lower * scale:+.2f}–"
                f"{row.no2_change_vs_historical_bootstrap_ci95_upper * scale:+.2f}]"
            ),
            ha="left",
            va="center",
            fontsize=4.85,
            color=BLACK,
        )

    labels = []
    for row in sensitivity.itertuples(index=False):
        primary = " (primary)" if int(row.buffer_km) == 20 else ""
        labels.append(f"{int(row.buffer_km)} km{primary}\n{int(row.no2_valid_days_2026)} valid d")
    ax.set_yticks(y, labels)
    for tick, row in zip(ax.get_yticklabels(), sensitivity.itertuples(index=False), strict=True):
        if int(row.buffer_km) == 20:
            tick.set_fontweight("bold")
    ax.text(
        0.0,
        1.012,
        "Population coverage: 98.7–99.6%",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.15,
        color=BLACK,
    )
    ax.set_xlabel("Difference from 2022–2025 history\n(10$^{-5}$ mol m$^{-2}$)")
    # Reserve enough in-axis room for the numerical interval labels so exported
    # raster and vector files never clip them at the right boundary.
    upper = max(hi) + 2.45
    ax.set_xlim(-0.15, upper)
    ax.set_ylim(-0.55, len(sensitivity) - 0.45)
    ax.tick_params(axis="both", labelsize=5.45, length=2, pad=1.5, colors=BLACK)
    clean(ax, "x")
    # The zero reference line is the sole left-side vertical guide.
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


def reproduce(data_root: Path, output_root: Path) -> dict[str, Any]:
    source_path = data_root / "files/main_figures/Figure_2_source_data.csv"
    source = pd.read_csv(source_path)
    source_checks = _validate_source(source)
    configure_style("public-lightweight-figure-2")
    configure()

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    gs = fig.add_gridspec(
        2,
        2,
        height_ratios=[0.45, 0.55],
        width_ratios=[0.71, 0.29],
        left=0.078,
        right=0.968,
        bottom=0.072,
        top=0.945,
        wspace=0.27,
        hspace=0.29,
    )
    draw_panel_a(fig.add_subplot(gs[0, :]), source)
    draw_panel_b(fig.add_subplot(gs[1, 0]), source)
    draw_panel_c(fig.add_subplot(gs[1, 1]), source)

    artifact = save_figure(fig, "Figure_2", output_root)
    copied = copy_source(source_path, output_root)
    artifact.update(
        {
            "panels": 3,
            "panel_ids": ["a", "b", "c"],
            "source_rows": len(source),
            "source_columns": len(source.columns),
            "source_sha256": sha256(source_path),
            "copied_source_sha256": sha256(copied),
            "source_checks": source_checks,
            "panel_mapping": {
                "a": {"record_types": ["year_point", "bootstrap_contrast"], "rows": 9},
                "b": {
                    "record_types": ["daily_port", "sar_date_timeline", "20-km phase summaries"],
                    "daily_port_rows": 181,
                    "eligible_sar_dates": 37,
                    "no2_phase_rows": 3,
                },
                "c": {"record_types": ["May–June fixed-domain NO2 anomaly contrasts"], "rows": 3},
            },
            "render_mode": "source_data_redraw_no_estimation",
            "scientific_estimation_runs": 0,
            "bootstrap_runs": 0,
        }
    )
    write_json(output_root / "qa/Figure_2_reproduction.json", artifact)
    write_json(
        output_root / "logs/Figure_2_render.json",
        {
            "figure": "Figure_2",
            "status": "render_complete",
            "source_sha256": artifact["source_sha256"],
            "source_checks": source_checks,
            "outputs": artifact["outputs"],
        },
    )
    return artifact


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.data_root, args.output_root), indent=2, sort_keys=True))
