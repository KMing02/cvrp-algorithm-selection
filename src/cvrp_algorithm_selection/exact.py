"""Exact CVRP solving with gurobipy for the problem-introduction baseline.

The model is the classic two-index arc formulation with load-propagation
(Miller-Tucker-Zemlin-style) constraints that simultaneously eliminate
subtours and enforce vehicle capacity:

    min   sum_{i != j} c_ij x_ij
    s.t.  sum_j x_ij = 1                    for every customer i (leave once)
          sum_j x_ji = 1                    for every customer i (enter once)
          sum_j x_dj = sum_j x_jd           depot departures equal returns
          u_j >= u_i + q_j - Q (1 - x_ij)   for customers i != j (load)
          q_i <= u_i <= Q                   for every customer i
          x_ij in {0, 1}

`u_i` is the cumulative load on the vehicle after serving customer `i`, so any
arc between customers propagates load and no route can exceed capacity `Q` or
form a cycle that avoids the depot. The fleet size is left free, matching the
unlimited-fleet convention used by the heuristic portfolio. Distances come
from the instance's own distance convention so exact and heuristic costs are
directly comparable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from cvrp_algorithm_selection.costs import solution_cost
from cvrp_algorithm_selection.distances import distance_matrix
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.solvers import Routes, _canonical_route
from cvrp_algorithm_selection.validation import validate_solution


@dataclass(frozen=True)
class ExactResult:
    solver_name: str
    routes: Routes
    total_distance: float | None
    lower_bound: float | None
    mip_gap: float | None
    runtime_seconds: float
    status: str
    optimal: bool
    feasible: bool
    n_variables: int
    n_constraints: int
    failure_reason: str | None = None


def solve_cvrp_with_gurobi(
    instance: CVRPInstance,
    time_limit_seconds: float = 300.0,
    log_to_console: bool = False,
) -> ExactResult:
    """Solve one CVRP instance to (near-)optimality with gurobipy.

    Returns an infeasible ExactResult with a failure_reason instead of raising
    when Gurobi cannot be used (e.g. the size-limited pip license is exceeded).
    """

    import gurobipy as gp
    from gurobipy import GRB

    depot = instance.depot_index
    customers = list(instance.customer_indices)
    nodes = [depot] + customers
    demands = instance.demands
    capacity = float(instance.vehicle_capacity)
    distances = distance_matrix(instance)

    try:
        with gp.Env(params={"OutputFlag": 1 if log_to_console else 0}) as env:
            with gp.Model("cvrp", env=env) as model:
                model.Params.TimeLimit = time_limit_seconds

                arcs = [(i, j) for i in nodes for j in nodes if i != j]
                x = model.addVars(arcs, vtype=GRB.BINARY, name="x")
                u = model.addVars(
                    customers,
                    lb={i: float(demands[i]) for i in customers},
                    ub=capacity,
                    name="u",
                )

                model.setObjective(
                    gp.quicksum(float(distances[i, j]) * x[i, j] for i, j in arcs),
                    GRB.MINIMIZE,
                )
                model.addConstrs(
                    (x.sum(i, "*") == 1 for i in customers), name="leave_once"
                )
                model.addConstrs(
                    (x.sum("*", i) == 1 for i in customers), name="enter_once"
                )
                model.addConstr(
                    x.sum(depot, "*") == x.sum("*", depot), name="depot_balance"
                )
                model.addConstrs(
                    (
                        u[j] >= u[i] + float(demands[j]) - capacity * (1 - x[i, j])
                        for i in customers
                        for j in customers
                        if i != j
                    ),
                    name="load",
                )

                model.optimize()

                status = _status_name(model.Status)
                if model.SolCount == 0:
                    return ExactResult(
                        solver_name="gurobipy-MTZ",
                        routes=[],
                        total_distance=None,
                        lower_bound=model.ObjBound if _has_bound(model) else None,
                        mip_gap=None,
                        runtime_seconds=float(model.Runtime),
                        status=status,
                        optimal=False,
                        feasible=False,
                        n_variables=model.NumVars,
                        n_constraints=model.NumConstrs,
                        failure_reason=f"no incumbent (status {status})",
                    )

                routes = _extract_routes(x, depot, customers)
                validation = validate_solution(instance, routes)
                if not validation.feasible:
                    raise RuntimeError(
                        f"gurobi solution failed independent validation: {validation.errors}"
                    )
                total = solution_cost(instance, routes, distances)
                if abs(total - model.ObjVal) > 1e-6:
                    raise RuntimeError(
                        f"independent cost {total} differs from Gurobi objective {model.ObjVal}"
                    )
                return ExactResult(
                    solver_name="gurobipy-MTZ",
                    routes=routes,
                    total_distance=float(total),
                    lower_bound=float(model.ObjBound),
                    mip_gap=float(model.MIPGap) if math.isfinite(model.MIPGap) else None,
                    runtime_seconds=float(model.Runtime),
                    status=status,
                    optimal=model.Status == GRB.OPTIMAL,
                    feasible=True,
                    n_variables=model.NumVars,
                    n_constraints=model.NumConstrs,
                )
    except gp.GurobiError as exc:
        return ExactResult(
            solver_name="gurobipy-MTZ",
            routes=[],
            total_distance=None,
            lower_bound=None,
            mip_gap=None,
            runtime_seconds=0.0,
            status="GurobiError",
            optimal=False,
            feasible=False,
            n_variables=0,
            n_constraints=0,
            failure_reason=f"GurobiError: {exc}",
        )


def _extract_routes(x, depot: int, customers: list[int]) -> Routes:
    successor: dict[int, list[int]] = {depot: []}
    for customer in customers:
        successor[customer] = []
    for (i, j), var in x.items():
        if var.X > 0.5:
            successor[i].append(j)
    for customer in customers:
        if len(successor[customer]) != 1:
            raise RuntimeError(f"customer {customer} has out-degree {len(successor[customer])}")

    routes: Routes = []
    for start in successor[depot]:
        route = []
        node = start
        while node != depot:
            route.append(node)
            node = successor[node][0]
        routes.append(route)
    return sorted(_canonical_route(route) for route in routes)


def _status_name(status_code: int) -> str:
    from gurobipy import GRB

    names = {
        value: name
        for name, value in vars(GRB.Status).items()
        if not name.startswith("_")
    }
    return names.get(status_code, str(status_code))


def _has_bound(model) -> bool:
    try:
        return math.isfinite(model.ObjBound)
    except Exception:
        return False
