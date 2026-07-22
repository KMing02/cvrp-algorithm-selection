"""Independent cost calculations for CVRP solutions."""

from __future__ import annotations

import math

import numpy as np

from cvrp_algorithm_selection.distances import distance_matrix
from cvrp_algorithm_selection.instance import CVRPInstance


def euclidean_distance_matrix(instance: CVRPInstance) -> np.ndarray:
    """Backward-compatible alias for the instance's configured distance matrix."""

    return distance_matrix(instance)


def route_cost(instance: CVRPInstance, route: list[int], distance_matrix: np.ndarray | None = None) -> float:
    """Cost of a depot-delimited route whose stored representation omits depot."""

    if not route:
        return 0.0

    distances = distance_matrix if distance_matrix is not None else euclidean_distance_matrix(instance)
    depot = instance.depot_index
    cost = float(distances[depot, route[0]])
    cost += sum(float(distances[a, b]) for a, b in zip(route, route[1:]))
    cost += float(distances[route[-1], depot])
    return cost


def solution_cost(
    instance: CVRPInstance,
    routes: list[list[int]],
    distance_matrix: np.ndarray | None = None,
) -> float:
    distances = distance_matrix if distance_matrix is not None else euclidean_distance_matrix(instance)
    total = sum(route_cost(instance, route, distances) for route in routes)
    if not math.isfinite(total):
        raise ValueError(f"solution cost is not finite: {total}")
    return float(total)
