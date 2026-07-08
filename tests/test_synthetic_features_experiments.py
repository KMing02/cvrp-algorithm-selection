from __future__ import annotations

import math
from pathlib import Path

from cvrp_algorithm_selection.experiments import choose_best_solver, run_experiment_table, write_experiment_outputs
from cvrp_algorithm_selection.features import extract_instance_features
from cvrp_algorithm_selection.solvers import SolverAdapter, SolverResult, selected_solver_portfolio
from cvrp_algorithm_selection.synthetic import SyntheticCVRPConfig, generate_synthetic_instance
from cvrp_algorithm_selection.validation import validate_instance


def _config(seed: int = 7) -> SyntheticCVRPConfig:
    return SyntheticCVRPConfig(
        n_customers=20,
        spatial_family="clustered",
        depot_position="center",
        demand_regime="high_variance",
        seed=seed,
        distance_convention="cvrplib_euc_2d",
    )


def test_generation_is_deterministic_with_identical_seed() -> None:
    first = generate_synthetic_instance(_config(seed=7))
    second = generate_synthetic_instance(_config(seed=7))

    assert first.name == second.name
    assert first.coordinates == second.coordinates
    assert first.demands == second.demands
    assert first.vehicle_capacity == second.vehicle_capacity


def test_different_seeds_produce_different_instances() -> None:
    first = generate_synthetic_instance(_config(seed=7))
    second = generate_synthetic_instance(_config(seed=8))

    assert first.name != second.name
    assert first.coordinates != second.coordinates


def test_generated_instance_is_valid_nontrivial_and_capacity_safe() -> None:
    instance = generate_synthetic_instance(_config(seed=7))

    assert validate_instance(instance).feasible
    assert max(instance.demands[1:]) <= instance.vehicle_capacity
    assert sum(instance.demands[1:]) > instance.vehicle_capacity
    assert all(demand > 0 for demand in instance.demands[1:])


def test_features_are_finite_and_ring_ratios_sum_to_one() -> None:
    features = extract_instance_features(generate_synthetic_instance(_config(seed=7)))
    ring_sum = sum(features[f"ring_{idx}_ratio"] for idx in range(1, 6))

    assert math.isclose(ring_sum, 1.0)
    assert all(math.isfinite(value) for value in features.values())


def test_feature_extraction_does_not_depend_on_solver_outputs() -> None:
    instance = generate_synthetic_instance(_config(seed=7))
    before = extract_instance_features(instance)
    selected_solver_portfolio()[0].solve(instance, seed=0)
    after = extract_instance_features(instance)

    assert before == after


def test_stable_instance_ids() -> None:
    assert _config(seed=7).stable_id() == _config(seed=7).stable_id()
    assert _config(seed=7).stable_id() != _config(seed=8).stable_id()


def test_label_matches_minimum_feasible_solver_cost() -> None:
    fast = SolverResult("s", "fast", [], 10.0, 2.0, True)
    cheap = SolverResult("s", "cheap", [], 9.0, 5.0, True)
    failed = SolverResult("s", "failed", [], None, 1.0, False, failure_reason="boom")

    assert choose_best_solver([fast, cheap, failed]).configuration_name == "cheap"


def test_tie_breaking_uses_runtime_when_costs_within_tolerance() -> None:
    slow = SolverResult("s", "slow", [], 10.0, 2.0, True)
    fast = SolverResult("s", "fast", [], 10.0 + 5e-10, 1.0, True)

    assert choose_best_solver([slow, fast], tie_tolerance=1e-9).configuration_name == "fast"


def test_one_solver_failure_does_not_abort_batch() -> None:
    instance = generate_synthetic_instance(_config(seed=7))
    failing = SolverAdapter("broken", "broken-config", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    working = selected_solver_portfolio()[0]

    rows = run_experiment_table([instance], solvers=[failing, working], seed=0)

    assert len(rows) == 1
    assert rows[0]["broken_config_feasible"] is False
    assert "RuntimeError" in rows[0]["broken_config_failure_reason"]
    assert rows[0]["valid_label"] is True


def test_experiment_output_schema(tmp_path: Path) -> None:
    instance = generate_synthetic_instance(_config(seed=7))
    rows = run_experiment_table([instance], solvers=[selected_solver_portfolio()[0]], seed=0)
    summary = write_experiment_outputs(rows, tmp_path)

    expected = {
        "instance_id",
        "seed",
        "spatial_family",
        "depot_position",
        "demand_regime",
        "customer_count",
        "distance_convention",
        "n_customers",
        "ring_1_ratio",
        "best_solver",
        "best_cost",
        "valid_label",
        "cw64_ps_minimize_distance_plus_2opt1_cost",
        "cw64_ps_minimize_distance_plus_2opt1_runtime",
        "cw64_ps_minimize_distance_plus_2opt1_feasible",
    }
    assert expected.issubset(rows[0])
    assert summary["number_of_instances"] == 1
    assert (tmp_path / "experiment_table.csv").exists()
    assert (tmp_path / "summary.json").exists()
