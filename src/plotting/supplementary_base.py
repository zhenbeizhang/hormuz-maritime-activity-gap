"""Base plotting functions for supplementary figures."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import rasterio
WIDTH_IN = 183 / 25.4
BLUE = '#0072B2'
SKY = '#56B4E9'
ORANGE = '#E69F00'
VERMILLION = '#D55E00'
GREEN = '#009E73'
PURPLE = '#7B61A8'
GREY = '#737B84'
MID_GREY = '#AAB1B8'
LIGHT_GREY = '#E8EBEE'
PALE_BLUE = '#EAF3F8'
PALE_ORANGE = '#FBF3E4'
BLACK = '#171A1D'
WHITE = '#FFFFFF'
PHASE_ORDER = ['pre_event', 'acute', 'follow_up']
PHASE_LABEL = {'pre_event': 'Pre-event', 'acute': 'Acute', 'follow_up': 'Follow-up'}
PHASE_COLOR = {'pre_event': GREY, 'acute': VERMILLION, 'follow_up': GREEN}
DIRECTION_COLUMNS = ['acute_port_below_same_year_baseline', 'acute_sar_above_same_year_baseline', 'late_phase_port_above_same_year_baseline', 'late_phase_sar_above_same_year_baseline', 'late_phase_no2_mean_above_same_year_baseline', 'late_phase_no2_mean_above_excluding_year_historical_reference']
DIRECTION_LABELS = [
    'March port\nbelow baseline',
    'March SAR\nabove baseline',
    'May–June port\nabove baseline',
    'May–June SAR\nabove baseline',
    'May–June NO$_2$\nabove baseline',
    'May–June NO$_2$ above\nleave-year-out history',
]

def configure_style() -> None:
    matplotlib.rcParams.update({'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica'], 'font.size': 6.5, 'axes.titlesize': 7.3, 'axes.labelsize': 6.5, 'xtick.labelsize': 5.5, 'ytick.labelsize': 5.5, 'legend.fontsize': 5.5, 'axes.linewidth': 0.65, 'xtick.major.width': 0.55, 'ytick.major.width': 0.55, 'xtick.major.size': 2.8, 'ytick.major.size': 2.8, 'text.color': BLACK, 'axes.labelcolor': BLACK, 'axes.edgecolor': BLACK, 'xtick.color': BLACK, 'ytick.color': BLACK, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none', 'svg.hashsalt': 'base-supplementary-redesign', 'savefig.facecolor': WHITE, 'figure.facecolor': WHITE})

def panel_title(ax: plt.Axes, letter: str, title: str) -> None:
    ax.text(0.0, 1.035, letter, transform=ax.transAxes, ha='left', va='bottom', fontsize=8.2, fontweight='bold', color=BLACK)
    ax.text(0.065, 1.035, title, transform=ax.transAxes, ha='left', va='bottom', fontsize=7.3, fontweight='bold', color=BLACK)

def clean_axes(ax: plt.Axes, grid: str | None=None) -> None:
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if grid:
        ax.grid(axis=grid, color=LIGHT_GREY, lw=0.55, zorder=0)

def figure3(source: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_IN, 190 / 25.4))
    gs = fig.add_gridspec(10, 2, left=0.075, right=0.985, bottom=0.055, top=0.945, wspace=0.17, hspace=0.16)
    data = source[source.record_type.eq('daily_port_series')].copy()
    data['date'] = pd.to_datetime(data.date)
    groups = ['Gulf and east-coast ports', 'Wider route context']
    for col, group in enumerate(groups):
        names = data[data.display_group.eq(group)].sort_values('display_order_within_group').portname.drop_duplicates().tolist()
        for row, name in enumerate(names):
            ax = fig.add_subplot(gs[row, col])
            q = data[(data.display_group == group) & (data.portname == name)]
            focal = name == 'Khor Fakkan'
            color = ORANGE if focal else BLUE
            ax.axvspan(pd.Timestamp('2026-03-01'), pd.Timestamp('2026-03-28'), color=PALE_ORANGE, zorder=0)
            ax.axvspan(pd.Timestamp('2026-05-01'), pd.Timestamp('2026-06-30'), color=PALE_BLUE, zorder=0)
            ax.scatter(q.date, q.portcalls, s=3.5, c=MID_GREY, alpha=0.32, lw=0, zorder=1)
            ax.plot(q.date, q.portcalls_2026_7d_mean, color=color, lw=1.0, zorder=3)
            ax.plot(q.date, q.historical_equal_year_7d_mean, color=GREY, lw=0.8, ls=(0, (3, 2)), zorder=2)
            ax.text(0.01, 0.83, name, transform=ax.transAxes, fontsize=5.2, fontweight='bold' if focal else 'normal', color=ORANGE if focal else BLACK)
            ax.set_xlim(pd.Timestamp('2026-01-01'), pd.Timestamp('2026-06-30'))
            ax.set_ylim(bottom=-0.05)
            ax.set_yticks([0, math.ceil(max(q.portcalls.max(), q.portcalls_2026_7d_mean.max()))])
            if row == len(names) - 1:
                ax.xaxis.set_major_locator(mdates.MonthLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            else:
                ax.set_xticklabels([])
            clean_axes(ax)
            if row == 0:
                panel_title(ax, 'a' if col == 0 else 'b', group)
    fig.text(0.018, 0.51, 'Provider-defined port calls per UTC day (row-specific scales)', rotation=90, va='center', fontsize=6.2)
    handles = [Line2D([], [], marker='o', ls='none', color=MID_GREY, alpha=0.5, label='daily observations'), Line2D([], [], color=BLUE, lw=1.2, label='2026 7-day mean'), Line2D([], [], color=ORANGE, lw=1.2, label='Khor Fakkan (post-result focal)'), Line2D([], [], color=GREY, lw=0.9, ls=(0, (3, 2)), label='2022–2025 equal-year 7-day mean')]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, 0.985), ncol=4, frameon=False, handlelength=2, columnspacing=1)
    fig.text(0.075, 0.018, 'Shading: 1–28 Mar (cream); 1 May–30 Jun (blue).', ha='left', fontsize=5.1)
    fig.text(0.985, 0.018, 'Rows ordered by geography/operations, not outcome; compare timing within rows.', ha='right', fontsize=5.1)
    return fig

def figure4(source: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_IN, 174 / 25.4))
    gs = fig.add_gridspec(3, 2, left=0.075, right=0.985, bottom=0.075, top=0.95, wspace=0.27, hspace=0.48, height_ratios=[1, 1, 1.08])
    sar = source[source.source_component.eq('SAR/PortWatch sensitivity') if 'source_component' in source else False].copy()
    loo = sar[sar.analysis_record_type.eq('leave_one_date')].copy()
    loo['omitted_date'] = pd.to_datetime(loo.omitted_value)
    ax = fig.add_subplot(gs[0, 0])
    panel_title(ax, 'a', 'Leave-one-date diagnostics')
    ax.scatter(loo.omitted_date, loo.sar_change, s=17, c=ORANGE, edgecolor=BLACK, lw=0.3, label='SAR density change')
    ax.set_ylabel('SAR density change\n(labels / 100 km²)')
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    span = max(float(loo.sar_change.max() - loo.sar_change.min()), 0.2)
    ax.set_ylim(float(loo.sar_change.min()) - 0.22 * span, float(loo.sar_change.max()) + 0.22 * span)
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4))
    clean_axes(ax)
    ax.text(0.99, 0.04, f'n={len(loo)} omitted dates', transform=ax.transAxes, ha='right', fontsize=5.1)
    holder = fig.add_subplot(gs[0, 1])
    holder.set_axis_off()
    panel_title(holder, 'b', 'Leave-one-orbit diagnostics')
    orb = sar[sar.analysis_record_type.eq('leave_one_relative_orbit')].copy()
    x = np.arange(len(orb))
    sub = gs[0, 1].subgridspec(2, 1, hspace=0.1)
    top = fig.add_subplot(sub[0, 0])
    bot = fig.add_subplot(sub[1, 0], sharex=top)
    top.scatter(x, orb.sar_change, s=24, facecolor=WHITE, edgecolor=ORANGE, lw=1.1)
    top.axhline(0, color=BLACK, lw=0.65)
    top.set_ylabel('SAR change\n(labels / 100 km²)')
    top.tick_params(labelbottom=False)
    clean_axes(top)
    top.spines['bottom'].set_visible(False)
    bot.scatter(x, orb.port_change, s=22, facecolor=WHITE, edgecolor=BLUE, lw=1.1)
    bot.axhline(0, color=BLACK, lw=0.65)
    bot.set_xticks(x, orb.omitted_value.astype(str))
    bot.set_xlabel('Omitted relative orbit')
    bot.set_ylabel('PortWatch change\n(calls/day)')
    clean_axes(bot)
    ax = fig.add_subplot(gs[1, 0])
    panel_title(ax, 'c', 'Historical matching tolerance')
    tol = sar[sar.analysis_record_type.eq('tolerance_summary')].sort_values('matching_tolerance_days')
    ax.plot(tol.matching_tolerance_days, tol.acute_sar_percent_change_vs_matched_historical, color=ORANGE, marker='o', lw=1.0, label='SAR')
    ax.plot(tol.matching_tolerance_days, tol.acute_portwatch_all_days_percent_change_vs_historical, color=BLUE, marker='o', lw=1.0, label='PortWatch')
    ax.axhline(0, color=BLACK, lw=0.65)
    ax.set_xticks(tol.matching_tolerance_days, [f'±{int(v)} d' for v in tol.matching_tolerance_days])
    ax.set_ylabel('Change vs metric-specific history (%)')
    ax.set_xlim(float(tol.matching_tolerance_days.min()) - 0.3, float(tol.matching_tolerance_days.max()) + 1.0)
    clean_axes(ax)
    last = tol.iloc[-1]
    ax.text(float(last.matching_tolerance_days) + 0.24, float(last.acute_sar_percent_change_vs_matched_historical), 'SAR', color=BLACK, va='center', fontsize=5.3)
    ax.text(float(last.matching_tolerance_days) + 0.24, float(last.acute_portwatch_all_days_percent_change_vs_historical), 'PortWatch', color=BLACK, va='center', fontsize=5.3)
    ax = fig.add_subplot(gs[1, 1])
    panel_title(ax, 'd', 'NO$_2$ sensitivity across fixed domains')
    n = source[source.analysis_record_type.eq('no2_spatial_domain') if 'analysis_record_type' in source else False].copy()
    n = n[n.phase.eq('late_phase')].dropna(subset=['no2_change_vs_historical_mol_m2'])
    order = [10, 20, 30]
    labels = []
    vals = []
    lo = []
    hi = []
    for km in order:
        q = n[n.buffer_km.eq(km) & n.analysis_id.eq('khor_fakkan_subregion_sensitivity')].iloc[0]
        labels.append(f'{km} km' + (' (primary)' if km == 20 else ''))
        vals.append(q.no2_change_vs_historical_mol_m2 * 1e5)
        lo.append(q.no2_change_vs_historical_bootstrap_ci95_lower * 1e5)
        hi.append(q.no2_change_vs_historical_bootstrap_ci95_upper * 1e5)
    combined = n[n.analysis_id.astype(str).str.contains('combined|cluster', case=False, regex=True)]
    if not combined.empty:
        q = combined.iloc[0]
        labels.append('East-coast cluster')
        vals.append(q.no2_change_vs_historical_mol_m2 * 1e5)
        lo.append(q.no2_change_vs_historical_bootstrap_ci95_lower * 1e5)
        hi.append(q.no2_change_vs_historical_bootstrap_ci95_upper * 1e5)
    yy = np.arange(len(vals))[::-1]
    ax.errorbar(vals, yy, xerr=[np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)], fmt='o', color=PURPLE, ecolor=PURPLE, capsize=2, lw=0.8)
    ax.axvline(0, color=BLACK, lw=0.65)
    ax.set_yticks(yy, labels)
    ax.set_xlabel('May–June anomaly difference from 2022–2025 history\n(10$^{-5}$ mol m$^{-2}$)')
    ax.set_xlim(min(0, min(lo) - 0.15), max(hi) + 1.75)
    for y_pos, value, lower, upper in zip(yy, vals, lo, hi):
        ax.text(upper + 0.08, y_pos, f'{value:+.2f} [{lower:+.2f}, {upper:+.2f}]', va='center', fontsize=5.0)
    clean_axes(ax)
    holder = fig.add_subplot(gs[2, :])
    holder.set_axis_off()
    panel_title(holder, 'e', 'Complete six-item recurrence matrix')
    lower = gs[2, :].subgridspec(1, 2, width_ratios=[4.7, 1.35], wspace=0.10)
    ax = fig.add_subplot(lower[0, 0])
    rec = source[source.record_type.eq('six_item_recurrence')].sort_values('year')
    cols = DIRECTION_COLUMNS
    arr = np.array([[1 if str(row[c]).lower() == 'true' or row[c] is True else 0 for c in cols] for _, row in rec.iterrows()])
    cmap = matplotlib.colors.ListedColormap(['#F1F3F4', BLUE])
    ax.imshow(arr, aspect='auto', cmap=cmap, vmin=0, vmax=1)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, 'present' if arr[i, j] else 'absent', ha='center', va='center', fontsize=5.0, color=WHITE if arr[i, j] else BLACK)
    direction_labels = [x.replace('\n', ' ') for x in DIRECTION_LABELS]
    ax.set_xticks(range(6), direction_labels, rotation=22, ha='right')
    ax.set_yticks(range(len(rec)), rec.year.astype(int))
    ax.tick_params(length=0)
    ax.add_patch(Rectangle((1.5, 1.5), 3.0, 1.0, facecolor='none', edgecolor=ORANGE, lw=1.05))
    ax.set_xticks(np.arange(-0.5, 6, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(rec), 1), minor=True)
    ax.grid(which='minor', color=WHITE, linewidth=0.8)
    ax.tick_params(which='minor', bottom=False, left=False)
    score = fig.add_subplot(lower[0, 1])
    scores = arr.sum(axis=1)
    years = rec.year.astype(int).to_numpy()
    score_colours = [ORANGE if year == 2024 else BLUE if year == 2026 else MID_GREY for year in years]
    score.barh(np.arange(len(rec)), scores, height=0.56, color=score_colours, edgecolor=WHITE, lw=0.5)
    for i, value in enumerate(scores):
        score.text(value + 0.14, i, f'{int(value)}/6', va='center', fontsize=5.4, fontweight='bold')
    score.set_xlim(0, 6.7)
    score.set_ylim(len(rec) - 0.5, -0.5)
    score.set_yticks([])
    score.set_xticks([0, 3, 6])
    score.set_xlabel('Items present')
    score.text(0.98, 1.03, 'Historical complete matches: 0/4', transform=score.transAxes, ha='right', va='bottom', fontsize=5.0)
    clean_axes(score)
    return fig

def _jitter(n: int, phase_index: int) -> np.ndarray:
    rng = np.random.default_rng(20260815 + phase_index + n)
    return phase_index + rng.uniform(-0.13, 0.13, n)

def figure6(source: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(WIDTH_IN, 105 / 25.4))
    gs = fig.add_gridspec(1, 3, left=0.07, right=0.985, bottom=0.17, top=0.9, wspace=0.34, width_ratios=[1, 1, 0.9])
    raw = source[source.record_type.eq('raw_observation')]
    for k, (domain, unit, title) in enumerate([('PortWatch', 'calls/day', 'PortWatch daily observations'), ('SAR', 'labels/100 km²', 'SAR scene observations')]):
        ax = fig.add_subplot(gs[0, k])
        panel_title(ax, 'a' if k == 0 else 'b', title)
        arrays = []
        for i, p in enumerate(PHASE_ORDER):
            vals = raw[(raw.domain == domain) & (raw.phase == p)].value.to_numpy(float)
            arrays.append(vals)
            ax.scatter(_jitter(len(vals), i), vals, s=10, c=PHASE_COLOR[p], alpha=0.58, edgecolor='white', lw=0.25, zorder=2)
        bp = ax.boxplot(arrays, positions=range(3), widths=0.34, patch_artist=True, showfliers=False, medianprops={'color': BLACK, 'lw': 1}, boxprops={'facecolor': WHITE, 'edgecolor': BLACK, 'lw': 0.7}, whiskerprops={'color': BLACK, 'lw': 0.6}, capprops={'color': BLACK, 'lw': 0.6})
        ax.set_xticks(range(3), [f'{PHASE_LABEL[p]}\nn={len(arrays[i])}' for i, p in enumerate(PHASE_ORDER)])
        ax.set_ylabel(unit)
        clean_axes(ax)
    holder = fig.add_subplot(gs[0, 2])
    holder.set_axis_off()
    panel_title(holder, 'c', 'Acute minus pre-event differences')
    eff = source[source.record_type.eq('primary_effect')]
    sub = gs[0, 2].subgridspec(2, 1, hspace=0.42)
    for j, (dom, col, unit) in enumerate([('PortWatch', BLUE, 'calls/day'), ('SAR', ORANGE, 'labels / 100 km²')]):
        ax = fig.add_subplot(sub[j, 0])
        r = eff[eff.domain == dom].iloc[0]
        ax.errorbar(r.difference, 0, xerr=[[r.difference - r.ci95_low], [r.ci95_high - r.difference]], fmt='o', ms=7, color=col, ecolor=col, capsize=2, lw=1.1)
        ax.axvline(0, color=BLACK, lw=0.7)
        ax.set_yticks([])
        ax.set_xlabel(f'{dom}: acute − pre-event ({unit})')
        ax.text(0.98, 0.9, f'Difference (95% CI)\n{r.difference:.2f} [{r.ci95_low:.2f}, {r.ci95_high:.2f}]', transform=ax.transAxes, ha='right', va='top', fontsize=5.0)
        clean_axes(ax)
    return fig
