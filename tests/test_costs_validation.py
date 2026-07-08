from __future__ import annotations

import math

import numpy as np

from cvrp_algorithm_selection.costs import euclidean_distance_matrix, route_cost, solution_cost
from cvrp_algorithm_selection.data import tiny_manual_instance
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.validation import validate_solution


def test_distance_matrix_is_symmetric_with_zero_diagonal() -> None:
    instance = tiny_manual_instance()
    distances = euclidean_distance_matrix(instance)

    assert distances.shape == (instance.size, instance.size)
    assert np.allclose(distances, distances.T)
    assert np.allclose(np.diag(distances), 0.0)


def test_known_route_and_solution_cost() -> None:
    instance = tiny_manual_instance()

    assert route_cost(instance, [1, 3]) == 12.0
    assert math.isclose(solution_cost(instance, [[1, 3], [2, 4], [5, 6]]), 50.82842712474619)


def test_valid_solution() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 3], [2, 4], [5, 6]])

    assert result.feasible
    assert result.errors == ()
    assert math.isclose(result.total_cost or 0.0, 50.82842712474619)


def test_missing_customer_detection() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 3], [2, 4], [5]])

    assert not result.feasible
    assert result.missing_customers == (6,)
    assert any("missing customers" in error for error in result.errors)


def test_duplicate_customer_detection() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 3], [2, 4], [5, 6, 1]])

    assert not result.feasible
    assert result.duplicate_customers == (1,)
    assert any("duplicated customers" in error for error in result.errors)


def test_capacity_violation_detection() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 2, 5], [3, 4], [6]])

    assert not result.feasible
    assert any("exceeds capacity" in error for error in result.errors)


def test_invalid_customer_index_detection() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 3], [2, 4], [5, 6, 99]])

    assert not result.feasible
    assert any("invalid customer index 99" in error for error in result.errors)


def test_depot_inside_route_is_rejected() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 0, 3], [2, 4], [5, 6]])

    assert not result.feasible
    assert any("includes depot" in error for error in result.errors)


def test_empty_route_is_allowed_with_warning() -> None:
    result = validate_solution(tiny_manual_instance(), [[1, 3], [], [2, 4], [5, 6]])

    assert result.feasible
    assert any("empty" in warning for warning in result.warnings)
    assert result.route_demands[1] == 0.0
    assert result.route_costs[1] == 0.0


def test_customer_demand_exceeding_capacity_invalidates_instance() -> None:
    instance = CVRPInstance(
        name="bad-demand",
        coordinates=((0.0, 0.0), (1.0, 0.0)),
        demands=(0.0, 5.0),
        vehicle_capacity=4.0,
    )

    result = validate_solution(instance, [[1]])

    assert not result.feasible
    assert any("exceeds vehicle capacity" in error for error in result.errors)
