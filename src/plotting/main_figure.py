"""Plotting functions for the main regional maritime-activity figure.

The figure keeps the full regional discovery screen visible: six analytical
waters, all 21 available PortWatch series and every eligible fold-1 SAR scene.  The
three unavailable candidates remain documented in the source data and
Supplementary Table 1 rather than occupying empty figure rows.  The
layout is deliberately descriptive.  It does not turn the post-result Khor
Fakkan case into a preregistered regional result and it does not interpret
vessel-like labels as verified vessels.
"""
from __future__ import annotations

from typing import Any

import geopandas as gpd
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from shapely.geometry import box


LAND = "#E8E3D9"
BLACK = "#111111"
BLUE = "#0072B2"
ORANGE = "#D55E00"
MID_GREY = "#737B84"
LIGHT_GREY = "#C5CBD1"
GRID = "#DCE1E5"
SEA = "#EDF5F8"
MARCH_SHADE = "#FBF1DE"
LATE_PHASE_SHADE = "#E9F3F7"

FIG_W = 180 / 25.4
FIG1_H = (170 * 180 / 183) / 25.4

WINDOW_LABELS = [
    "1–14\nMar",
    "15–28\nMar",
    "29 Mar–\n11 Apr",
    "12–25\nApr",
    "26–30\nApr",
    "May",
    "June",
]

WINDOW_RANGES = {
    "long_baseline": ("2000-01-01", "2000-03-01"),
    "early": ("2000-03-01", "2000-03-15"),
    "F1": ("2000-03-15", "2000-03-29"),
    "F2": ("2000-03-29", "2000-04-12"),
    "F3": ("2000-04-12", "2000-04-26"),
    "F4_tail": ("2000-04-26", "2000-05-01"),
    "May": ("2000-05-01", "2000-06-01"),
    "June": ("2000-06-01", "2000-07-01"),
}

SAR_ORDER = [
    "strait_of_hormuz_transit_gate",
    "bandar_abbas_port_approach",
    "jebel_ali_port_waiting_area",
    "fujairah_port_anchorage",
    "sohar_port_anchorage",
    "khor_fakkan_fujairah_adjacent_secondary_water",
]

SAR_LABELS = {
    "strait_of_hormuz_transit_gate": "Hormuz",
    "bandar_abbas_port_approach": "Bandar Abbas",
    "jebel_ali_port_waiting_area": "Jebel Ali",
    "fujairah_port_anchorage": "Fujairah",
    "sohar_port_anchorage": "Sohar",
    "khor_fakkan_fujairah_adjacent_secondary_water": "Khor Fakkan*",
}


def configure() -> None:
    """Configure typography at the final 180-mm figure width."""
    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 6.7,
            "axes.titlesize": 7.0,
            "axes.labelsize": 6.7,
            "xtick.labelsize": 6.0,
            "ytick.labelsize": 6.0,
            "legend.fontsize": 5.8,
            "axes.linewidth": 0.55,
            "lines.linewidth": 0.9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "hormuz-main-figure-1",
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
    y: float = 1.035,
) -> None:
    """Draw a compact Nature-style panel label and factual title."""
    ax.text(
        -0.006,
        y,
        letter,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.2,
        fontweight="bold",
        clip_on=False,
    )
    ax.text(
        0.018,
        y,
        title,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.1,
        fontweight="bold",
        clip_on=False,
    )


