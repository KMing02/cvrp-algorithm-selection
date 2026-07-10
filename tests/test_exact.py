"""Tests for the gurobipy exact CVRP baseline."""

from __future__ import annotations

import math

import pytest

gurobipy = pytest.importorskip("gurobipy")

from cvrp_algorithm_selection.data import tiny_manual_instance
from cvrp_algorithm_selection.exact import solve_cvrp_with_gurobi
from cvrp_algorithm_selection.solvers import final_ml_solver_portfolio
from cvrp_algorithm_selection.validation import validate_solution


def test_gurobi_solves_tiny_instance_to_optimality() -> None:
    instance = tiny_manual_instance()
    result = solve_cvrp_with_gurobi(instance, time_limit_seconds=60.0)

    assert result.feasible, result.failure_reason
    assert result.optimal
    assert result.total_distance is not None
    assert validate_solution(instance, result.routes).feasible
    assert math.isclose(result.mip_gap or 0.0, 0.0, abs_tol=1e-9)


def test_gurobi_optimum_is_no_worse_than_every_heuristic() -> None:
    instance = tiny_manual_instance()
    exact = solve_cvrp_with_gurobi(instance, time_limit_seconds=60.0)
    assert exact.feasible and exact.total_distance is not None

    heuristic_costs = []
    for solver in final_ml_solver_portfolio():
        result = solver.solve(instance, seed=0)
        if result.feasible and result.total_distance is not None:
            heuristic_costs.append(result.total_distance)
    assert heuristic_costs
    assert exact.total_distance <= min(heuristic_costs) + 1e-9
