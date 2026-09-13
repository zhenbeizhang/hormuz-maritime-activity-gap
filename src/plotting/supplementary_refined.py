"""Refined plotting functions for supplementary figures."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from PIL import Image, ImageDraw, ImageFont, ImageOps
from src.plotting import supplementary_base as base
WIDTH_IN = 183 / 25.4

def configure_style() -> None:
    base.configure_style()
    matplotlib.rcParams['svg.hashsalt'] = 'refined-targeted-supplementary-revision'

def panel_title(ax: plt.Axes, letter: str, title: str, title_x: float=0.085) -> None:
    ax.text(0.0, 1.035, letter, transform=ax.transAxes, ha='left', va='bottom', fontsize=8.2, fontweight='bold', color=base.BLACK)
    ax.text(title_x, 1.035, title, transform=ax.transAxes, ha='left', va='bottom', fontsize=7.3, fontweight='bold', color=base.BLACK)

VALIDATION_PERIOD_ORDER = ['pre_event', 'event_early', 'event_mid', 'event_late']
VALIDATION_PERIOD_LABELS = {
    'pre_event': 'Pre-event',
    'event_early': 'Early',
    'event_mid': 'Mid',
    'event_late': 'Late',
}
VALIDATION_PERIOD_COLORS = {
    'pre_event': base.GREY,
    'event_early': base.ORANGE,
    'event_mid': base.VERMILLION,
    'event_late': base.PURPLE,
}
VALIDATION_PERIOD_MARKERS = {
    'pre_event': 'o',
    'event_early': '^',
    'event_mid': 's',
    'event_late': 'D',
}


def _draw_detector_overlap(ax: plt.Axes, source: pd.DataFrame) -> None:
    panel_title(ax, 'a', 'Direction-conditional detector overlap')
    subset = source.loc[source['record_type'].eq('cross_detector_overlap')].copy()
    order = ['Primary to CFAR', 'CFAR to primary', 'Primary to neural', 'Neural to primary']
    display = {
        'Primary to CFAR': 'Primary → CFAR',
        'CFAR to primary': 'CFAR → primary',
        'Primary to neural': 'Primary → neural',
        'Neural to primary': 'Neural → primary',
    }
    subset['_order'] = subset['direction'].map({name: i for i, name in enumerate(order)})
    subset = subset.sort_values('_order')
    y = np.arange(len(subset))[::-1]
    values = 100 * subset['fraction'].to_numpy(float)
    colors = [base.BLUE if method == 'CFAR' else base.GREEN for method in subset['method']]
    for y_value, value, color, row in zip(y, values, colors, subset.itertuples()):
        ax.hlines(y_value, 0, 100, color=base.LIGHT_GREY, lw=3.2, zorder=1)
        ax.hlines(y_value, 0, value, color=color, lw=3.2, zorder=2)
        ax.scatter(value, y_value, s=28, facecolor=color, edgecolor='white', linewidth=0.6, zorder=3)
        x_text, align = (value - 2.4, 'right') if value >= 72 else (value + 2.4, 'left')
        ax.text(
            x_text,
            y_value + 0.24,
            f"{int(row.count)}/{int(row.denominator)} ({value:.1f}%)",
            ha=align,
            va='bottom',
            fontsize=5.2,
            fontweight='bold',
            color=base.BLACK,
        )
    ax.set_yticks(y, [display[value] for value in subset['direction']])
    ax.set_xlim(0, 103)
    ax.set_ylim(-0.55, 3.55)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('Direction-conditional matched detections (%)')
    base.clean_axes(ax, 'x')
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0, pad=3)
    ax.axhline(1.5, color='#BFC4CA', lw=0.55, zorder=0)
    ax.text(101.5, 3.42, '150 m', ha='right', va='top', fontsize=5.0, color=base.BLACK)
    ax.text(101.5, 1.42, '200 m', ha='right', va='top', fontsize=5.0, color=base.BLACK)


def _draw_scene_counts(container: plt.Axes, source: pd.DataFrame) -> None:
    panel_title(container, 'b', 'Scene-level detector counts')
    container.axis('off')
    subset = source.loc[source['record_type'].eq('scene_count_agreement')].copy()
    specifications = [
        ('CFAR', 'CFAR count', [0, 200, 400, 600]),
        ('Neural detector', 'Neural count', [0, 10, 20, 30]),
    ]
    for index, (method, ylabel, yticks) in enumerate(specifications):
        ax = container.inset_axes([0.00 + 0.53 * index, 0.12, 0.46, 0.68])
        method_data = subset.loc[subset['method'].eq(method)].copy()
        for period in VALIDATION_PERIOD_ORDER:
            period_data = method_data.loc[method_data['validation_period'].eq(period)]
            ax.scatter(
                period_data['primary_count'],
                period_data['independent_count'],
                marker=VALIDATION_PERIOD_MARKERS[period],
                s=24,
                facecolor=VALIDATION_PERIOD_COLORS[period],
                edgecolor='white',
                linewidth=0.55,
                alpha=0.95,
                zorder=3,
            )
        ax.set_xlim(40, 82)
        ax.set_xticks([40, 60, 80])
        ax.set_yticks(yticks)
        ax.set_ylim((0, 625) if method == 'CFAR' else (0, 32))
        ax.set_xlabel('Primary xView3 count')
        ax.set_ylabel(ylabel)
        base.clean_axes(ax, 'both')
        rho = float(method_data['spearman_rho'].iloc[0])
        ax.text(
            0.04,
            0.94,
            f'{method}\nSpearman ρ = {rho:.2f}; n = 12',
            transform=ax.transAxes,
            ha='left',
            va='top',
            fontsize=5.2,
            color=base.BLACK,
        )
    handles = [
        Line2D(
            [0],
            [0],
            marker=VALIDATION_PERIOD_MARKERS[period],
            linestyle='none',
            markersize=4.0,
            markerfacecolor=VALIDATION_PERIOD_COLORS[period],
            markeredgecolor='white',
            label=VALIDATION_PERIOD_LABELS[period],
        )
        for period in VALIDATION_PERIOD_ORDER
    ]
    container.legend(
        handles=handles,
        ncol=4,
        loc='upper center',
        bbox_to_anchor=(0.50, 0.92),
        frameon=False,
        handletextpad=0.35,
        columnspacing=0.75,
        borderaxespad=0,
    )


def _draw_fixed_sensitivity(ax: plt.Axes, source: pd.DataFrame) -> None:
    panel_title(ax, 'c', 'Sign and uncertainty across fixed SAR sensitivity analyses')
    subset = source.loc[source['record_type'].eq('within_year_direction_sensitivity')].copy()
    windows = ['early', 'F1', 'May', 'June']
    window_labels = ['1–14 Mar', '15–28 Mar', 'May', 'June']
    settings = (
        subset[['setting_order', 'setting_label', 'sensitivity_dimension']]
        .drop_duplicates()
        .sort_values('setting_order')
    )
    if len(settings) != 10 or len(subset) != 40:
        raise ValueError('Expected 10 settings by four windows in SAR sensitivity panel')

    group_spans = [
        (-0.48, 3.48, 'Model fold'),
        (3.52, 6.48, 'Objectness threshold'),
        (6.52, 9.48, 'Predicted length'),
    ]
    group_fills = ['#F4F8FB', '#FBF7EF', '#F6F5F9']
    for (left, right, _), fill in zip(group_spans, group_fills):
        ax.add_patch(
            Rectangle(
                (left, -0.50),
                right - left,
                4.0,
                facecolor=fill,
                edgecolor='none',
                zorder=0,
            )
        )

    directions = {
        'increase': ('^', base.BLUE, base.BLUE),
        'decrease': ('v', base.ORANGE, base.ORANGE),
        'no_change': ('o', 'white', base.GREY),
    }
    for window_order, window in enumerate(windows):
        for row in subset.loc[subset['window'].eq(window)].itertuples():
            x = int(row.setting_order)
            marker, face, edge = directions[str(row.direction)]
            if str(row.direction) != 'no_change' and not bool(row.bootstrap_ci95_excludes_zero):
                face = 'white'
            ax.add_patch(
                Rectangle(
                    (x - 0.42, window_order - 0.38),
                    0.84,
                    0.76,
                    facecolor='white',
                    edgecolor='#D6DADE',
                    linewidth=0.45,
                    zorder=1,
                )
            )
            ax.scatter(x, window_order, marker=marker, s=31, facecolor=face, edgecolor=edge, linewidth=0.85, zorder=3)

    for boundary in (3.5, 6.5):
        ax.axvline(boundary, ymin=0.18, ymax=0.80, color='#AEB4BB', lw=0.65)
    for left, right, label in group_spans:
        ax.text((left + right) / 2, -0.94, label, ha='center', va='center', fontsize=5.6, fontweight='bold', color=base.BLACK)
    for row in settings.itertuples(index=False):
        ax.text(int(row.setting_order), -0.46, str(row.setting_label), ha='center', va='center', fontsize=5.1, color=base.BLACK)

    ax.set_yticks(range(4), window_labels)
    ax.set_xticks([])
    ax.set_xlim(-0.55, 9.55)
    ax.set_ylim(3.55, -1.20)
    ax.tick_params(axis='y', length=0, pad=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel('Sign of median-density difference relative to 1 Jan–28 Feb 2026', labelpad=5)
    handles = [
        Line2D([], [], marker=marker, linestyle='none', markersize=4.2, markerfacecolor=face, markeredgecolor=edge, label=label)
        for label, (marker, face, edge) in [
            ('Increase', directions['increase']),
            ('Decrease', directions['decrease']),
            ('Zero', directions['no_change']),
        ]
    ]
    ax.legend(handles=handles, ncol=3, frameon=False, loc='lower right', bbox_to_anchor=(1.0, -0.31), handletextpad=0.35, columnspacing=0.9, borderaxespad=0)
    ax.text(0.0, -0.27, 'Filled triangles: 95% bootstrap interval excludes zero', transform=ax.transAxes, ha='left', va='center', fontsize=5.2, color=base.BLACK, clip_on=False)


def figure1(source: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_IN, 111 / 25.4))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[0.44, 0.56],
        height_ratios=[0.56, 0.44],
        left=0.10,
        right=0.986,
        bottom=0.105,
        top=0.94,
        wspace=0.27,
        hspace=0.48,
    )
    _draw_detector_overlap(fig.add_subplot(grid[0, 0]), source)
    _draw_scene_counts(fig.add_subplot(grid[0, 1]), source)
    _draw_fixed_sensitivity(fig.add_subplot(grid[1, :]), source)
    return fig

def figure5(source: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_IN, 151 / 25.4))
    gs = fig.add_gridspec(2, 2, left=0.12, right=0.975, bottom=0.105, top=0.94, wspace=0.3, hspace=0.32, height_ratios=[0.72, 1])
    heat = source[source.record_type.eq('focal_multipollutant_window')].copy()
    ax = fig.add_subplot(gs[0, :])
    panel_title(ax, 'a', 'Multipollutant anomalies across fixed phases', title_x=0.065)
    indicators = ['no2', 'so2', 'hcho', 'aai']
    window_order = ['early', 'F1', 'F2', 'F3', 'F4_tail', 'May', 'June', 'full_event']
    windows = [heat.loc[heat.window_id.eq(w), 'window_label'].iloc[0] for w in window_order]
    matrix = np.full((4, len(windows)), np.nan)
    for i, indicator in enumerate(indicators):
        for j, window in enumerate(windows):
            q = heat[(heat.indicator_id.str.lower() == indicator) & (heat.window_label == window)]
            if not q.empty:
                matrix[i, j] = q.z_anomaly.iloc[0]
    image = ax.imshow(np.clip(matrix, -3, 3), cmap='RdBu_r', vmin=-3, vmax=3, aspect='auto')
    for i in range(4):
        for j in range(len(windows)):
            value = matrix[i, j]
            if np.isfinite(value):
                label = f'{value:.2f}{('*' if abs(value) > 3 else '')}'
                text_colour = base.WHITE if abs(np.clip(value, -3, 3)) >= 1.8 else base.BLACK
                ax.text(j, i, label, ha='center', va='center', fontsize=5.1, color=text_colour, fontweight='bold' if abs(value) > 3 else 'normal')
    ax.set_yticks(range(4), ['NO$_2$', 'SO$_2$', 'HCHO', 'AAI'])
    ax.set_xticks(range(len(windows)), windows, rotation=25, ha='right')
    ax.tick_params(length=0)
    colourbar = fig.colorbar(image, ax=ax, fraction=0.018, pad=0.012)
    colourbar.ax.set_title('z', fontsize=5.2, pad=2.0)
    colourbar.ax.tick_params(labelsize=5)
    ax.text(1.0, 1.02, '* |z| > 3; colours clipped at ±3', transform=ax.transAxes, ha='right', va='bottom', fontsize=5.0)
    checklist = source[source.record_type.eq('source_compatibility_checklist')].copy()
    ax = fig.add_subplot(gs[1, 0])
    panel_title(ax, 'b', 'Source-compatibility checklist', title_x=0.085)
    checklist['source_group'] = checklist.criterion.astype(str).str.extract('^([A-D])', expand=False)
    criteria = ['A', 'B', 'C', 'D']
    criterion_labels = ['Direct\nshipping', 'Port /\nindustrial', 'Fire /\nburning', 'Dust\ntransport']
    regions = checklist.region_label.dropna().drop_duplicates().tolist()
    for i, region in enumerate(regions):
        for j, criterion in enumerate(criteria):
            q = checklist[(checklist.region_label == region) & (checklist.source_group == criterion)]
            status = q.status.astype(str).str.lower()
            met = int((status == 'true').sum())
            unmet = int((status == 'false').sum())
            not_assessable = int((status == 'not_assessable').sum())
            fills = {0: '#F1F3F4', 1: '#F5E7CF', 2: '#EBCB98'}
            ax.add_patch(Rectangle((j - 0.46, i - 0.42), 0.92, 0.84, facecolor=fills.get(met, '#E1B86F'), edgecolor=base.WHITE, lw=0.7))
            ax.text(j, i, f'{met} met\n{unmet} unmet\n{not_assessable} NA', ha='center', va='center', fontsize=5.0)
    ax.set_xticks(range(len(criteria)), criterion_labels)
    ax.set_yticks(range(len(regions)), regions)
    ax.set_xlim(-0.5, len(criteria) - 0.5)
    ax.set_ylim(len(regions) - 0.5, -0.5)
    ax.tick_params(length=0)
    ax.text(0.99, 1.01, 'NA = not assessable', transform=ax.transAxes, ha='right', va='bottom', fontsize=5.0)
    sensitivity = source[source.record_type.eq('march17_leave_one_day')].copy()
    sensitivity = sensitivity.dropna(subset=['z_anomaly_including', 'z_anomaly_excluding'])
    holder = fig.add_subplot(gs[1, 1])
    holder.set_axis_off()
    panel_title(holder, 'c', 'Sensitivity to 17 March', title_x=0.085)
    split = gs[1, 1].subgridspec(1, 2, width_ratios=[0.24, 0.76], wspace=0.07)
    left = fig.add_subplot(split[0, 0])
    right = fig.add_subplot(split[0, 1], sharey=left)
    y = np.arange(len(sensitivity))[::-1]
    for yy, (_, row) in zip(y, sensitivity.iterrows()):
        for axis in (left, right):
            axis.plot([row.z_anomaly_including, row.z_anomaly_excluding], [yy, yy], color=base.MID_GREY, lw=1.0)
            axis.scatter(row.z_anomaly_including, yy, c=base.BLUE, s=19, zorder=2)
            axis.scatter(row.z_anomaly_excluding, yy, facecolor=base.WHITE, edgecolor=base.ORANGE, s=22, lw=1.0, zorder=2)
    labels = [f'{str(row.indicator_id).upper()} — {('15–28 Mar' if row.window_id == 'F1' else '1 Mar–30 Jun')}' for row in sensitivity.itertuples(index=False)]
    left.set_xlim(-40, -35)
    left.set_xticks([-40, -38, -36])
    left.set_yticks(y, labels)
    right.set_xlim(-3, 3)
    right.set_xticks([-2, 0, 2])
    right.tick_params(axis='y', left=False, labelleft=False)
    right.axvline(0, color=base.BLACK, lw=0.65)
    for axis in (left, right):
        base.clean_axes(axis)
    left.spines['right'].set_visible(False)
    right.spines['left'].set_visible(False)
    mark = 0.014
    left.plot((1 - mark, 1 + mark), (-mark, mark), transform=left.transAxes, color=base.BLACK, lw=0.7, clip_on=False)
    right.plot((-mark, mark), (-mark, mark), transform=right.transAxes, color=base.BLACK, lw=0.7, clip_on=False)
    holder.text(0.5, -0.13, 'Historical-SD z anomaly', transform=holder.transAxes, ha='center', va='top', fontsize=6.5)
    right.legend([Line2D([], [], marker='o', ls='none', color=base.BLUE), Line2D([], [], marker='o', ls='none', markerfacecolor=base.WHITE, markeredgecolor=base.ORANGE)], ['including 17 March', 'excluding 17 March'], frameon=False, loc='upper left', bbox_to_anchor=(0.01, 0.99), borderaxespad=0)
    return fig

def figure7(source: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_IN, 100 / 25.4))
    gs = fig.add_gridspec(2, 2, left=0.075, right=0.985, bottom=0.13, top=0.92, wspace=0.28, hspace=0.34, height_ratios=[1, 0.38], width_ratios=[1.55, 0.75])
    scenes = source[source.record_type.eq('scene')].copy()
    scenes['date'] = pd.to_datetime(scenes.acquisition_time_utc)
    ax = fig.add_subplot(gs[0, 0])
    panel_title(ax, 'a', 'All eligible Baltimore SAR dates', title_x=0.07)
    ax.axvspan(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-03-25'), color='#F3F4F5')
    ax.axvspan(pd.Timestamp('2024-03-26'), pd.Timestamp('2024-05-20'), color=base.PALE_ORANGE)
    ax.axvspan(pd.Timestamp('2024-05-21'), pd.Timestamp('2024-06-30'), color=base.PALE_BLUE)
    for phase in base.PHASE_ORDER:
        q = scenes[scenes.phase.eq(phase)]
        ax.scatter(q.date, q.vessel_like_density_per_100_km2, s=22, c=base.PHASE_COLOR[phase], edgecolor=base.WHITE, lw=0.4, zorder=3)
    ax.set_ylabel('Vessel-like labels / 100 km²')
    ax.set_xlim(pd.Timestamp('2024-01-01'), pd.Timestamp('2024-06-30'))
    ax.set_ylim(0, float(scenes.vessel_like_density_per_100_km2.max()) * 1.18)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    base.clean_axes(ax)
    phase_midpoints = {
        'pre_event': pd.Timestamp('2024-02-12'),
        'acute': pd.Timestamp('2024-04-22'),
        'follow_up': pd.Timestamp('2024-06-02'),
    }
    for phase in base.PHASE_ORDER:
        n_phase = int(scenes.phase.eq(phase).sum())
        ax.text(phase_midpoints[phase], 0.985, f'{base.PHASE_LABEL[phase]} (n={n_phase})', transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=5.2, fontweight='bold')
    ax = fig.add_subplot(gs[0, 1])
    panel_title(ax, 'b', 'Coverage and orbit composition', title_x=0.095)
    counts = scenes.groupby(['phase', 'relative_orbit_number']).size().unstack(fill_value=0)
    y = np.arange(3)[::-1]
    left = np.zeros(3)
    for orbit, colour in ((4, base.BLUE), (106, base.ORANGE)):
        values = np.array([counts.loc[phase, orbit] for phase in base.PHASE_ORDER])
        ax.barh(y, values, left=left, color=colour, height=0.48, edgecolor=base.WHITE, lw=0.5, label=f'orbit {orbit}')
        for yy, lft, value in zip(y, left, values):
            if value:
                ax.text(lft + value / 2, yy, str(int(value)), ha='center', va='center', fontsize=5.2, color=base.WHITE, fontweight='bold')
        left += values
    ax.set_yticks(y, [base.PHASE_LABEL[p] for p in base.PHASE_ORDER])
    ax.set_xlim(0, 14.5)
    ax.set_ylim(-0.5, 3.15)
    ax.set_xticks([0, 5, 10, 14])
    ax.set_xlabel('Eligible scenes')
    base.clean_axes(ax)
    ax.legend(frameon=False, ncol=2, loc='lower right')
    ax.text(0.02, 0.97, 'Valid coverage for all 29 scenes; Sentinel-1A', transform=ax.transAxes, ha='left', va='top', fontsize=5.2)
    ax = fig.add_subplot(gs[1, :])
    panel_title(ax, 'c', 'Phase medians across eligible scenes', title_x=0.045)
    summaries = source[source.record_type.eq('phase_summary')]
    x = np.arange(3)
    medians = [summaries[summaries.phase.eq(p)].vessel_like_density_median_per_100_km2.iloc[0] for p in base.PHASE_ORDER]
    ns = [int(summaries[summaries.phase.eq(p)].scene_count.iloc[0]) for p in base.PHASE_ORDER]
    ax.scatter(x, medians, s=34, c=[base.PHASE_COLOR[p] for p in base.PHASE_ORDER], edgecolor=base.WHITE, lw=0.5, zorder=3)
    for xx, value in zip(x, medians):
        ax.text(xx, value + 0.35, f'{value:.2f}', ha='center', va='bottom', fontsize=5.1)
    ax.set_xticks(x, [f'{base.PHASE_LABEL[p]}  n={n}' for p, n in zip(base.PHASE_ORDER, ns)])
    ax.set_ylabel('Median labels / 100 km²')
    ax.set_xlim(-0.45, 2.45)
    base.clean_axes(ax)
    return fig
