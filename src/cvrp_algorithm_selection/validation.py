"""Independent CVRP instance and solution validation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from cvrp_algorithm_selection.costs import route_cost, solution_cost
from cvrp_algorithm_selection.distances import distance_matrix, instance_distance_convention
from cvrp_algorithm_selection.instance import CVRPInstance


@dataclass(frozen=True)
class ValidationResult:
    feasible: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    route_demands: tuple[float, ...] = ()
    route_costs: tuple[float, ...] = ()
    total_cost: float | None = None
    missing_customers: tuple[int, ...] = ()
    duplicate_customers: tuple[int, ...] = ()


@dataclass
class _ValidationState:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_instance(instance: CVRPInstance) -> ValidationResult:
    state = _ValidationState()

    if not instance.name:
        state.errors.append("instance name must be non-empty")
    if not instance.coordinates:
        state.errors.append("instance must contain at least one node")
    if len(instance.coordinates) != len(instance.demands):
        state.errors.append("coordinates and demands must have the same length")
    if not 0 <= instance.depot_index < len(instance.coordinates):
        state.errors.append(f"invalid depot index {instance.depot_index}")
    if not math.isfinite(instance.vehicle_capacity) or instance.vehicle_capacity <= 0:
        state.errors.append("vehicle capacity must be a finite positive number")
    try:
        instance_distance_convention(instance)
    except ValueError as exc:
        state.errors.append(str(exc))

    for idx, coord in enumerate(instance.coordinates):
        if len(coord) != 2 or not all(math.isfinite(value) for value in coord):
            state.errors.append(f"node {idx} has invalid coordinates {coord}")

    for idx, demand in enumerate(instance.demands):
        if not math.isfinite(demand) or demand < 0:
            state.errors.append(f"node {idx} has invalid demand {demand}")
        if idx == instance.depot_index and demand != 0:
            state.errors.append("depot demand must be zero")
        if idx != instance.depot_index and demand > instance.vehicle_capacity:
            state.errors.append(
                f"customer {idx} demand {demand} exceeds vehicle capacity {instance.vehicle_capacity}"
            )

    if not state.errors:
        distances = distance_matrix(instance)
        if distances.shape != (instance.size, instance.size):
            state.errors.append("distance matrix has invalid shape")
        if not np.all(np.isfinite(distances)):
            state.errors.append("distance matrix contains non-finite values")
        if not np.allclose(distances, distances.T):
            state.errors.append("distance matrix is not symmetric")
        if not np.allclose(np.diag(distances), 0.0):
            state.errors.append("distance matrix diagonal is not zero")

    return ValidationResult(feasible=not state.errors, errors=tuple(state.errors), warnings=tuple(state.warnings))


def validate_solution(instance: CVRPInstance, routes: list[list[int]]) -> ValidationResult:
    instance_validation = validate_instance(instance)
    errors = list(instance_validation.errors)
    warnings = list(instance_validation.warnings)
    route_demands: list[float] = []
    route_costs: list[float] = []

    expected = set(instance.customer_indices)
    visits: list[int] = []

    for route_idx, route in enumerate(routes):
        if not route:
            warnings.append(f"route {route_idx} is empty and contributes zero cost")
            route_demands.append(0.0)
            route_costs.append(0.0)
            continue

        for node in route:
            if not isinstance(node, int):
                errors.append(f"route {route_idx} contains non-integer node {node!r}")
                continue
            if node == instance.depot_index:
                errors.append(f"route {route_idx} includes depot {node}; depot must be implicit")
            if node < 0 or node >= instance.size:
                errors.append(f"route {route_idx} contains invalid customer index {node}")
                continue
            visits.append(node)

        valid_nodes = [node for node in route if isinstance(node, int) and 0 <= node < instance.size]
        demand = sum(instance.demands[node] for node in valid_nodes if node != instance.depot_index)
        route_demands.append(float(demand))
        if demand > instance.vehicle_capacity:
            errors.append(
                f"route {route_idx} demand {demand} exceeds capacity {instance.vehicle_capacity}"
            )

    duplicate_customers = tuple(sorted(node for node in expected if visits.count(node) > 1))
    missing_customers = tuple(sorted(expected.difference(visits)))
    unexpected_customers = tuple(sorted(set(visits).difference(expected)))

    if missing_customers:
        errors.append(f"missing customers: {list(missing_customers)}")
    if duplicate_customers:
        errors.append(f"duplicated customers: {list(duplicate_customers)}")
    if unexpected_customers:
        errors.append(f"unexpected customers: {list(unexpected_customers)}")

    total_cost: float | None = None
    if not errors:
        distances = distance_matrix(instance)
        route_costs = [route_cost(instance, route, distances) for route in routes]
        total_cost = solution_cost(instance, routes, distances)
        if not all(math.isfinite(cost) for cost in route_costs) or not math.isfinite(total_cost):
            errors.append("solution contains non-finite route or total cost")
            total_cost = None

    return ValidationResult(
        feasible=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        route_demands=tuple(route_demands),
        route_costs=tuple(float(cost) for cost in route_costs),
        total_cost=total_cost,
        missing_customers=missing_customers,
        duplicate_customers=duplicate_customers,
    )