def clean(ax: plt.Axes, grid: str | None = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(axis=grid, color=GRID, lw=0.38, zorder=0)


def _plot_land(
    ax: plt.Axes,
    land_source: gpd.GeoDataFrame,
    extent: tuple[float, float, float, float],
) -> None:
    clipper = box(extent[0], extent[2], extent[1], extent[3])
    land = land_source.copy()
    land["geometry"] = land.geometry.intersection(clipper)
    land = land.loc[~land.geometry.is_empty]
    land.plot(
        ax=ax,
        facecolor=LAND,
        edgecolor="#AAA397",
        linewidth=0.32,
        zorder=1,
    )


def _water_anchor(waters: gpd.GeoDataFrame, region_id: str):
    geom = waters.loc[waters["region_id"].eq(region_id), "geometry"].iloc[0]
    return geom.representative_point()


def _draw_map_frame(
    ax: plt.Axes,
    data: dict[str, Any],
    extent: tuple[float, float, float, float],
    positions: dict[str, tuple[float, float, str]],
    scale_km: float,
    *,
    ticks: bool = True,
    north: bool = True,
) -> None:
    waters = data["waters"].to_crs("EPSG:4326")
    ports = data["ports"].to_crs("EPSG:4326")
    ax.set_facecolor(SEA)
    _plot_land(ax, data["land"], extent)

    for row in waters.itertuples(index=False):
        focal = row.region_id == SAR_ORDER[-1]
        gpd.GeoSeries([row.geometry], crs=waters.crs).plot(
            ax=ax,
            facecolor="#F3BE70" if focal else "#91C7DD",
            edgecolor=ORANGE if focal else BLUE,
            alpha=0.88,
            linewidth=1.0 if focal else 0.75,
            zorder=4,
        )

    ports.plot(
        ax=ax,
        marker="D",
        markersize=12,
        facecolor=BLACK,
        edgecolor="white",
        linewidth=0.45,
        zorder=7,
    )

    for region_id, (tx, ty, align) in positions.items():
        anchor = _water_anchor(waters, region_id)
        focal = region_id == SAR_ORDER[-1]
        ax.annotate(
            SAR_LABELS[region_id].replace("*", ""),
            xy=(anchor.x, anchor.y),
            xytext=(tx, ty),
            ha=align,
            va="center",
            fontsize=5.8,
            fontweight="bold" if focal else "normal",
            color=BLACK,
            arrowprops={
                "arrowstyle": "-",
                "lw": 0.52,
                "color": ORANGE if focal else BLACK,
                "shrinkA": 1.5,
                "shrinkB": 1.5,
            },
            zorder=8,
        )

    ax.set_xlim(extent[:2])
    ax.set_ylim(extent[2:])
    ax.set_aspect("equal", adjustable="box")

    if ticks:
        xticks = [x for x in (55, 56, 57) if extent[0] <= x <= extent[1]]
        yticks = [y for y in (25, 26, 27) if extent[2] <= y <= extent[3]]
        ax.set_xticks(xticks)
        ax.set_yticks(yticks)
        ax.set_xticklabels([f"{x}° E" for x in xticks])
        ax.set_yticklabels([f"{y}° N" for y in yticks], rotation=90, va="center")
        ax.tick_params(length=2.2, width=0.55, pad=1.6, labelsize=5.8)
    else:
        ax.set_xticks([])
        ax.set_yticks([])

    if north:
        ax.annotate(
            "N",
            xy=(0.94, 0.92),
            xytext=(0.94, 0.81),
            xycoords="axes fraction",
            ha="center",
            va="bottom",
            fontsize=5.9,
            fontweight="bold",
            arrowprops={"arrowstyle": "-|>", "lw": 0.7, "color": BLACK},
        )

    x0 = extent[0] + 0.08 * (extent[1] - extent[0])
    y0 = extent[2] + 0.055 * (extent[3] - extent[2])
    dx = scale_km / (111.32 * np.cos(np.deg2rad(np.mean(extent[2:]))))
    ax.plot([x0, x0 + dx], [y0, y0], color=BLACK, lw=1.1, zorder=9)
    ax.text(
        x0 + dx / 2,
        y0 + 0.025 * (extent[3] - extent[2]),
        f"{scale_km:g} km",
        ha="center",
        va="bottom",
        fontsize=5.3,
        color=BLACK,
    )


def draw_map(ax: plt.Axes, data: dict[str, Any]) -> None:
    """Draw the complete regional frame with a clean east-coast inset."""
    ax.set_axis_off()
    panel_label(ax, "a", "Analytical waters and PortWatch points", y=1.095)

    # Fill the panel container so that panels a and b share the same visible
    # top and bottom plotting boundaries.  The wider top-left grid cell keeps
    # the geographic aspect ratio without compressing the map.
    regional = ax.inset_axes([0.006, 0.000, 0.988, 1.000])
    regional_positions = {
        "strait_of_hormuz_transit_gate": (56.91, 26.55, "right"),
        "bandar_abbas_port_approach": (55.78, 27.16, "left"),
        "jebel_ali_port_waiting_area": (54.74, 24.82, "left"),
        "sohar_port_anchorage": (56.90, 24.39, "right"),
    }
    _draw_map_frame(
        regional,
        data,
        (54.68, 56.95, 24.32, 27.22),
        regional_positions,
        50,
    )
    regional.text(
        55.94,
        25.79,
        "Gulf of Oman",
        fontsize=5.5,
        fontstyle="italic",
        rotation=-23,
        color=BLACK,
        zorder=6,
    )

    # The dashed rectangle is the exact geographic extent of the inset.
    # Use a near-square geographic extent.  The previous tall, narrow extent
    # forced the equal-aspect inset to collapse into a thin strip and made the
    # two east-coast waters and labels appear crowded.
    detail_extent = (56.15, 56.75, 24.92, 25.62)
    regional.add_patch(
        Rectangle(
            (detail_extent[0], detail_extent[2]),
            detail_extent[1] - detail_extent[0],
            detail_extent[3] - detail_extent[2],
            fill=False,
            ec=BLACK,
            lw=0.65,
            ls=(0, (2.2, 1.5)),
            zorder=9,
        )
    )

    # Position the detail where it covers no analytical water in the regional
    # frame.  A white keyline keeps the two spatial scales unambiguous.
    detail = regional.inset_axes([0.035, 0.555, 0.52, 0.415])
    detail_positions = {
        "fujairah_port_anchorage": (56.70, 25.08, "right"),
        "khor_fakkan_fujairah_adjacent_secondary_water": (56.19, 25.50, "left"),
    }
    _draw_map_frame(
        detail,
        data,
        detail_extent,
        detail_positions,
        10,
        ticks=False,
        north=False,
    )
    for spine in detail.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.7)
        spine.set_color(BLACK)
    detail.text(
        0.035,
        0.965,
        "East-coast detail",
        transform=detail.transAxes,
        ha="left",
        va="top",
        fontsize=5.35,
        fontweight="bold",
        color=BLACK,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.7, "alpha": 0.88},
    )

    ax.legend(
        handles=[
            Patch(facecolor="#91C7DD", edgecolor=BLUE, label="analytical water"),
            Patch(facecolor="#F3BE70", edgecolor=ORANGE, label="post-result focal*"),
            Line2D([], [], marker="D", ms=4.1, lw=0, mfc=BLACK, mec="white", label="PortWatch point"),
        ],
        loc="upper left",
        bbox_to_anchor=(0.006, -0.052),
        frameon=False,
        fontsize=5.85,
        ncol=3,
        handlelength=1.35,
        handleheight=1.15,
        columnspacing=0.75,
        handletextpad=0.40,
        borderaxespad=0,
    )


