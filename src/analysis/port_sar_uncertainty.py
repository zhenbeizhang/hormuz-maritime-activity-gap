"""Public reproduction of the port uncertainty and aggregate SAR checks.

The module recomputes the port-call point estimates and circular moving-block
bootstrap from the shared daily series.  It also validates the delayed,
aggregate SAR robustness and detector-opportunity records.  Exact detector
locations and imagery are intentionally not distributed, so the spatial null
cannot be rerun from this repository alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from scipy.spatial import cKDTree

HISTORICAL_YEARS = (2022, 2023, 2024, 2025)
EVENT_YEAR = 2026
ALL_YEARS = (*HISTORICAL_YEARS, EVENT_YEAR)
GLOBAL_SEED = 20261013
PRIMARY_BLOCK_DAYS = 7
SENSITIVITY_BLOCK_DAYS = (5, 14)
BOOTSTRAP_REPLICATES = 5000
PUBLIC_UNCERTAINTY_LABEL = "sparse_acquisition_robustness_range"


def percent_change(current: float, reference: float) -> float:
    if not np.isfinite(current) or not np.isfinite(reference) or reference == 0:
        return math.nan
    return 100.0 * (current - reference) / reference


def stable_seed(base: int, *parts: Any) -> int:
    token = "|".join([str(base), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "little")


def circular_block_sample(values: np.ndarray, block: int, rng: np.random.Generator) -> np.ndarray:
    """Sample complete circular calendar blocks; observed zeroes and NaNs move unchanged."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values.copy()
    starts = rng.integers(0, values.size, size=int(math.ceil(values.size / block)))
    offsets = np.arange(block, dtype=int)
    indices = ((starts[:, None] + offsets[None, :]) % values.size).ravel()[: values.size]
    return values[indices]


