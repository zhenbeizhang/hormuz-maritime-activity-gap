from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.port_sar_uncertainty import (
    BOOTSTRAP_REPLICATES,
    GLOBAL_SEED,
    PUBLIC_UNCERTAINTY_LABEL,
    circular_block_sample,
    feasible_rigid_shifts,
    load_port_arrays,
    maximum_one_to_one_count,
    port_block_bootstrap,
    port_point_table,
    summarize_bootstrap,
    validate_aggregate_sar,
)

ROOT = Path(__file__).resolve().parents[1]


def test_circular_block_sample_is_deterministic_and_preserves_zero_missing_counts() -> None:
    values = np.array([0.0, 1.0, np.nan, 2.0, 3.0, 4.0, 5.0])
    first = circular_block_sample(values, 7, np.random.default_rng(GLOBAL_SEED))
    second = circular_block_sample(values, 7, np.random.default_rng(GLOBAL_SEED))
    np.testing.assert_equal(first, second)
    assert len(first) == len(values)
    assert np.isnan(first).sum() == 1
    assert np.sum(first == 0) == 1


def test_one_to_one_matching_finds_maximum_cardinality_conflict_case() -> None:
    reference = np.array([[0.0, 0.0], [1.8, 0.0]])
    comparator = np.array([[0.9, 0.0], [-0.9, 0.0]])
    assert maximum_one_to_one_count(reference, comparator, 1.0) == 2
    assert maximum_one_to_one_count(reference, comparator[:1], 1.0) == 1


def test_feasible_rigid_shifts_exclude_near_zero_and_remain_valid() -> None:
    valid = np.ones((8, 8), dtype=bool)
    valid[0, :] = False
    rows = np.array([3.2, 4.2])
    cols = np.array([3.2, 4.2])
    shifts = feasible_rigid_shifts(valid, rows, cols, min_displacement_pixels=1.0)
    assert len(shifts) > 0
    assert np.all(np.hypot(shifts[:, 0], shifts[:, 1]) > 1.0)


def test_port_point_estimates_match_reported_values() -> None:
    path = ROOT / "data/files/statistical_inputs/khor_fakkan_port_daily.csv"
    points = port_point_table(load_port_arrays(path))
    event = points[points["year"].eq(2026)].iloc[0]
    assert event["acute_vs_baseline_percent"] == pytest.approx(-52.696793002915456, abs=1e-12)
    assert event["recovery_vs_baseline_percent"] == pytest.approx(75.67748410839745, abs=1e-12)
    assert points.attrs["recovery_event_vs_equal_weight_history_percent"] == pytest.approx(
        18.272425249169434, abs=1e-12
    )


def test_primary_port_block_interval_matches_publication_source() -> None:
    path = ROOT / "data/files/statistical_inputs/khor_fakkan_port_daily.csv"
    arrays = load_port_arrays(path)
    samples = port_block_bootstrap(
        arrays, block=7, replicates=BOOTSTRAP_REPLICATES, seed=GLOBAL_SEED
    )
    summary = summarize_bootstrap(samples)
    acute = summary[summary["metric"].eq("event_acute_vs_baseline_percent")].iloc[0]
    history = summary[
        summary["metric"].eq("event_acute_minus_reselected_historical_min_pp")
    ].iloc[0]
    assert acute["q025"] == pytest.approx(-88.5064935065, abs=1e-9)
    assert acute["q975"] == pytest.approx(-9.69387755102, abs=1e-9)
    assert history["q025"] == pytest.approx(-60.17269144144146, abs=1e-12)
    assert history["q975"] == pytest.approx(24.33673007500117, abs=1e-12)


def test_aggregate_sar_records_are_public_and_match_audited_totals() -> None:
    path = (
        ROOT
        / "data/files/analysis_ready/Supplementary_Data_5_acute_port_sar_robustness.csv"
    )
    result = validate_aggregate_sar(path)
    assert result == {
        "rows": 91,
        "sparse_settings": 25,
        "detector_phase_records": 6,
        "individual_locations_distributed": False,
    }
    frame = pd.read_csv(path)
    assert set(
        frame.loc[
            frame["record_family"].eq("sar_sparse_acquisition"),
            "publication_uncertainty_label",
        ].dropna()
    ) == {PUBLIC_UNCERTAINTY_LABEL}