def draw_portwatch(ax: plt.Axes, pw: pd.DataFrame) -> None:
    """Draw the 21 available series from the 24-candidate provider screen."""
    panel_label(ax, "b", "Port-call change across 21 available series", y=1.095)
    labels = (
        pw[["candidate_id", "display_name", "row_order", "data_available"]]
        .drop_duplicates()
        .sort_values("row_order")
    )
    labels = labels.loc[labels["data_available"].astype(bool)].reset_index(drop=True)
    display_row = {candidate_id: i for i, candidate_id in enumerate(labels["candidate_id"])}
    n_rows = len(labels)
    vals = np.full((n_rows, 7), np.nan)
    for row in pw.loc[pw["data_available"].astype(bool)].itertuples(index=False):
        y = display_row[row.candidate_id]
        vals[y, int(row.window_order)] = (
            row.relative_change_vs_2026_long_baseline_percent
        )

    cmap = ListedColormap(
        ["#2F6F96", "#679BB6", "#AFC8D6", "#F7F5F0", "#E8C3A6", "#D99163", "#B95F36"]
    )
    cmap.set_bad("white")
    bounds = [-100, -75, -50, -25, 25, 50, 75, 100]
    norm = BoundaryNorm(bounds, cmap.N, clip=True)
    im = ax.imshow(
        np.clip(vals, -100, 100),
        aspect="auto",
        cmap=cmap,
        norm=norm,
        interpolation="none",
    )

    for y in range(n_rows):
        for x in range(7):
            ax.add_patch(
                Rectangle(
                    (x - 0.5, y - 0.5),
                    1,
                    1,
                    fill=False,
                    edgecolor="white",
                    lw=0.42,
                )
            )
            if np.isnan(vals[y, x]):
                ax.text(x, y, "–", ha="center", va="center", fontsize=5.7, color=BLACK)
            elif vals[y, x] > 100:
                # Retain the saturated colour scale while disclosing values
                # beyond its upper bound.
                ax.plot(
                    x + 0.31,
                    y,
                    marker=">",
                    ms=2.4,
                    mfc="white",
                    mec=BLACK,
                    mew=0.35,
                    clip_on=True,
                    zorder=4,
                )

    names = labels["display_name"].astype(str).tolist()
    names[names.index("Khor Fakkan")] = "Khor Fakkan*"
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(names, fontsize=5.45, color=BLACK)
    for tick in ax.get_yticklabels():
        if tick.get_text().startswith("Khor Fakkan"):
            tick.set_fontweight("bold")

    ax.set_xticks(range(7))
    ax.set_xticklabels(WINDOW_LABELS, fontsize=5.55, color=BLACK)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=2)
    ax.tick_params(axis="y", length=0, pad=2)

    # The focal outline discloses the post-result case used downstream.
    focal_y = names.index("Khor Fakkan*")
    ax.add_patch(
        Rectangle(
            (-0.5, focal_y - 0.5),
            7,
            1,
            fill=False,
            edgecolor=ORANGE,
            linewidth=1.0,
            zorder=6,
            clip_on=False,
        )
    )
    # A complete, light keyline makes the top-row plot boundary read as the
    # rectangular counterpart to the map frame in panel a.
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(BLACK)
        spine.set_linewidth(0.50)

    cax = ax.inset_axes([0.10, -0.112, 0.80, 0.034])
    cb = plt.colorbar(
        im,
        cax=cax,
        orientation="horizontal",
        ticks=[-100, -50, 0, 50, 100],
        boundaries=bounds,
    )
    cb.ax.set_xticklabels(["−100", "−50", "0", "+50", "+100"])
    cb.ax.tick_params(labelsize=5.45, length=1.9, pad=1.1, colors=BLACK)
    cb.outline.set_linewidth(0.55)
    cb.set_label(
        "Change from 1 Jan–28 Feb 2026 baseline (%)",
        fontsize=5.65,
        labelpad=1.2,
        color=BLACK,
    )


