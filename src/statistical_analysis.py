from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.common import write_json


YEARS = (2022, 2023, 2024, 2025, 2026)
HISTORICAL_YEARS = YEARS[:-1]
EVENT_YEAR = YEARS[-1]
STAGES = ("baseline", "acute")


def _percent_change(current: float, baseline: float) -> float:
    if not np.isfinite(current) or not np.isfinite(baseline) or baseline == 0:
        return math.nan
    return 100.0 * (current / baseline - 1.0)


def _quantiles(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return {"q025": math.nan, "q500": math.nan, "q975": math.nan}
    values_at_quantiles = np.quantile(finite, [0.025, 0.5, 0.975])
    return {
        "q025": float(values_at_quantiles[0]),
        "q500": float(values_at_quantiles[1]),
        "q975": float(values_at_quantiles[2]),
    }


def _load_inputs(data_root: Path) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    input_root = data_root / "files/statistical_inputs"
    parameters = json.loads(
        (input_root / "analysis_parameters.json").read_text(encoding="utf-8")
    )
    port = pd.read_csv(input_root / "khor_fakkan_port_daily.csv")
    sar = pd.read_csv(input_root / "khor_fakkan_sar_eligible_dates.csv")
    port["date_utc"] = pd.to_datetime(port["date_utc"], utc=True)
    sar["date_utc"] = pd.to_datetime(sar["date_utc"], utc=True)
    return parameters, port, sar


def _validate_inputs(
    parameters: dict[str, Any], port: pd.DataFrame, sar: pd.DataFrame
) -> dict[str, Any]:
    required_port = {
        "date_utc",
        "year",
        "analysis_stage",
        "portwatch_port_id",
        "portwatch_port_name",
        "port_calls_per_day",
    }
    required_sar = {
        "date_utc",
        "year",
        "analysis_stage",
        "fixed_window",
        "orbit_direction",
        "relative_orbit_number",
        "incidence_angle_deg",
        "scene_group_id",
        "sentinel_1_product_id",
        "vessel_like_density_per_100_km2",
        "matched_reference_years",
    }
    missing_port = sorted(required_port.difference(port.columns))
    missing_sar = sorted(required_sar.difference(sar.columns))
    if missing_port or missing_sar:
        raise ValueError(
            f"Statistical input schema mismatch; port={missing_port}, SAR={missing_sar}"
        )

    expected_years = tuple(int(value) for value in parameters["years"])
    if expected_years != YEARS:
        raise ValueError(f"Expected years {YEARS}, found {expected_years}")
    if set(port["year"].astype(int)) != set(YEARS):
        raise ValueError("Port input does not contain the five declared years.")
    if set(sar["year"].astype(int)) != set(YEARS):
        raise ValueError("SAR input does not contain the five declared years.")
    if set(port["analysis_stage"]) != set(STAGES):
        raise ValueError("Port input stage labels changed.")
    if set(sar["analysis_stage"]) != set(STAGES):
        raise ValueError("SAR input stage labels changed.")
    if port.duplicated(["date_utc", "year", "analysis_stage"]).any():
        raise ValueError("Port input contains duplicate daily records.")
    if sar.duplicated(["date_utc", "year", "analysis_stage"]).any():
        raise ValueError("SAR input contains duplicate eligible dates.")
    if (port["date_utc"].dt.year != port["year"].astype(int)).any():
        raise ValueError("Port year and UTC date disagree.")
    if (sar["date_utc"].dt.year != sar["year"].astype(int)).any():
        raise ValueError("SAR year and UTC date disagree.")
    if port["date_utc"].dt.strftime("%m-%d").eq("02-29").any():
        raise ValueError("February 29 is excluded from the fixed calendar windows.")
    if sar["date_utc"].dt.strftime("%m-%d").eq("02-29").any():
        raise ValueError("February 29 is excluded from the SAR matching input.")
    if not np.isfinite(port["port_calls_per_day"].to_numpy(float)).all():
        raise ValueError("Port input contains missing or non-finite values.")
    if not np.isfinite(
        sar["vessel_like_density_per_100_km2"].to_numpy(float)
    ).all():
        raise ValueError("SAR input contains missing or non-finite densities.")
    if (sar["matched_reference_years"].astype(int) < 3).any():
        raise ValueError("SAR input contains dates below the reference-year threshold.")

    expected_days = {"baseline": 59, "acute": 28}
    port_counts = (
        port.groupby(["year", "analysis_stage"], sort=True)
        .size()
        .to_dict()
    )
    for year in YEARS:
        for stage in STAGES:
            if port_counts.get((year, stage)) != expected_days[stage]:
                raise ValueError(
                    f"Unexpected PortWatch day count for {year} {stage}: "
                    f"{port_counts.get((year, stage))}"
                )
    orbit_counts = (
        sar.groupby(["year", "analysis_stage"], sort=True)[
            "relative_orbit_number"
        ]
        .nunique()
        .to_dict()
    )
    if any(orbit_counts.get((year, stage)) != 3 for year in YEARS for stage in STAGES):
        raise ValueError("Every year-stage SAR sample must retain three relative orbits.")

    return {
        "port_rows": int(len(port)),
        "sar_rows": int(len(sar)),
        "port_days_by_year_stage": {
            f"{year}_{stage}": int(port_counts[(year, stage)])
            for year in YEARS
            for stage in STAGES
        },
        "sar_dates_by_year_stage": {
            f"{year}_{stage}": int(
                len(
                    sar.loc[
                        sar["year"].eq(year)
                        & sar["analysis_stage"].eq(stage)
                    ]
                )
            )
            for year in YEARS
            for stage in STAGES
        },
        "sar_relative_orbits_by_year_stage": {
            f"{year}_{stage}": int(orbit_counts[(year, stage)])
            for year in YEARS
            for stage in STAGES
        },
    }


def _values_by_year_stage(
    port: pd.DataFrame, sar: pd.DataFrame
) -> tuple[
    dict[int, dict[str, np.ndarray]],
    dict[int, dict[str, list[np.ndarray]]],
]:
    port_values: dict[int, dict[str, np.ndarray]] = {}
    sar_values: dict[int, dict[str, list[np.ndarray]]] = {}
    for year in YEARS:
        port_values[year] = {}
        sar_values[year] = {}
        for stage in STAGES:
            port_subset = port.loc[
                port["year"].eq(year) & port["analysis_stage"].eq(stage)
            ].sort_values("date_utc", kind="mergesort")
            port_values[year][stage] = port_subset[
                "port_calls_per_day"
            ].to_numpy(float)

            sar_subset = sar.loc[
                sar["year"].eq(year) & sar["analysis_stage"].eq(stage)
            ].sort_values(
                ["relative_orbit_number", "date_utc"], kind="mergesort"
            )
            sar_values[year][stage] = [
                group["vessel_like_density_per_100_km2"].to_numpy(float)
                for _, group in sar_subset.groupby(
                    "relative_orbit_number", sort=True
                )
            ]
    return port_values, sar_values


def _summarize(
    port_values: dict[int, dict[str, np.ndarray]],
    sar_values: dict[int, dict[str, list[np.ndarray]]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in YEARS:
        port_baseline = float(np.mean(port_values[year]["baseline"]))
        port_acute = float(np.mean(port_values[year]["acute"]))
        sar_baseline_values = np.concatenate(sar_values[year]["baseline"])
        sar_acute_values = np.concatenate(sar_values[year]["acute"])
        sar_baseline = float(np.median(sar_baseline_values))
        sar_acute = float(np.median(sar_acute_values))
        rows.append(
            {
                "year": year,
                "year_role": "event_year" if year == EVENT_YEAR else "historical_year",
                "port_baseline_days": len(port_values[year]["baseline"]),
                "port_baseline_mean_calls_per_day": port_baseline,
                "port_acute_days": len(port_values[year]["acute"]),
                "port_acute_mean_calls_per_day": port_acute,
                "port_change_calls_per_day": port_acute - port_baseline,
                "port_percent_change": _percent_change(port_acute, port_baseline),
                "sar_baseline_eligible_dates": len(sar_baseline_values),
                "sar_baseline_median_labels_per_100_km2": sar_baseline,
                "sar_acute_eligible_dates": len(sar_acute_values),
                "sar_acute_median_labels_per_100_km2": sar_acute,
                "sar_change_labels_per_100_km2": sar_acute - sar_baseline,
                "sar_percent_change": _percent_change(sar_acute, sar_baseline),
            }
        )
    return pd.DataFrame(rows)


def _bootstrap(
    port_values: dict[int, dict[str, np.ndarray]],
    sar_values: dict[int, dict[str, list[np.ndarray]]],
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    port_percent = np.full((replicates, len(YEARS)), np.nan, dtype=float)
    sar_percent = np.full_like(port_percent, np.nan)
    for replicate in range(replicates):
        for column, year in enumerate(YEARS):
            sampled_port: dict[str, float] = {}
            for stage in STAGES:
                values = port_values[year][stage]
                indices = rng.integers(0, len(values), size=len(values))
                sampled_port[stage] = float(np.mean(values[indices]))
            port_percent[replicate, column] = _percent_change(
                sampled_port["acute"], sampled_port["baseline"]
            )

            sampled_sar: dict[str, float] = {}
            for stage in STAGES:
                strata = []
                for values in sar_values[year][stage]:
                    indices = rng.integers(0, len(values), size=len(values))
                    strata.append(values[indices])
                sampled_sar[stage] = float(np.median(np.concatenate(strata)))
            sar_percent[replicate, column] = _percent_change(
                sampled_sar["acute"], sampled_sar["baseline"]
            )

    valid = np.isfinite(port_percent).all(axis=1) & np.isfinite(sar_percent).all(axis=1)
    port_percent = port_percent[valid]
    sar_percent = sar_percent[valid]
    event_index = YEARS.index(EVENT_YEAR)
    year_2024_index = YEARS.index(2024)
    port_extreme = port_percent[:, event_index] - np.min(
        port_percent[:, : len(HISTORICAL_YEARS)], axis=1
    )
    sar_extreme = sar_percent[:, event_index] - np.max(
        sar_percent[:, : len(HISTORICAL_YEARS)], axis=1
    )
    joint = (port_extreme < 0) & (sar_extreme > 0)
    return {
        "requested_replicates": int(replicates),
        "effective_replicates": int(valid.sum()),
        "seed": int(seed),
        "resampling_unit_port": "UTC day within year and stage",
        "resampling_unit_sar": "eligible UTC date within year, stage and relative orbit",
        "historical_extrema_reselected_each_replicate": True,
        "joint_dominance_fraction": float(np.mean(joint)),
        "joint_dominance_fraction_is_p_value": False,
        "port_2026_minus_historical_min": _quantiles(port_extreme),
        "sar_2026_minus_historical_max": _quantiles(sar_extreme),
        "port_2026_minus_2024": _quantiles(
            port_percent[:, event_index] - port_percent[:, year_2024_index]
        ),
        "sar_2026_minus_2024": _quantiles(
            sar_percent[:, event_index] - sar_percent[:, year_2024_index]
        ),
        "per_year": {
            str(year): {
                "port_percent_change": _quantiles(port_percent[:, index]),
                "sar_percent_change": _quantiles(sar_percent[:, index]),
            }
            for index, year in enumerate(YEARS)
        },
    }


def _verify_against_shared_results(
    data_root: Path, summary: pd.DataFrame, bootstrap: dict[str, Any]
) -> dict[str, Any]:
    shared = pd.read_csv(
        data_root
        / "files/analysis_ready/Supplementary_Data_5_acute_joint_extremeness.csv"
    )
    expected_points = shared.loc[
        shared["record_type"].eq("year_point")
        & shared["tolerance_days"].eq(8)
    ].copy()
    expected_points["year"] = expected_points["year"].astype(int)
    joined = summary.merge(
        expected_points,
        on="year",
        suffixes=("_recomputed", "_shared"),
        validate="one_to_one",
    )
    point_fields = (
        "port_baseline_mean_calls_per_day",
        "port_acute_mean_calls_per_day",
        "port_percent_change",
        "sar_baseline_median_labels_per_100_km2",
        "sar_acute_median_labels_per_100_km2",
        "sar_percent_change",
    )
    point_checks = {
        field: bool(
            np.allclose(
                joined[f"{field}_recomputed"].to_numpy(float),
                joined[f"{field}_shared"].to_numpy(float),
                rtol=0,
                atol=1e-10,
            )
        )
        for field in point_fields
    }

    expected_contrasts = shared.loc[
        shared["record_type"].eq("bootstrap_contrast")
        & shared["tolerance_days"].eq(8)
    ].set_index("contrast_id")
    contrast_checks: dict[str, bool] = {}
    for contrast in (
        "port_2026_minus_historical_min",
        "sar_2026_minus_historical_max",
        "port_2026_minus_2024",
        "sar_2026_minus_2024",
    ):
        expected = expected_contrasts.loc[contrast, ["q025", "q500", "q975"]].to_numpy(float)
        observed = np.array(
            [bootstrap[contrast][key] for key in ("q025", "q500", "q975")]
        )
        contrast_checks[contrast] = bool(
            np.allclose(observed, expected, rtol=0, atol=1e-10)
        )
    checks = {
        "point_estimates": point_checks,
        "bootstrap_contrasts": contrast_checks,
        "replicates": int(bootstrap["effective_replicates"])
        == int(expected_contrasts["effective_replicates"].iloc[0]),
        "seed": int(bootstrap["seed"])
        == int(expected_contrasts["bootstrap_seed"].iloc[0]),
    }
    if not (
        all(point_checks.values())
        and all(contrast_checks.values())
        and checks["replicates"]
        and checks["seed"]
    ):
        raise ValueError(f"Recomputed statistics disagree with shared results: {checks}")
    return checks


def _load_no2_inputs(
    data_root: Path,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    input_root = data_root / "files/statistical_inputs"
    parameters = json.loads(
        (input_root / "no2_analysis_parameters.json").read_text(encoding="utf-8")
    )
    daily = pd.read_csv(input_root / "no2_daily_aggregates.csv")
    shared_summary = pd.read_csv(input_root / "no2_may_june_summary.csv")
    daily["utc_date"] = pd.to_datetime(daily["utc_date"], utc=True)
    return parameters, daily, shared_summary


def _validate_no2_inputs(
    parameters: dict[str, Any], daily: pd.DataFrame
) -> dict[str, Any]:
    required = {
        "utc_date",
        "analysis_id",
        "buffer_km",
        "year",
        "population_weighted_observed_no2_mol_m2",
        "expected_no2_mol_m2",
        "population_weighted_no2_anomaly_mol_m2",
        "full_valid_coverage_fraction",
        "effective_population_coverage_fraction",
        "no2_area_coverage_eligible",
        "primary_population_coverage_eligible",
        "expected_value_available",
        "meteorological_normalization_reliable",
        "primary_analysis_day_eligible",
        "no2_unit",
    }
    missing = sorted(required.difference(daily.columns))
    if missing:
        raise ValueError(f"NO2 daily aggregate schema mismatch: {missing}")
    if daily.duplicated(["analysis_id", "buffer_km", "utc_date"]).any():
        raise ValueError("NO2 daily aggregates contain duplicate region-date rows.")
    if len(daily) != 3624:
        raise ValueError(f"Expected 3,624 NO2 daily aggregate rows, found {len(daily)}")
    if set(daily["year"].astype(int)) != set(YEARS):
        raise ValueError("NO2 daily aggregates do not contain the five declared years.")
    if (daily["utc_date"].dt.year != daily["year"].astype(int)).any():
        raise ValueError("NO2 year and UTC date disagree.")
    if set(daily["no2_unit"].dropna()) != {"mol m-2"}:
        raise ValueError("NO2 units changed.")

    area_threshold = float(
        parameters["eligibility"]["minimum_area_coverage_fraction"]
    )
    population_threshold = float(
        parameters["eligibility"]["minimum_population_coverage_fraction"]
    )
    formula = (
        daily["full_valid_coverage_fraction"].ge(area_threshold)
        & daily["effective_population_coverage_fraction"].ge(
            population_threshold
        )
        & daily["expected_value_available"].astype(bool)
        & daily["meteorological_normalization_reliable"].astype(bool)
        & daily["population_weighted_no2_anomaly_mol_m2"].notna()
    )
    if not formula.equals(daily["primary_analysis_day_eligible"].astype(bool)):
        raise ValueError("Stored NO2 eligibility flags disagree with the public rule.")
    if not daily["no2_area_coverage_eligible"].astype(bool).equals(
        daily["full_valid_coverage_fraction"].ge(area_threshold)
    ):
        raise ValueError("Stored area-coverage eligibility flags changed.")
    if not daily["primary_population_coverage_eligible"].astype(bool).equals(
        daily["effective_population_coverage_fraction"].ge(population_threshold)
    ):
        raise ValueError("Stored population-coverage eligibility flags changed.")

    declared_regions = {
        (row["analysis_id"], int(row["buffer_km"]))
        for row in parameters["regions"]
    }
    observed_regions = set(
        daily[["analysis_id", "buffer_km"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    if observed_regions != declared_regions:
        raise ValueError(
            f"NO2 analytical domains changed: {sorted(observed_regions)}"
        )
    rows_by_region = (
        daily.groupby(["analysis_id", "buffer_km"], sort=True)
        .size()
        .to_dict()
    )
    if any(value != 906 for value in rows_by_region.values()):
        raise ValueError(f"Unexpected NO2 calendar coverage: {rows_by_region}")
    return {
        "daily_rows": int(len(daily)),
        "unique_region_date_keys": int(
            daily[["analysis_id", "buffer_km", "utc_date"]]
            .drop_duplicates()
            .shape[0]
        ),
        "analytical_domains": int(len(observed_regions)),
        "calendar_rows_per_domain": {
            f"{analysis_id}_{int(buffer_km)}km": int(count)
            for (analysis_id, buffer_km), count in rows_by_region.items()
        },
        "eligibility_rule_recomputed": True,
        "raw_pixel_rows_included": False,
    }


def _fixed_week_start(values: pd.Series) -> pd.Series:
    normalized = values.dt.normalize()
    return normalized - pd.to_timedelta(normalized.dt.dayofweek, unit="D")


def _bootstrap_no2_difference(
    eligible: pd.DataFrame, *, replicates: int, seed: int
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    yearly: dict[int, np.ndarray] = {}
    metric = "population_weighted_no2_anomaly_mol_m2"
    week_counts: dict[str, int] = {}
    for year in YEARS:
        year_frame = eligible.loc[eligible["year"].eq(year)].copy()
        year_frame["week_start_utc"] = _fixed_week_start(year_frame["utc_date"])
        weekly = (
            year_frame.groupby("week_start_utc", observed=True)[metric]
            .agg(["sum", "count"])
            .reset_index(drop=True)
        )
        if weekly.empty:
            raise ValueError(f"NO2 bootstrap has no eligible UTC weeks for {year}.")
        week_counts[str(year)] = int(len(weekly))
        indices = rng.integers(0, len(weekly), size=(replicates, len(weekly)))
        sums = weekly["sum"].to_numpy(float)[indices].sum(axis=1)
        counts = weekly["count"].to_numpy(float)[indices].sum(axis=1)
        yearly[year] = sums / counts
    event = yearly[EVENT_YEAR]
    historical = np.mean(
        np.vstack([yearly[year] for year in HISTORICAL_YEARS]), axis=0
    )
    difference = event - historical
    percent = 100.0 * difference / np.abs(historical)
    return {
        "replicates": int(replicates),
        "seed": int(seed),
        "resampling_unit": "UTC week within year",
        "historical_year_weighting": "equal",
        "eligible_utc_weeks_by_year": week_counts,
        "event_interval": [
            float(np.nanpercentile(event, 2.5)),
            float(np.nanpercentile(event, 97.5)),
        ],
        "historical_interval": [
            float(np.nanpercentile(historical, 2.5)),
            float(np.nanpercentile(historical, 97.5)),
        ],
        "difference_interval": [
            float(np.nanpercentile(difference, 2.5)),
            float(np.nanpercentile(difference, 97.5)),
        ],
        "percent_change_interval": [
            float(np.nanpercentile(percent, 2.5)),
            float(np.nanpercentile(percent, 97.5)),
        ],
    }


def _summarize_no2_may_june(
    parameters: dict[str, Any], daily: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    phase = parameters["phase"]
    month_day = daily["utc_date"].dt.strftime("%m-%d")
    phase_calendar = daily.loc[
        month_day.between(phase["start"], phase["end"])
    ].copy()
    phase_rows = phase_calendar.loc[
        phase_calendar["primary_analysis_day_eligible"].astype(bool)
    ].copy()
    replicates = int(parameters["bootstrap"]["replicates"])
    rows: list[dict[str, Any]] = []
    bootstrap_records: dict[str, Any] = {}
    for region in parameters["regions"]:
        analysis_id = str(region["analysis_id"])
        buffer_km = int(region["buffer_km"])
        calendar_selected = phase_calendar.loc[
            phase_calendar["analysis_id"].eq(analysis_id)
            & phase_calendar["buffer_km"].eq(buffer_km)
        ].copy()
        selected = phase_rows.loc[
            phase_rows["analysis_id"].eq(analysis_id)
            & phase_rows["buffer_km"].eq(buffer_km)
        ].copy()
        event = selected.loc[selected["year"].eq(EVENT_YEAR)].copy()
        history = selected.loc[selected["year"].isin(HISTORICAL_YEARS)].copy()
        historical_anomaly_by_year = (
            history.groupby("year", observed=True)[
                "population_weighted_no2_anomaly_mol_m2"
            ]
            .mean()
            .reindex(HISTORICAL_YEARS)
        )
        historical_observed_by_year = (
            history.groupby("year", observed=True)[
                "population_weighted_observed_no2_mol_m2"
            ]
            .mean()
            .reindex(HISTORICAL_YEARS)
        )
        event_mean = float(
            event["population_weighted_no2_anomaly_mol_m2"].mean()
        )
        historical_mean = float(historical_anomaly_by_year.mean())
        observed_event_mean = float(
            event["population_weighted_observed_no2_mol_m2"].mean()
        )
        observed_historical_mean = float(historical_observed_by_year.mean())
        bootstrap = _bootstrap_no2_difference(
            selected,
            replicates=replicates,
            seed=int(region["bootstrap_seed"]),
        )
        key = f"{analysis_id}_{buffer_km}km"
        bootstrap_records[key] = bootstrap
        difference = event_mean - historical_mean
        rows.append(
            {
                "analysis_id": analysis_id,
                "buffer_km": buffer_km,
                "analysis_type": region["analysis_type"],
                "phase": phase["id"],
                "calendar_days_2026": int(
                    calendar_selected.loc[
                        calendar_selected["year"].eq(EVENT_YEAR), "utc_date"
                    ].nunique()
                ),
                "no2_valid_days_2026": int(event["utc_date"].nunique()),
                "no2_mean_anomaly_mol_m2": event_mean,
                "no2_equal_year_historical_mean_mol_m2": historical_mean,
                "no2_change_vs_historical_mol_m2": difference,
                "no2_change_vs_historical_bootstrap_ci95_lower": bootstrap[
                    "difference_interval"
                ][0],
                "no2_change_vs_historical_bootstrap_ci95_upper": bootstrap[
                    "difference_interval"
                ][1],
                "no2_percent_change_vs_historical": 100.0
                * difference
                / abs(historical_mean),
                "no2_percent_change_vs_historical_bootstrap_ci95_lower": bootstrap[
                    "percent_change_interval"
                ][0],
                "no2_percent_change_vs_historical_bootstrap_ci95_upper": bootstrap[
                    "percent_change_interval"
                ][1],
                "observed_population_weighted_no2_mean_mol_m2": observed_event_mean,
                "observed_population_weighted_no2_equal_year_historical_mean_mol_m2": observed_historical_mean,
                "observed_population_weighted_no2_change_vs_historical_mol_m2": observed_event_mean
                - observed_historical_mean,
                "observed_population_weighted_no2_percent_change_vs_historical": 100.0
                * (observed_event_mean - observed_historical_mean)
                / abs(observed_historical_mean),
                "historical_valid_days_by_year_json": json.dumps(
                    {
                        str(year): int(
                            history.loc[history["year"].eq(year), "utc_date"].nunique()
                        )
                        for year in HISTORICAL_YEARS
                    },
                    sort_keys=True,
                ),
                "mean_population_coverage_fraction": float(
                    event["effective_population_coverage_fraction"].mean()
                ),
                "no2_bootstrap_interval_excludes_zero": bool(
                    bootstrap["difference_interval"][0] > 0
                    or bootstrap["difference_interval"][1] < 0
                ),
            }
        )
    return pd.DataFrame(rows), bootstrap_records


def _verify_no2_summary(
    recomputed: pd.DataFrame, shared: pd.DataFrame
) -> dict[str, Any]:
    joined = recomputed.merge(
        shared,
        on=["analysis_id", "buffer_km"],
        suffixes=("_recomputed", "_shared"),
        validate="one_to_one",
    )
    numeric_fields = (
        "calendar_days_2026",
        "no2_valid_days_2026",
        "no2_mean_anomaly_mol_m2",
        "no2_equal_year_historical_mean_mol_m2",
        "no2_change_vs_historical_mol_m2",
        "no2_change_vs_historical_bootstrap_ci95_lower",
        "no2_change_vs_historical_bootstrap_ci95_upper",
        "no2_percent_change_vs_historical",
        "no2_percent_change_vs_historical_bootstrap_ci95_lower",
        "no2_percent_change_vs_historical_bootstrap_ci95_upper",
        "observed_population_weighted_no2_mean_mol_m2",
        "observed_population_weighted_no2_equal_year_historical_mean_mol_m2",
        "observed_population_weighted_no2_change_vs_historical_mol_m2",
        "observed_population_weighted_no2_percent_change_vs_historical",
        "mean_population_coverage_fraction",
    )
    percent_fields = {
        "no2_percent_change_vs_historical",
        "no2_percent_change_vs_historical_bootstrap_ci95_lower",
        "no2_percent_change_vs_historical_bootstrap_ci95_upper",
        "observed_population_weighted_no2_percent_change_vs_historical",
    }
    count_fields = {"calendar_days_2026", "no2_valid_days_2026"}
    numeric_checks = {
        field: bool(
            np.allclose(
                joined[f"{field}_recomputed"].to_numpy(float),
                joined[f"{field}_shared"].to_numpy(float),
                rtol=0,
                atol=(
                    0
                    if field in count_fields
                    else 1e-8
                    if field in percent_fields
                    else 1e-10
                    if field == "mean_population_coverage_fraction"
                    else 1e-14
                ),
            )
        )
        for field in numeric_fields
    }
    historical_days_match = bool(
        all(
            json.loads(left) == json.loads(right)
            for left, right in zip(
                joined["historical_valid_days_by_year_json_recomputed"],
                joined["historical_valid_days_by_year_json_shared"],
                strict=True,
            )
        )
    )
    interval_flag_match = bool(
        joined["no2_bootstrap_interval_excludes_zero_recomputed"]
        .astype(bool)
        .equals(
            joined["no2_bootstrap_interval_excludes_zero_shared"].astype(bool)
        )
    )
    checks = {
        "numeric_fields": numeric_checks,
        "historical_valid_days": historical_days_match,
        "interval_excludes_zero_flag": interval_flag_match,
    }
    if not (
        all(numeric_checks.values())
        and historical_days_match
        and interval_flag_match
    ):
        raise ValueError(f"Recomputed NO2 statistics disagree with shared summary: {checks}")
    return checks


def _reproduce_no2(data_root: Path, output_root: Path) -> dict[str, Any]:
    parameters, daily, shared = _load_no2_inputs(data_root)
    validation = _validate_no2_inputs(parameters, daily)
    summary, bootstrap = _summarize_no2_may_june(parameters, daily)
    verification = _verify_no2_summary(summary, shared)
    statistics_root = output_root / "statistics"
    statistics_root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(
        statistics_root / "no2_may_june_summary.csv",
        index=False,
        encoding="utf-8",
        float_format="%.12g",
        lineterminator="\n",
    )
    write_json(statistics_root / "no2_may_june_bootstrap.json", bootstrap)
    return {
        "status": "PASS",
        "analysis": parameters["analysis"],
        "validation": validation,
        "verification_against_shared_summary": verification,
        "outputs": {
            "summary": "statistics/no2_may_june_summary.csv",
            "bootstrap": "statistics/no2_may_june_bootstrap.json",
        },
        "interpretation_boundary": parameters["interpretation_boundary"],
    }


def reproduce(data_root: Path, output_root: Path) -> dict[str, Any]:
    parameters, port, sar = _load_inputs(data_root)
    validation = _validate_inputs(parameters, port, sar)
    port_values, sar_values = _values_by_year_stage(port, sar)
    summary = _summarize(port_values, sar_values)
    bootstrap = _bootstrap(
        port_values,
        sar_values,
        replicates=int(parameters["bootstrap"]["replicates"]),
        seed=int(parameters["bootstrap"]["seed"]),
    )
    verification = _verify_against_shared_results(
        data_root, summary, bootstrap
    )
    no2 = _reproduce_no2(data_root, output_root)

    statistics_root = output_root / "statistics"
    statistics_root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(
        statistics_root / "port_sar_year_summary.csv",
        index=False,
        encoding="utf-8",
        float_format="%.12g",
        lineterminator="\n",
    )
    write_json(statistics_root / "port_sar_bootstrap.json", bootstrap)
    result = {
        "status": "PASS",
        "analysis": "five-year Khor Fakkan port-call and adjacent-water SAR comparison",
        "scope": parameters["scope"],
        "windows": parameters["windows"],
        "validation": validation,
        "verification_against_shared_results": verification,
        "outputs": {
            "summary": "statistics/port_sar_year_summary.csv",
            "bootstrap": "statistics/port_sar_bootstrap.json",
        },
        "interpretation_boundary": parameters["interpretation_boundary"],
        "no2": no2,
    }
    write_json(output_root / "qa/STATISTICAL_REPRODUCTION.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recompute the shared port–SAR and May–June NO2 statistics."
    )
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = reproduce(args.data_root.resolve(), args.output_root.resolve())
    print(
        json.dumps(
            {
                "port_sar_status": result["status"],
                "no2_status": result["no2"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