def load_port_arrays(path: Path) -> dict[int, dict[str, np.ndarray]]:
    frame = pd.read_csv(path)
    required = {"date_utc", "year", "analysis_stage", "port_calls_per_day"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Port input is missing columns: {sorted(missing)}")
    frame["date_utc"] = pd.to_datetime(frame["date_utc"], utc=True, errors="raise").dt.normalize()
    if frame.duplicated("date_utc").any():
        raise ValueError("Port input contains duplicate UTC dates.")
    series = frame.set_index("date_utc")["port_calls_per_day"].astype(float)
    arrays: dict[int, dict[str, np.ndarray]] = {}
    for year in ALL_YEARS:
        windows = {
            "baseline": (f"{year}-01-01", f"{year}-02-28"),
            "acute": (f"{year}-03-01", f"{year}-03-28"),
            "recovery": (f"{year}-05-01", f"{year}-06-30"),
        }
        arrays[year] = {}
        for phase, (start, end) in windows.items():
            calendar = pd.date_range(start, end, freq="D", tz="UTC")
            arrays[year][phase] = series.reindex(calendar).to_numpy(dtype=float, na_value=np.nan)
    return arrays


def mean_finite(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return float(finite.mean()) if len(finite) else math.nan


def port_point_table(arrays: dict[int, dict[str, np.ndarray]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for year in ALL_YEARS:
        means = {
            phase: mean_finite(arrays[year][phase])
            for phase in ("baseline", "acute", "recovery")
        }
        row: dict[str, Any] = {
            "year": year,
            **{f"{phase}_mean_calls_per_day": value for phase, value in means.items()},
        }
        row["acute_vs_baseline_percent"] = percent_change(means["acute"], means["baseline"])
        row["recovery_vs_baseline_percent"] = percent_change(means["recovery"], means["baseline"])
        for phase in ("baseline", "acute", "recovery"):
            values = arrays[year][phase]
            row[f"{phase}_calendar_days"] = int(len(values))
            row[f"{phase}_valid_days"] = int(np.isfinite(values).sum())
            row[f"{phase}_missing_days"] = int((~np.isfinite(values)).sum())
            row[f"{phase}_zero_days"] = int(np.sum(values[np.isfinite(values)] == 0))
        rows.append(row)
    points = pd.DataFrame(rows)
    historical = points[points["year"].isin(HISTORICAL_YEARS)]
    event = points[points["year"].eq(EVENT_YEAR)].iloc[0]
    points.attrs["acute_event_minus_historical_min_pp"] = float(
        event["acute_vs_baseline_percent"] - historical["acute_vs_baseline_percent"].min()
    )
    points.attrs["recovery_event_minus_historical_max_pp"] = float(
        event["recovery_vs_baseline_percent"] - historical["recovery_vs_baseline_percent"].max()
    )
    points.attrs["acute_event_vs_equal_weight_history_percent"] = percent_change(
        float(event["acute_mean_calls_per_day"]),
        float(historical["acute_mean_calls_per_day"].mean()),
    )
    points.attrs["recovery_event_vs_equal_weight_history_percent"] = percent_change(
        float(event["recovery_mean_calls_per_day"]),
        float(historical["recovery_mean_calls_per_day"].mean()),
    )
    return points


def port_block_bootstrap(
    arrays: dict[int, dict[str, np.ndarray]], *, block: int, replicates: int, seed: int
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for replicate in range(replicates):
        means: dict[int, dict[str, float]] = {}
        for year in ALL_YEARS:
            means[year] = {
                phase: mean_finite(circular_block_sample(arrays[year][phase], block, rng))
                for phase in ("baseline", "acute", "recovery")
            }
        acute = {
            year: percent_change(means[year]["acute"], means[year]["baseline"])
            for year in ALL_YEARS
        }
        recovery = {
            year: percent_change(means[year]["recovery"], means[year]["baseline"])
            for year in ALL_YEARS
        }
        historical_acute_min = min(acute[year] for year in HISTORICAL_YEARS)
        historical_recovery_max = max(recovery[year] for year in HISTORICAL_YEARS)
        rows.append(
            {
                "block_length_days": block,
                "replicate": replicate,
                "event_acute_vs_baseline_percent": acute[EVENT_YEAR],
                "event_acute_minus_reselected_historical_min_pp": acute[EVENT_YEAR]
                - historical_acute_min,
                "event_acute_vs_equal_weight_history_percent": percent_change(
                    means[EVENT_YEAR]["acute"],
                    float(np.mean([means[year]["acute"] for year in HISTORICAL_YEARS])),
                ),
                "event_recovery_vs_baseline_percent": recovery[EVENT_YEAR],
                "event_recovery_minus_reselected_historical_max_pp": recovery[EVENT_YEAR]
                - historical_recovery_max,
                "event_recovery_vs_equal_weight_history_percent": percent_change(
                    means[EVENT_YEAR]["recovery"],
                    float(np.mean([means[year]["recovery"] for year in HISTORICAL_YEARS])),
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_bootstrap(replicates: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "event_acute_vs_baseline_percent",
        "event_acute_minus_reselected_historical_min_pp",
        "event_acute_vs_equal_weight_history_percent",
        "event_recovery_vs_baseline_percent",
        "event_recovery_minus_reselected_historical_max_pp",
        "event_recovery_vs_equal_weight_history_percent",
    ]
    rows = []
    for (block,), group in replicates.groupby(["block_length_days"], sort=True):
        for metric in metrics:
            q = group[metric].quantile([0.025, 0.5, 0.975])
            rows.append(
                {
                    "block_length_days": int(block),
                    "metric": metric,
                    "q025": float(q.loc[0.025]),
                    "median": float(q.loc[0.5]),
                    "q975": float(q.loc[0.975]),
                    "n": int(group[metric].notna().sum()),
                    "interval_method": "circular_moving_block_bootstrap",
                    "historical_extreme_reselected_each_replicate": True,
                }
            )
    return pd.DataFrame(rows)


def maximum_one_to_one_count(
    reference_xy: np.ndarray,
    comparator_xy: np.ndarray,
    radius: float,
    delta_xy: tuple[float, float] = (0.0, 0.0),
) -> int:
    """Maximum-cardinality one-to-one matching under a fixed distance radius."""
    reference_xy = np.asarray(reference_xy, dtype=float)
    comparator_xy = np.asarray(comparator_xy, dtype=float)
    if not len(reference_xy) or not len(comparator_xy):
        return 0
    shifted_reference = reference_xy - np.asarray(delta_xy, dtype=float)
    neighbours = cKDTree(comparator_xy).query_ball_point(shifted_reference, r=radius)
    row_index: list[int] = []
    col_index: list[int] = []
    for row, columns in enumerate(neighbours):
        row_index.extend([row] * len(columns))
        col_index.extend(columns)
    if not row_index:
        return 0
    graph = csr_matrix(
        (np.ones(len(row_index), dtype=np.int8), (row_index, col_index)),
        shape=(len(reference_xy), len(comparator_xy)),
    )
    matched = maximum_bipartite_matching(graph, perm_type="column")
    return int(np.sum(matched >= 0))


def feasible_rigid_shifts(
    valid: np.ndarray,
    comparator_rows: np.ndarray,
    comparator_cols: np.ndarray,
    *,
    min_displacement_pixels: float,
) -> np.ndarray:
    """Enumerate integer-pixel translations that keep every comparator point valid."""
    rows = np.floor(np.asarray(comparator_rows, dtype=float)).astype(int)
    cols = np.floor(np.asarray(comparator_cols, dtype=float)).astype(int)
    if not len(rows):
        return np.empty((0, 2), dtype=np.int32)
    if np.any(rows < 0) or np.any(cols < 0) or np.any(rows >= valid.shape[0]) or np.any(cols >= valid.shape[1]):
        raise ValueError("Comparator point lies outside the mask.")
    if not np.all(valid[rows, cols]):
        raise ValueError("Comparator point lies outside valid water.")
    base_r, base_c = int(rows.min()), int(cols.min())
    offsets = np.unique(np.column_stack((rows - base_r, cols - base_c)), axis=0)
    out_h = valid.shape[0] - int(offsets[:, 0].max())
    out_w = valid.shape[1] - int(offsets[:, 1].max())
    feasible = np.ones((out_h, out_w), dtype=bool)
    for row_offset, col_offset in offsets:
        feasible &= valid[row_offset : row_offset + out_h, col_offset : col_offset + out_w]
    anchors = np.argwhere(feasible)
    shifts = anchors - np.asarray([base_r, base_c], dtype=int)
    keep = np.hypot(shifts[:, 0], shifts[:, 1]) > float(min_displacement_pixels)
    return shifts[keep].astype(np.int32, copy=False)


def validate_aggregate_sar(path: Path) -> dict[str, Any]:
    frame = pd.read_csv(path)
    forbidden_columns = {
        "projected_x_m",
        "projected_y_m",
        "longitude",
        "latitude",
        "center_row_px",
        "center_col_px",
        "mmsi",
        "imo",
        "call_sign",
    }
    if forbidden_columns.intersection(frame.columns):
        raise ValueError("Aggregate SAR file contains prohibited location or vessel fields.")
    sparse = frame[frame["record_family"].eq("sar_sparse_acquisition")]
    if len(sparse) != 25 or set(sparse["publication_uncertainty_label"].dropna()) != {PUBLIC_UNCERTAINTY_LABEL}:
        raise ValueError("Sparse-acquisition records do not match the public contract.")
    phases = frame[
        frame["record_family"].eq("detector_opportunity_baseline")
        & frame["reporting_level"].eq("phase")
    ]
    expected = {
        ("baseline", "cfar"): (238, 0.510182, 0.040782),
        ("acute", "cfar"): (339, 0.507105, 0.053852),
        ("recovery_stage", "cfar"): (302, 0.451758, 0.043418),
        ("baseline", "independent_neural"): (50, 0.331126, 0.033113),
        ("acute", "independent_neural"): (23, 0.117949, 0.020513),
        ("recovery_stage", "independent_neural"): (39, 0.216066, 0.027701),
    }
    for key, values in expected.items():
        row = phases[(phases["reporting_unit"] == key[0]) & (phases["detector"] == key[1])]
        if len(row) != 1:
            raise ValueError(f"Missing aggregate detector record: {key}")
        item = row.iloc[0]
        if int(item["matched_pair_count"]) != values[0]:
            raise ValueError(f"Matched-pair count changed for {key}")
        if not np.isclose(float(item["symmetric_match_score"]), values[1], atol=5e-7):
            raise ValueError(f"Symmetric score changed for {key}")
        if not np.isclose(float(item["null_symmetric_score_q97_5"]), values[2], atol=5e-7):
            raise ValueError(f"Opportunity baseline changed for {key}")
    return {
        "rows": int(len(frame)),
        "sparse_settings": int(len(sparse)),
        "detector_phase_records": int(len(phases)),
        "individual_locations_distributed": False,
    }


def run(data_root: Path, output_root: Path, replicates: int = BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    port_path = data_root / "files/statistical_inputs/khor_fakkan_port_daily.csv"
    sar_path = data_root / "files/analysis_ready/Supplementary_Data_5_acute_port_sar_robustness.csv"
    arrays = load_port_arrays(port_path)
    points = port_point_table(arrays)
    parts = []
    for block in (PRIMARY_BLOCK_DAYS, *SENSITIVITY_BLOCK_DAYS):
        seed = GLOBAL_SEED if block == PRIMARY_BLOCK_DAYS else stable_seed(GLOBAL_SEED, "port", block)
        parts.append(port_block_bootstrap(arrays, block=block, replicates=replicates, seed=seed))
    bootstrap = pd.concat(parts, ignore_index=True)
    summary = summarize_bootstrap(bootstrap)
    sar_qa = validate_aggregate_sar(sar_path)
    output_root.mkdir(parents=True, exist_ok=True)
    points.to_csv(output_root / "port_point_estimates.csv", index=False)
    summary.to_csv(output_root / "port_block_bootstrap_summary.csv", index=False)
    result = {
        "seed": GLOBAL_SEED,
        "replicates_per_block": int(replicates),
        "primary_block_days": PRIMARY_BLOCK_DAYS,
        "sensitivity_block_days": list(SENSITIVITY_BLOCK_DAYS),
        "port_event_acute_change_percent": float(
            points.loc[points["year"].eq(EVENT_YEAR), "acute_vs_baseline_percent"].iloc[0]
        ),
        "port_event_recovery_change_percent": float(
            points.loc[points["year"].eq(EVENT_YEAR), "recovery_vs_baseline_percent"].iloc[0]
        ),
        "recovery_event_vs_equal_weight_history_percent": float(
            points.attrs["recovery_event_vs_equal_weight_history_percent"]
        ),
        "aggregate_sar_validation": sar_qa,
        "boundary": "delayed aggregate activity only; no vessel identity or exact detector coordinates",
    }
    (output_root / "port_sar_validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    repository = Path(__file__).resolve().parents[2]
    parser.add_argument("--data-root", type=Path, default=repository / "data")
    parser.add_argument("--output-root", type=Path, default=repository / "reproduced_outputs/port_sar")
    parser.add_argument("--replicates", type=int, default=BOOTSTRAP_REPLICATES)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args.data_root.resolve(), args.output_root.resolve(), args.replicates)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

