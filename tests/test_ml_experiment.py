from __future__ import annotations

import math

import numpy as np
import pandas as pd

from cvrp_algorithm_selection.ml_experiment import (
    choose_sbs,
    evaluate_predictions,
    feature_columns,
    make_train_test_split,
    validate_feature_columns,
    validate_label_minima,
)


PREFIXES = {
    "solver_a": "solver_a",
    "solver_b": "solver_b",
}


def _row(idx: int, label: str, a_cost: float, b_cost: float) -> dict:
    return {
        "instance_id": f"i{idx}",
        "seed": idx,
        "spatial_family": "uniform",
        "depot_position": "center",
        "demand_regime": "low_variance",
        "customer_count": 20,
        "distance_convention": "cvrplib_euc_2d",
        "n_customers": 20.0,
        "capacity": 100.0 + idx,
        "ring_1_ratio": 0.2,
        "solver_a_cost": a_cost,
        "solver_a_runtime": 1.0,
        "solver_a_feasible": True,
        "solver_a_failure_reason": None,
        "solver_b_cost": b_cost,
        "solver_b_runtime": 2.0,
        "solver_b_feasible": True,
        "solver_b_failure_reason": None,
        "best_solver": label,
        "best_cost": min(a_cost, b_cost),
        "best_runtime_among_tied_costs": 1.0 if a_cost <= b_cost else 2.0,
        "valid_label": True,
    }


def _frame() -> pd.DataFrame:
    rows = []
    for idx in range(10):
        rows.append(_row(idx, "solver_a", 10.0 + idx, 12.0 + idx))
    for idx in range(10, 20):
        rows.append(_row(idx, "solver_b", 13.0 + idx, 11.0 + idx))
    return pd.DataFrame(rows)


def test_five_class_label_validation_checks_minimum_cost() -> None:
    df = _frame()
    validate_label_minima(df, PREFIXES)
    bad = df.copy()
    bad.loc[0, "best_solver"] = "solver_b"

    try:
        validate_label_minima(bad, PREFIXES)
    except ValueError as exc:
        assert "label mismatch" in str(exc)
    else:
        raise AssertionError("expected label mismatch")


def test_feature_columns_exclude_leakage_columns() -> None:
    cols = feature_columns(_frame())

    assert "capacity" in cols
    assert "solver_a_cost" not in cols
    assert "best_cost" not in cols
    assert "spatial_family" not in cols


def test_validate_feature_columns_rejects_solver_outputs() -> None:
    try:
        validate_feature_columns(["capacity", "solver_a_runtime"])
    except ValueError as exc:
        assert "prohibited" in str(exc)
    else:
        raise AssertionError("expected prohibited column failure")


def test_split_is_reproducible_and_disjoint(tmp_path) -> None:
    df = _frame()
    first = make_train_test_split(df, tmp_path)
    second = make_train_test_split(df, tmp_path)

    assert set(first["manifest"]["train_instance_ids"]).isdisjoint(first["manifest"]["test_instance_ids"])
    assert first["manifest"] == second["manifest"]


def test_sbs_uses_training_data_cost_ratios() -> None:
    assert choose_sbs(_frame(), PREFIXES) == "solver_a"


def test_vbs_regret_and_cost_ratio_integrity() -> None:
    df = _frame().iloc[:6].reset_index(drop=True)
    true = df["best_solver"].to_numpy()
    result = evaluate_predictions("VBS", true, true, df, PREFIXES, 0.0, 0.0, ["solver_a", "solver_b"])

    assert result["summary"]["mean_regret"] == 0.0
    assert result["summary"]["mean_cost_ratio"] == 1.0
    assert all(math.isfinite(v) for v in result["summary"].values() if isinstance(v, float))


def test_predicted_solver_names_map_to_cost_columns() -> None:
    df = _frame().iloc[:2].reset_index(drop=True)
    pred = np.asarray(["solver_b", "solver_a"])
    result = evaluate_predictions("test", pred, df["best_solver"].to_numpy(), df, PREFIXES, 0.0, 0.0, ["solver_a", "solver_b"])

    assert result["summary"]["mean_cost_ratio"] > 1.0
