from pathlib import Path

import numpy as np
import pytest

from src.analysis.no2_full_refit_bootstrap import (
    BOOTSTRAP_REPLICATES,
    DOMAINS_KM,
    GLOBAL_SEED,
    PARAMETER_COUNT,
    circular_moving_block_indices,
    load_domains,
    model_diagnostics,
    run_bootstrap,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/files/statistical_inputs/no2_full_refit_daily_design.csv"


def test_circular_moving_block_indices_are_deterministic_and_bounded() -> None:
    first = circular_moving_block_indices(61, 7, np.random.default_rng(123))
    second = circular_moving_block_indices(61, 7, np.random.default_rng(123))
    assert np.array_equal(first, second)
    assert len(first) == 61
    assert int(first.min()) >= 0
    assert int(first.max()) < 61


def test_frozen_point_estimates_and_daily_contract_reproduce() -> None:
    prepared, qa = load_domains(INPUT)
    assert [domain.buffer_km for domain in prepared] == list(DOMAINS_KM)
    expected = {
        10: 2.503029954406082e-05,
        20: 2.1387914761472713e-05,
        30: 1.681268617424807e-05,
    }
    for domain in prepared:
        assert domain.frozen_point_estimate == pytest.approx(expected[domain.buffer_km], abs=1e-16)
        assert len(domain.frame) == 906
        assert not domain.frame["utc_date"].duplicated().any()
    assert qa["join_cardinality"] == "one_to_one_complete_by_utc_date_and_buffer_km"
    assert qa["units"] == "mol m-2"


def test_model_diagnostics_keep_frozen_design_and_beat_climatology() -> None:
    prepared, _ = load_domains(INPUT)
    diagnostics, coverage = model_diagnostics(prepared)
    overall = diagnostics[diagnostics["record_type"].eq("loyo_overall")]
    assert set(overall["buffer_km"]) == set(DOMAINS_KM)
    assert overall["parameter_count"].eq(PARAMETER_COUNT).all()
    assert overall["design_matrix_rank"].eq(PARAMETER_COUNT).all()
    assert overall["mae_improvement_fraction"].gt(0).all()
    assert set(coverage["year"]) == {2022, 2023, 2024, 2025, 2026}
    assert coverage["recovery_final_eligible_days"].ge(7).all()


def test_small_bootstrap_smoke_run_preserves_contract() -> None:
    prepared, _ = load_domains(INPUT)
    sample = run_bootstrap(prepared[1], block_length=7, replicates=3)
    assert len(sample) == 3
    assert sample["status"].eq("SUCCESS").all()
    assert np.isfinite(sample["adjusted_difference_mol_m2"]).all()


def test_execution_constants_are_frozen() -> None:
    assert BOOTSTRAP_REPLICATES == 5000
    assert GLOBAL_SEED == 20261013
    assert DOMAINS_KM == (10, 20, 30)