def _draw_window_medians(ax: plt.Axes, current: pd.DataFrame, color: str) -> None:
    for window, (start_s, end_s) in WINDOW_RANGES.items():
        values = current.loc[
            current["window"].eq(window), "vessel_like_density_per_100_km2"
        ].dropna()
        if values.empty:
            continue
        start = pd.Timestamp(start_s, tz="UTC")
        end = pd.Timestamp(end_s, tz="UTC")
        pad = pd.Timedelta(hours=10)
        mid = start + (end - start) / 2
        median = float(values.median())
        ax.hlines(
            median,
            start + pad,
            end - pad,
            color=color,
            lw=1.80,
            zorder=4,
        )
        ax.plot(
            mid,
            median,
            marker="D",
            ms=2.9,
            mfc=color,
            mec="white",
            mew=0.3,
            zorder=5,
        )


def draw_sar_strips(container: plt.Axes, sar: pd.DataFrame) -> None:
    """Draw all SAR scenes plus exact fixed-window medians for 2026."""
    container.set_axis_off()
    panel_label(
        container,
        "c",
        "All SAR scenes and 2026 fixed-window medians (n=1,360)",
    )
    container.text(
        0.076,
        0.976,
        "Vessel-like labels per 100 km²; row-specific y-scales",
        transform=container.transAxes,
        fontsize=5.70,
        color=BLACK,
        ha="left",
        va="top",
    )

    positions = [
        (0.005, 0.675, 0.465, 0.225),
        (0.535, 0.675, 0.465, 0.225),
        (0.005, 0.365, 0.465, 0.225),
        (0.535, 0.365, 0.465, 0.225),
        (0.005, 0.055, 0.465, 0.225),
        (0.535, 0.055, 0.465, 0.225),
    ]

    for i, aoi in enumerate(SAR_ORDER):
        ax = container.inset_axes(positions[i])
        row = sar.loc[sar["aoi_id"].eq(aoi)].copy()
        row["date"] = pd.to_datetime(row["plot_date"], utc=True)
        hist = row.loc[row["year"].lt(2026)]
        current = row.loc[row["year"].eq(2026)]
        focal = aoi == SAR_ORDER[-1]
        color = ORANGE if focal else BLUE

        ax.axvspan(
            pd.Timestamp("2000-03-01", tz="UTC"),
            pd.Timestamp("2000-03-29", tz="UTC"),
            color=MARCH_SHADE,
            zorder=-3,
        )
        ax.axvspan(
            pd.Timestamp("2000-05-01", tz="UTC"),
            pd.Timestamp("2000-07-01", tz="UTC"),
            color=LATE_PHASE_SHADE,
            zorder=-3,
        )
        ax.scatter(
            hist["date"],
            hist["vessel_like_density_per_100_km2"],
            s=4.4,
            facecolor=LIGHT_GREY,
            edgecolor="none",
            alpha=0.42,
            rasterized=True,
            zorder=1,
        )
        ax.scatter(
            current["date"],
            current["vessel_like_density_per_100_km2"],
            s=7.8,
            facecolor=color,
            edgecolor="white",
            linewidth=0.2,
            alpha=0.76,
            zorder=3,
        )
        _draw_window_medians(ax, current, color)

        ax.set_xlim(
            pd.Timestamp("2000-01-01", tz="UTC"),
            pd.Timestamp("2000-07-02", tz="UTC"),
        )
        ymax = max(float(row["vessel_like_density_per_100_km2"].max()) * 1.08, 1)
        ax.set_ylim(-0.025 * ymax, ymax)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=3, min_n_ticks=2))
        ax.tick_params(axis="y", labelsize=5.35, length=1.8, pad=1.2, colors=BLACK)
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        if i < 4:
            ax.tick_params(axis="x", labelbottom=False, length=1.8)
        else:
            ax.tick_params(axis="x", labelsize=5.45, length=2, pad=1.2, colors=BLACK)
        clean(ax, "y")
        # Keep every small multiple rectangular and align the two columns to
        # the shared outer left and right boundaries of the complete figure.
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(BLACK)
            spine.set_linewidth(0.48)
        ax.text(
            0.0,
            1.025,
            SAR_LABELS[aoi],
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=5.95,
            fontweight="bold" if focal else "normal",
            color=BLACK,
            clip_on=False,
        )
        ax.text(
            1.0,
            1.025,
            f"n={len(row)}",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=5.35,
            color=BLACK,
            clip_on=False,
        )

    container.legend(
        handles=[
            Line2D([], [], marker="o", ms=3.2, lw=0, color=LIGHT_GREY, label="2022–2025 scenes"),
            Line2D([], [], marker="o", ms=3.5, lw=0, color=BLUE, label="2026 scenes"),
            Line2D([], [], marker="D", ms=3.1, lw=1.7, color=BLUE, label="2026 window median"),
            Line2D([], [], marker="D", ms=3.1, lw=1.7, color=ORANGE, label="post-result focal*"),
        ],
        loc="upper right",
        bbox_to_anchor=(0.996, 1.012),
        ncol=4,
        frameon=False,
        fontsize=5.25,
        handletextpad=0.35,
        columnspacing=0.8,
        borderaxespad=0,
    )
