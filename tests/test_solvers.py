from __future__ import annotations

import math
from pathlib import Path

from cvrp_algorithm_selection.data import load_cvrplib_with_verypy, tiny_manual_instance
from cvrp_algorithm_selection.solvers import (
    benchmark,
    candidate_solver_portfolio,
    final_ml_solver_portfolio,
    recommended_solver_portfolio,
    selected_solver_portfolio,
    verypy_solution_to_routes,
)
from cvrp_algorithm_selection.validation import validate_solution


def test_verypy_output_conversion() -> None:
    assert verypy_solution_to_routes([0, 1, 3, 0, 2, 4, 0, 5, 6, 0]) == [
        [1, 3],
        [2, 4],
        [5, 6],
    ]
    assert verypy_solution_to_routes([0, 0, 1, 0]) == [[1]]
    assert verypy_solution_to_routes([0, 6, 5, 0, 3, 1, 0]) == [[1, 3], [5, 6]]


def test_candidate_portfolio_has_distinct_configurations() -> None:
    configs = [solver.configuration_name for solver in candidate_solver_portfolio()]

    assert len(configs) >= 10
    assert len(configs) == len(set(configs))
    assert "MJ76-insertion/all-strain" in configs
    assert "Be83-RFCS/default" in configs


def test_recommended_portfolio_has_expected_size_and_distinct_configurations() -> None:
    configs = [solver.configuration_name for solver in recommended_solver_portfolio()]

    assert 4 <= len(configs) <= 6
    assert len(configs) == len(set(configs))


def test_final_ml_portfolio_excludes_gaskell_and_has_five_solvers() -> None:
    configs = [solver.configuration_name for solver in final_ml_solver_portfolio()]

    assert len(configs) == 5
    assert "Gaskell-PS/both-savings" not in configs
    assert "CW64-PS/minimize-distance+2opt1" in configs


def test_all_selected_solvers_return_feasible_solutions_on_tiny_instance() -> None:
    instance = tiny_manual_instance()

    for solver in selected_solver_portfolio():
        result = solver.solve(instance, seed=123)
        assert result.feasible, result
        assert result.total_distance is not None
        assert result.library_cost is not None
        assert result.cost_discrepancy is not None
        assert result.cost_discrepancy < 1e-7
        assert validate_solution(instance, result.routes).feasible


def test_selected_solvers_are_reproducible_on_tiny_instance() -> None:
    instance = tiny_manual_instance()

    for solver in selected_solver_portfolio():
        first = solver.solve(instance, seed=123)
        second = solver.solve(instance, seed=123)
        assert first.routes == second.routes
        assert math.isclose(first.total_distance or 0.0, second.total_distance or 0.0)


def test_all_selected_solvers_return_feasible_solutions_on_cvrplib_fixture() -> None:
    instance = load_cvrplib_with_verypy(Path("data/cvrplib/E-n51-k5.vrp"))
    results = benchmark(instance, seed=123)

    assert len(results) == len(selected_solver_portfolio())
    for result in results:
        assert result.feasible, result
        assert result.total_distance is not None
        assert validate_solution(instance, result.routes).feasible
