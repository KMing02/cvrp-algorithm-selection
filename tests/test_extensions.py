"""Tests for the HGS benchmark, CVRPLIB OOD evaluation, and tuning supplements."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cvrp_algorithm_selection.cvrplib_ood import benchmark_instance_paths, parse_sol_cost
from cvrp_algorithm_selection.data import tiny_manual_instance
from cvrp_algorithm_selection.hgs_benchmark import sample_test_instances, solve_with_pyvrp_hgs
from cvrp_algorithm_selection.instance import CVRPInstance


def test_parse_sol_cost(tmp_path: Path) -> None:
    sol = tmp_path / "toy.sol"
    sol.write_text("Route #1: 1 2 3\nRoute #2: 4 5\nCost 784\n")
    assert parse_sol_cost(sol) == 784.0
    assert parse_sol_cost(tmp_path / "missing.sol") is None


def test_benchmark_instance_paths_cover_expected_sets() -> None:
    paths, skipped = benchmark_instance_paths()
    sets = {path.parent.name for path in paths}
    assert sets == {"A", "B", "E", "P"}
    # 87 files, minus the two EXPLICIT-distance E instances without coordinates.
    assert len(paths) == 85
    assert {entry["instance"] for entry in skipped} == {"E-n13-k4", "E-n31-k7"}
    assert all(path.suffix == ".vrp" for path in paths)


def test_sample_test_instances_is_deterministic_and_stratified() -> None:
    test = pd.DataFrame(
        {
            "instance_id": [f"i{i}" for i in range(12)],
            "customer_count": [20] * 6 + [50] * 6,
            "spatial_family": ["uniform", "radial"] * 6,
        }
    )
    sampled = sample_test_instances(test, per_cell=2)
    assert len(sampled) == 8  # 2 counts x 2 families x 2 per cell
    again = sample_test_instances(test, per_cell=2)
    assert sampled["instance_id"].tolist() == again["instance_id"].tolist()


def test_solve_with_pyvrp_hgs_on_tiny_instance() -> None:
    pytest.importorskip("pyvrp")
    base = tiny_manual_instance()
    instance = CVRPInstance(
        name=base.name,
        coordinates=base.coordinates,
        demands=base.demands,
        vehicle_capacity=base.vehicle_capacity,
        depot_index=base.depot_index,
        metadata={**base.metadata, "distance_convention": "cvrplib_euc_2d"},
    )
    result = solve_with_pyvrp_hgs(instance, time_budget_seconds=0.5)
    assert result["feasible"]
    assert result["cost"] is not None and result["cost"] > 0
    assert result["n_routes"] >= 2


def test_solve_with_pyvrp_hgs_rejects_float_distances() -> None:
    pytest.importorskip("pyvrp")
    instance = tiny_manual_instance()  # euclidean_float convention
    with pytest.raises(ValueError, match="integer distances"):
        solve_with_pyvrp_hgs(instance, time_budget_seconds=0.5)
