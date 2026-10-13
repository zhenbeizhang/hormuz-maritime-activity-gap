"""Public full-refit block bootstrap for population-weighted NO2 context.

The input is a daily, analysis-ready design table.  Each bootstrap replicate
refits the same fixed OLS model, repeats leave-one-year-out prediction for the
historical comparison, and preserves daily missingness and eligibility.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

ANALYSIS_ID = "khor_fakkan_subregion_sensitivity"
DOMAINS_KM = (10, 20, 30)
HISTORICAL_YEARS = (2022, 2023, 2024, 2025)
ALL_YEARS = (*HISTORICAL_YEARS, 2026)
FIXED_PREDICTORS = (
    "season_sin_1",
    "season_cos_1",
    "season_sin_2",
    "season_cos_2",
    "wind_speed_m_s",
    "wind_dir_sin",
    "wind_dir_cos",
    "boundary_layer_height_m",
    "temperature_2m_k",
    "total_precipitation_m",
    "valid_coverage_fraction",
    "mean_cloud_fraction",
    "days_since_2022_start",
)
PRIMARY_BLOCK_DAYS = 7
SENSITIVITY_BLOCK_DAYS = (5, 14)
BOOTSTRAP_REPLICATES = 5000
GLOBAL_SEED = 20261013
PARAMETER_COUNT = 1 + len(FIXED_PREDICTORS)
MIN_EVALUATION_DAYS = 7
SUCCESS_THRESHOLD = 0.95
NO2_UNIT = "mol m-2"
INTERPRETATION = (
    "population-weighted tropospheric NO2 column-anomaly context; "
    "not source attribution, surface concentration, personal exposure, "
    "health effect or a causal estimate"
)


class ReproductionError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedDomain:
    buffer_km: int
    frame: pd.DataFrame
    frozen_point_estimate: float
    frozen_2026_mean: float
    frozen_historical_mean: float
    frozen_unadjusted_difference: float


def _design_matrix(frame: pd.DataFrame) -> np.ndarray:
    values = frame.loc[:, FIXED_PREDICTORS].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    return np.column_stack([np.ones(len(frame), dtype=float), values])


def _fit_coefficients(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, int, int]:
    complete = np.isfinite(y) & np.isfinite(x).all(axis=1)
    x_use = x[complete]
    y_use = y[complete]
    n = int(len(y_use))
    if n <= x.shape[1] + 2:
        raise ReproductionError("insufficient complete training rows")
    coefficients, _, rank, _ = np.linalg.lstsq(x_use, y_use, rcond=None)
    if int(rank) < x.shape[1]:
        raise ReproductionError("rank-deficient training design")
    return coefficients, int(rank), n


def circular_moving_block_indices(
    n: int, block_length: int, rng: np.random.Generator
) -> np.ndarray:
    if n <= 0 or block_length <= 0:
        raise ValueError("n and block_length must be positive")
    block_count = int(math.ceil(n / block_length))
    starts = rng.integers(0, n, size=block_count)
    offsets = np.arange(block_length, dtype=np.int64)
    indices = (starts[:, None] + offsets[None, :]) % n
    return indices.reshape(-1)[:n]


def _seed_for(buffer_km: int, block_length: int) -> int:
    sequence = np.random.SeedSequence([GLOBAL_SEED, int(buffer_km), int(block_length)])
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


def load_domains(path: Path) -> tuple[list[PreparedDomain], dict[str, Any]]:
    frame = pd.read_csv(path)
    required = {
        "utc_date",
        "analysis_id",
        "buffer_km",
        "year",
        "observed_no2_mol_m2",
        "training_eligible",
        "population_weighted_observed_no2_mol_m2",
        "population_weighted_no2_anomaly_mol_m2",
        "effective_population_coverage_fraction",
        "evaluation_eligible",
        "recovery_period",
        *FIXED_PREDICTORS,
    }
    missing = required - set(frame)
    if missing:
        raise ReproductionError(f"Daily design is missing columns: {sorted(missing)}")
    frame = frame[
        frame["analysis_id"].eq(ANALYSIS_ID) & frame["buffer_km"].isin(DOMAINS_KM)
    ].copy()
    frame["utc_date"] = pd.to_datetime(frame["utc_date"], utc=True, errors="raise")
    for column in ("training_eligible", "evaluation_eligible", "recovery_period"):
        frame[column] = frame[column].astype(str).str.lower().map({"true": True, "false": False})
        if frame[column].isna().any():
            raise ReproductionError(f"Invalid boolean value in {column}")
    expected_calendar_counts = {2022: 181, 2023: 181, 2024: 182, 2025: 181, 2026: 181}
    prepared: list[PreparedDomain] = []
    audit_rows: list[dict[str, Any]] = []
    for buffer_km in DOMAINS_KM:
        local = frame[frame["buffer_km"].eq(buffer_km)].sort_values("utc_date").copy()
        if local.duplicated("utc_date").any():
            raise ReproductionError(f"Duplicate UTC date in {buffer_km}-km domain")
        counts = local.groupby(local["utc_date"].dt.year).size().to_dict()
        if counts != expected_calendar_counts:
            raise ReproductionError(f"Unexpected calendar counts in {buffer_km}-km domain: {counts}")
        recovery = local[local["recovery_period"] & local["evaluation_eligible"]].copy()
        anomaly_means = recovery.groupby(recovery["utc_date"].dt.year)[
            "population_weighted_no2_anomaly_mol_m2"
        ].mean()
        observed_means = recovery.groupby(recovery["utc_date"].dt.year)[
            "population_weighted_observed_no2_mol_m2"
        ].mean()
        if set(anomaly_means.index) != set(ALL_YEARS):
            raise ReproductionError(f"Missing recovery year in {buffer_km}-km domain")
        point = float(anomaly_means.loc[2026] - anomaly_means.loc[list(HISTORICAL_YEARS)].mean())
        unadjusted = float(observed_means.loc[2026] - observed_means.loc[list(HISTORICAL_YEARS)].mean())
        prepared.append(
            PreparedDomain(
                buffer_km=buffer_km,
                frame=local,
                frozen_point_estimate=point,
                frozen_2026_mean=float(anomaly_means.loc[2026]),
                frozen_historical_mean=float(anomaly_means.loc[list(HISTORICAL_YEARS)].mean()),
                frozen_unadjusted_difference=unadjusted,
            )
        )
        audit_rows.append(
            {
                "buffer_km": buffer_km,
                "rows": int(len(local)),
                "duplicate_dates": int(local.duplicated("utc_date").sum()),
                "recovery_eligible_days": {
                    str(int(year)): int(value)
                    for year, value in recovery.groupby(recovery["utc_date"].dt.year).size().items()
                },
            }
        )
    return prepared, {
        "join_cardinality": "one_to_one_complete_by_utc_date_and_buffer_km",
        "units": NO2_UNIT,
        "domains": audit_rows,
    }


def _metrics(observed: np.ndarray, predicted: np.ndarray) -> tuple[float, float, int]:
    valid = np.isfinite(observed) & np.isfinite(predicted)
    if not valid.any():
        return math.nan, math.nan, 0
    residual = observed[valid] - predicted[valid]
    return float(np.mean(np.abs(residual))), float(np.sqrt(np.mean(residual**2))), int(valid.sum())


def _autocorrelation(values: pd.Series, dates: pd.Series, lag: int) -> float:
    frame = pd.DataFrame({"value": values, "date": pd.to_datetime(dates, utc=True)})
    frame = frame.dropna().sort_values("date")
    if len(frame) <= lag:
        return math.nan
    current = frame.set_index("date")["value"]
    shifted = current.copy()
    shifted.index = shifted.index + pd.Timedelta(days=lag)
    paired = pd.concat([current.rename("current"), shifted.rename("lagged")], axis=1).dropna()
    if len(paired) < 3 or paired["current"].std(ddof=0) == 0 or paired["lagged"].std(ddof=0) == 0:
        return math.nan
    return float(paired["current"].corr(paired["lagged"]))


def model_diagnostics(prepared: Iterable[PreparedDomain]) -> tuple[pd.DataFrame, pd.DataFrame]:
    diagnostic_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    for domain in prepared:
        frame = domain.frame.copy()
        training = frame[frame["training_eligible"]].copy()
        historical = training[training["year"].isin(HISTORICAL_YEARS)].copy()
        _, final_rank, final_n = _fit_coefficients(
            _design_matrix(historical),
            pd.to_numeric(historical["observed_no2_mol_m2"], errors="coerce").to_numpy(float),
        )
        residual_parts = []
        for held_year in HISTORICAL_YEARS:
            train = historical[historical["year"].ne(held_year)].copy()
            test = historical[historical["year"].eq(held_year)].copy()
            coefficients, rank, n_train = _fit_coefficients(
                _design_matrix(train),
                pd.to_numeric(train["observed_no2_mol_m2"], errors="coerce").to_numpy(float),
            )
            predicted = _design_matrix(test) @ coefficients
            climatology = train.groupby("month_day", observed=True)["observed_no2_mol_m2"].mean()
            climatology_prediction = test["month_day"].map(climatology).to_numpy(float)
            observed = pd.to_numeric(test["observed_no2_mol_m2"], errors="coerce").to_numpy(float)
            model_mae, model_rmse, model_n = _metrics(observed, predicted)
            clim_mae, clim_rmse, clim_n = _metrics(observed, climatology_prediction)
            residual = observed - predicted
            diagnostic_rows.append(
                {
                    "buffer_km": domain.buffer_km,
                    "record_type": "loyo_year",
                    "held_out_year": held_year,
                    "n_train": n_train,
                    "n_test_model": model_n,
                    "n_test_climatology": clim_n,
                    "parameter_count": PARAMETER_COUNT,
                    "design_matrix_rank": rank,
                    "model_mae_mol_m2": model_mae,
                    "model_rmse_mol_m2": model_rmse,
                    "climatology_mae_mol_m2": clim_mae,
                    "climatology_rmse_mol_m2": clim_rmse,
                    "mae_improvement_fraction": (clim_mae - model_mae) / clim_mae,
                    "rmse_improvement_fraction": (clim_rmse - model_rmse) / clim_rmse,
                    "residual_lag1_autocorrelation": _autocorrelation(
                        pd.Series(residual), test["utc_date"].reset_index(drop=True), 1
                    ),
                    "residual_lag7_autocorrelation": _autocorrelation(
                        pd.Series(residual), test["utc_date"].reset_index(drop=True), 7
                    ),
                }
            )
            residual_parts.append(
                pd.DataFrame(
                    {
                        "year": held_year,
                        "utc_date": test["utc_date"].to_numpy(),
                        "observed": observed,
                        "predicted": predicted,
                        "climatology": climatology_prediction,
                        "residual": residual,
                    }
                )
            )
        residuals = pd.concat(residual_parts, ignore_index=True)
        model_mae, model_rmse, model_n = _metrics(
            residuals["observed"].to_numpy(float), residuals["predicted"].to_numpy(float)
        )
        clim_mae, clim_rmse, clim_n = _metrics(
            residuals["observed"].to_numpy(float), residuals["climatology"].to_numpy(float)
        )
        lag1 = [_autocorrelation(g["residual"], g["utc_date"], 1) for _, g in residuals.groupby("year")]
        lag7 = [_autocorrelation(g["residual"], g["utc_date"], 7) for _, g in residuals.groupby("year")]
        diagnostic_rows.append(
            {
                "buffer_km": domain.buffer_km,
                "record_type": "loyo_overall",
                "held_out_year": pd.NA,
                "n_train": final_n,
                "n_test_model": model_n,
                "n_test_climatology": clim_n,
                "parameter_count": PARAMETER_COUNT,
                "design_matrix_rank": final_rank,
                "model_mae_mol_m2": model_mae,
                "model_rmse_mol_m2": model_rmse,
                "climatology_mae_mol_m2": clim_mae,
                "climatology_rmse_mol_m2": clim_rmse,
                "mae_improvement_fraction": (clim_mae - model_mae) / clim_mae,
                "rmse_improvement_fraction": (clim_rmse - model_rmse) / clim_rmse,
                "residual_lag1_autocorrelation": float(np.nanmean(lag1)),
                "residual_lag7_autocorrelation": float(np.nanmean(lag7)),
            }
        )
        for year in ALL_YEARS:
            year_frame = frame[frame["year"].eq(year)]
            recovery = year_frame[year_frame["recovery_period"]]
            coverage_rows.append(
                {
                    "buffer_km": domain.buffer_km,
                    "year": year,
                    "calendar_days_jan_jun": int(len(year_frame)),
                    "model_training_eligible_days_jan_jun": int(year_frame["training_eligible"].sum()),
                    "recovery_calendar_days": int(len(recovery)),
                    "recovery_final_eligible_days": int(recovery["evaluation_eligible"].sum()),
                    "mean_population_coverage_fraction_jan_jun": float(
                        year_frame["effective_population_coverage_fraction"].mean()
                    ),
                    "mean_population_coverage_fraction_recovery": float(
                        recovery["effective_population_coverage_fraction"].mean()
                    ),
                    "minimum_population_coverage_fraction_recovery": float(
                        recovery["effective_population_coverage_fraction"].min()
                    ),
                }
            )
    return pd.DataFrame(diagnostic_rows), pd.DataFrame(coverage_rows)


def _year_arrays(frame: pd.DataFrame) -> dict[int, dict[str, np.ndarray]]:
    arrays: dict[int, dict[str, np.ndarray]] = {}
    for year in ALL_YEARS:
        year_frame = frame[frame["year"].eq(year)].sort_values("utc_date")
        recovery = year_frame[year_frame["recovery_period"]]
        if len(recovery) != 61:
            raise ReproductionError(f"Recovery calendar is not 61 days in {year}")
        arrays[year] = {
            "train_x": _design_matrix(year_frame),
            "train_y": pd.to_numeric(year_frame["observed_no2_mol_m2"], errors="coerce").to_numpy(float),
            "train_eligible": year_frame["training_eligible"].to_numpy(bool),
            "eval_x": _design_matrix(recovery),
            "eval_observed_population": pd.to_numeric(
                recovery["population_weighted_observed_no2_mol_m2"], errors="coerce"
            ).to_numpy(float),
            "eval_eligible": recovery["evaluation_eligible"].to_numpy(bool),
        }
    return arrays


def run_bootstrap(
    domain: PreparedDomain, *, block_length: int, replicates: int
) -> pd.DataFrame:
    arrays = _year_arrays(domain.frame)
    rng = np.random.default_rng(_seed_for(domain.buffer_km, block_length))
    rows: list[dict[str, Any]] = []
    for replicate in range(replicates):
        row: dict[str, Any] = {
            "buffer_km": domain.buffer_km,
            "block_length_days": block_length,
            "replicate": replicate,
            "status": "SUCCESS",
            "failure_reason": "",
        }
        try:
            train_indices = {
                year: circular_moving_block_indices(len(arrays[year]["train_y"]), block_length, rng)
                for year in HISTORICAL_YEARS
            }
            eval_indices = {
                year: circular_moving_block_indices(61, block_length, rng)
                for year in ALL_YEARS
            }
            sampled_train: dict[int, tuple[np.ndarray, np.ndarray]] = {}
            for year in HISTORICAL_YEARS:
                index = train_indices[year]
                eligible = arrays[year]["train_eligible"][index]
                sampled_train[year] = (
                    arrays[year]["train_x"][index][eligible],
                    arrays[year]["train_y"][index][eligible],
                )
            sampled_eval: dict[int, tuple[np.ndarray, np.ndarray]] = {}
            for year in ALL_YEARS:
                index = eval_indices[year]
                eligible = arrays[year]["eval_eligible"][index]
                if int(eligible.sum()) < MIN_EVALUATION_DAYS:
                    raise ReproductionError(f"insufficient evaluation days: {year}")
                sampled_eval[year] = (
                    arrays[year]["eval_x"][index][eligible],
                    arrays[year]["eval_observed_population"][index][eligible],
                )
            final_x = np.concatenate([sampled_train[year][0] for year in HISTORICAL_YEARS])
            final_y = np.concatenate([sampled_train[year][1] for year in HISTORICAL_YEARS])
            final_coefficients, _, _ = _fit_coefficients(final_x, final_y)
            event_x, event_observed = sampled_eval[2026]
            event_anomaly = float(np.mean(event_observed - event_x @ final_coefficients))
            historical_anomalies = {}
            historical_observed = {}
            for held_year in HISTORICAL_YEARS:
                train_years = [year for year in HISTORICAL_YEARS if year != held_year]
                fold_x = np.concatenate([sampled_train[year][0] for year in train_years])
                fold_y = np.concatenate([sampled_train[year][1] for year in train_years])
                coefficients, _, _ = _fit_coefficients(fold_x, fold_y)
                eval_x, observed = sampled_eval[held_year]
                historical_anomalies[held_year] = float(np.mean(observed - eval_x @ coefficients))
                historical_observed[held_year] = float(np.mean(observed))
            historical_mean = float(np.mean(list(historical_anomalies.values())))
            row.update(
                {
                    "adjusted_difference_mol_m2": event_anomaly - historical_mean,
                    "unadjusted_observed_difference_mol_m2": float(
                        np.mean(event_observed) - np.mean(list(historical_observed.values()))
                    ),
                }
            )
        except (ReproductionError, np.linalg.LinAlgError, ValueError) as exc:
            row["status"] = "FAILED"
            row["failure_reason"] = str(exc)
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_bootstrap(
    prepared: Iterable[PreparedDomain], replicates: pd.DataFrame
) -> pd.DataFrame:
    prepared_map = {domain.buffer_km: domain for domain in prepared}
    rows = []
    for (buffer_km, block_length), group in replicates.groupby(
        ["buffer_km", "block_length_days"], sort=True
    ):
        domain = prepared_map[int(buffer_km)]
        successful = group[group["status"].eq("SUCCESS")]
        success_rate = len(successful) / len(group)
        adjusted = pd.to_numeric(successful["adjusted_difference_mol_m2"], errors="coerce").dropna()
        unadjusted = pd.to_numeric(
            successful["unadjusted_observed_difference_mol_m2"], errors="coerce"
        ).dropna()
        allowed = success_rate >= SUCCESS_THRESHOLD
        aq = adjusted.quantile([0.025, 0.5, 0.975]) if allowed else pd.Series({0.025: np.nan, 0.5: np.nan, 0.975: np.nan})
        uq = unadjusted.quantile([0.025, 0.5, 0.975]) if allowed else pd.Series({0.025: np.nan, 0.5: np.nan, 0.975: np.nan})
        rows.append(
            {
                "analysis_id": ANALYSIS_ID,
                "buffer_km": int(buffer_km),
                "block_length_days": int(block_length),
                "analysis_role": "primary" if int(block_length) == PRIMARY_BLOCK_DAYS else "sensitivity",
                "replicates_requested": int(len(group)),
                "replicates_successful": int(len(successful)),
                "success_rate": float(success_rate),
                "failure_reasons_json": json.dumps(
                    Counter(group.loc[group["status"].eq("FAILED"), "failure_reason"]), sort_keys=True
                ),
                "frozen_point_estimate_mol_m2": domain.frozen_point_estimate,
                "q2_5_adjusted_difference_mol_m2": float(aq.loc[0.025]),
                "q50_adjusted_difference_mol_m2": float(aq.loc[0.5]),
                "q97_5_adjusted_difference_mol_m2": float(aq.loc[0.975]),
                "frozen_unadjusted_observed_difference_mol_m2": domain.frozen_unadjusted_difference,
                "q2_5_unadjusted_observed_difference_mol_m2": float(uq.loc[0.025]),
                "q50_unadjusted_observed_difference_mol_m2": float(uq.loc[0.5]),
                "q97_5_unadjusted_observed_difference_mol_m2": float(uq.loc[0.975]),
                "unit": NO2_UNIT,
                "interpretation": INTERPRETATION,
            }
        )
    return pd.DataFrame(rows).sort_values(["buffer_km", "block_length_days"], ignore_index=True)


def run(input_path: Path, output_root: Path, replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    prepared, audit = load_domains(input_path)
    diagnostics, coverage = model_diagnostics(prepared)
    replicate_parts = []
    for domain in prepared:
        for block in (PRIMARY_BLOCK_DAYS, *SENSITIVITY_BLOCK_DAYS):
            replicate_parts.append(run_bootstrap(domain, block_length=block, replicates=replicates))
    summary = summarize_bootstrap(prepared, pd.concat(replicate_parts, ignore_index=True))
    output_root.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_root / "no2_full_refit_bootstrap_summary.csv", index=False)
    diagnostics.to_csv(output_root / "no2_model_diagnostics.csv", index=False)
    coverage.to_csv(output_root / "no2_population_coverage.csv", index=False)
    result = {
        "seed": GLOBAL_SEED,
        "replicates_per_domain_and_block": int(replicates),
        "domains_km": list(DOMAINS_KM),
        "primary_block_days": PRIMARY_BLOCK_DAYS,
        "sensitivity_block_days": list(SENSITIVITY_BLOCK_DAYS),
        "input_audit": audit,
        "interpretation": INTERPRETATION,
    }
    (output_root / "no2_reproduction.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    repository = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--input",
        type=Path,
        default=repository / "data/files/statistical_inputs/no2_full_refit_daily_design.csv",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=repository / "reproduced_outputs/no2",
    )
    parser.add_argument("--replicates", type=int, default=BOOTSTRAP_REPLICATES)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.replicates <= 0:
        raise ReproductionError("replicates must be positive")
    result = run(args.input.resolve(), args.output_root.resolve(), args.replicates)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

