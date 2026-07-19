"""Thin adapters around selected VeRyPy classical CVRP heuristics."""

from __future__ import annotations

import random
import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
from verypy.classic_heuristics.cheapest_insertion import cheapest_insertion_init
from verypy.classic_heuristics.cmt_2phase import cmt_2phase_init
from verypy.classic_heuristics.gaskell_savings import gaskell_savings_init
from verypy.classic_heuristics.mole_jameson_insertion import mole_jameson_insertion_init
from verypy.classic_heuristics.nearest_neighbor import nearest_neighbor_init
from verypy.classic_heuristics.parallel_savings import parallel_savings_init
from verypy.classic_heuristics.rfcs import route_first_cluster_second_init
from verypy.classic_heuristics.sequential_savings import sequential_savings_init
from verypy.classic_heuristics.sweep import sweep_init
from verypy.classic_heuristics.tyagi_nearest_neighbor import tyagi_init
from verypy.classic_heuristics.wren_holliday_sweep import wren_holliday_init
from verypy.local_search import ITEROPT, LSOPT, do_local_search
from verypy.local_search.intra_route_operators import do_2opt_move
from verypy.util import objf

from cvrp_algorithm_selection.costs import solution_cost
from cvrp_algorithm_selection.distances import distance_matrix
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.validation import validate_solution


Routes = list[list[int]]
VeryPySolver = Callable[[np.ndarray, list[float], float, np.ndarray], list[int] | None]

# Fixed per-solver wall-clock budget for the final ML portfolio. A solver that
# does not return a feasible solution within this budget is recorded as failed,
# so the "best solver" label means "best solution within the fixed time budget".
TIME_BUDGET_SECONDS = 20.0


@dataclass(frozen=True)
class SolverResult:
    solver_name: str
    configuration_name: str
    routes: Routes
    total_distance: float | None
    runtime_seconds: float
    feasible: bool
    raw_output: Any = None
    warning: str | None = None
    failure_reason: str | None = None
    library_cost: float | None = None
    cost_discrepancy: float | None = None


@dataclass(frozen=True)
class SolverAdapter:
    solver_name: str
    configuration_name: str
    _solve: VeryPySolver
    timeout_seconds: float | None = None

    def solve(self, instance: CVRPInstance, seed: int | None = None) -> SolverResult:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        distances = distance_matrix(instance)
        demands = list(instance.demands)
        started = time.perf_counter()
        raw_output: list[int] | None = None
        try:
            raw_output = self._run_with_optional_timeout(distances, demands, instance.vehicle_capacity, np.asarray(instance.coordinates))
            routes = verypy_solution_to_routes(raw_output, instance.depot_index)
            validation = validate_solution(instance, routes)
            total_distance = solution_cost(instance, routes, distances) if validation.feasible else None
            library_cost = float(objf(raw_output, distances)) if raw_output else None
            discrepancy = (
                abs(total_distance - library_cost)
                if total_distance is not None and library_cost is not None
                else None
            )
            warning = None
            if discrepancy is not None and discrepancy > 1e-7:
                warning = (
                    f"independent cost {total_distance:.12g} differs from "
                    f"VeRyPy cost {library_cost:.12g}"
                )
            return SolverResult(
                solver_name=self.solver_name,
                configuration_name=self.configuration_name,
                routes=routes,
                total_distance=total_distance,
                runtime_seconds=time.perf_counter() - started,
                feasible=validation.feasible,
                raw_output=raw_output,
                warning=warning,
                failure_reason="; ".join(validation.errors) if validation.errors else None,
                library_cost=library_cost,
                cost_discrepancy=discrepancy,
            )
        except Exception as exc:  # pragma: no cover - exercised only on third-party failure
            return SolverResult(
                solver_name=self.solver_name,
                configuration_name=self.configuration_name,
                routes=[],
                total_distance=None,
                runtime_seconds=time.perf_counter() - started,
                feasible=False,
                raw_output=raw_output,
                failure_reason=f"{type(exc).__name__}: {exc}",
            )

    def _run_with_optional_timeout(
        self,
        distances: np.ndarray,
        demands: list[float],
        capacity: float,
        coordinates: np.ndarray,
    ) -> list[int] | None:
        if self.timeout_seconds is None:
            return self._solve(distances, demands, capacity, coordinates)
        if hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread():
            return self._run_with_signal_timeout(distances, demands, capacity, coordinates)
        return self._run_with_thread_timeout(distances, demands, capacity, coordinates)

    def _run_with_signal_timeout(
        self,
        distances: np.ndarray,
        demands: list[float],
        capacity: float,
        coordinates: np.ndarray,
    ) -> list[int] | None:
        def _timeout_handler(signum: int, frame: Any) -> None:
            raise TimeoutError(f"solver exceeded {self.timeout_seconds} seconds")

        old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, self.timeout_seconds)
        try:
            return self._solve(distances, demands, capacity, coordinates)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, old_handler)

    def _run_with_thread_timeout(
        self,
        distances: np.ndarray,
        demands: list[float],
        capacity: float,
        coordinates: np.ndarray,
    ) -> list[int] | None:
        # SIGALRM is unavailable on Windows (and outside the main thread), so
        # run the solver in a daemon worker and abandon it on timeout. The
        # abandoned worker cannot be killed and may keep consuming CPU until
        # the underlying VeRyPy call returns on its own.
        holder: dict[str, Any] = {}

        def _target() -> None:
            try:
                holder["result"] = self._solve(distances, demands, capacity, coordinates)
            except BaseException as exc:
                holder["error"] = exc

        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        worker.join(self.timeout_seconds)
        if worker.is_alive():
            raise TimeoutError(f"solver exceeded {self.timeout_seconds} seconds")
        if "error" in holder:
            raise holder["error"]
        return holder.get("result")


def verypy_solution_to_routes(solution: list[int] | None, depot_index: int = 0) -> Routes:
    """Convert VeRyPy's depot-delimited flat solution to canonical routes.

    CVRP distances are symmetric in this project, so a route and its reversal
    have identical cost. Canonical orientation and ordering make deterministic
    tests robust to third-party tie handling.
    """

    if solution is None:
        return []

    routes: Routes = []
    current: list[int] = []
    for node in solution:
        if node == depot_index:
            if current:
                routes.append(current)
                current = []
        else:
            current.append(int(node))
    if current:
        routes.append(current)
    return sorted(_canonical_route(route) for route in routes)


def _canonical_route(route: list[int]) -> list[int]:
    reversed_route = list(reversed(route))
    return route if tuple(route) <= tuple(reversed_route) else reversed_route


def selected_solver_portfolio() -> list[SolverAdapter]:
    """Recommended compact portfolio after the VeRyPy candidate audit."""

    return recommended_solver_portfolio()


def recommended_solver_portfolio() -> list[SolverAdapter]:
    return [
        _with_intra_route_2opt(_parallel_clarke_wright()),
        _gaskell_savings(),
        _mole_jameson_insertion(),
        _wren_holliday_sweep(),
        _cmt_two_phase(),
        _rfcs(),
    ]


def final_ml_solver_portfolio() -> list[SolverAdapter]:
    """Five-solver portfolio used for the main ML selector.

    Every solver runs under the same fixed time budget so the resulting label
    is "best solution within TIME_BUDGET_SECONDS". Gaskell remains supported
    and documented in the audit, but it is excluded here because it had too
    few winning labels in the development audit.
    """

    return [
        replace(solver, timeout_seconds=TIME_BUDGET_SECONDS)
        for solver in (
            _with_intra_route_2opt(_parallel_clarke_wright()),
            _mole_jameson_insertion(),
            _wren_holliday_sweep(),
            _cmt_two_phase(),
            _rfcs(),
        )
    ]


def candidate_solver_portfolio() -> list[SolverAdapter]:
    """Viable deterministic candidates used for portfolio-design diagnostics."""

    return [
        _parallel_clarke_wright(),
        _sequential_clarke_wright("farthest"),
        _sequential_clarke_wright("closest"),
        _gaskell_savings(),
        _basic_sweep(),
        _wren_holliday_sweep(),
        _cheapest_insertion(),
        _mole_jameson_insertion(),
        _cmt_two_phase(),
        _rfcs(),
        _tyagi_nearest_neighbor(),
        _sequential_nearest_neighbor("farthest"),
        _sequential_nearest_neighbor("closest"),
        _with_intra_route_2opt(_parallel_clarke_wright()),
        _with_intra_route_2opt(_basic_sweep()),
        _with_intra_route_2opt(_cheapest_insertion()),
    ]


def benchmark(instance: CVRPInstance, seed: int | None = None) -> list[SolverResult]:
    """Run the six-solver audit portfolio (no time budget) on one instance.

    This is a diagnostic entry point. The ML selector experiment instead uses
    ``final_ml_solver_portfolio()``, the five-solver portfolio in which every
    solver runs under ``TIME_BUDGET_SECONDS``.
    """

    return [solver.solve(instance, seed=seed) for solver in selected_solver_portfolio()]


def _parallel_clarke_wright() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy parallel Clarke-Wright savings",
        configuration_name="CW64-PS/minimize-distance",
        _solve=lambda distances, demands, capacity, coordinates: parallel_savings_init(
            distances, demands, capacity, minimize_K=False
        ),
    )


def _sequential_clarke_wright(seed_rule: str) -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy sequential Clarke-Wright savings",
        configuration_name=f"CW64-SS/{seed_rule}-seed",
        _solve=lambda distances, demands, capacity, coordinates: sequential_savings_init(
            distances,
            demands,
            capacity,
            minimize_K=False,
            initialize_routes_with=seed_rule,
        ),
    )


def _gaskell_savings() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy Gaskell savings",
        configuration_name="Gaskell-PS/both-savings",
        _solve=lambda distances, demands, capacity, coordinates: gaskell_savings_init(
            distances,
            demands,
            capacity,
            None,
            minimize_K=False,
            savings_method="both",
        ),
    )


def _basic_sweep() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy Sweep",
        configuration_name="basic-sweep/both-directions/best-start",
        _solve=lambda distances, demands, capacity, coordinates: sweep_init(
            coordinates,
            distances,
            demands,
            capacity,
            direction="both",
        ),
    )


def _cheapest_insertion() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy cheapest insertion",
        configuration_name="cheapest-insertion/sequential-farthest",
        _solve=lambda distances, demands, capacity, coordinates: cheapest_insertion_init(
            distances,
            demands,
            capacity,
            emerging_route_count=1,
            initialize_routes_with="farthest",
        ),
    )


def _wren_holliday_sweep() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy Wren-Holliday sweep",
        configuration_name="WH72-sweep/both-directions",
        _solve=lambda distances, demands, capacity, coordinates: wren_holliday_init(
            [tuple(point) for point in coordinates.tolist()],
            distances,
            demands,
            capacity,
            direction="both",
        ),
        timeout_seconds=10.0,
    )


def _mole_jameson_insertion() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy Mole-Jameson insertion",
        configuration_name="MJ76-insertion/all-strain",
        _solve=lambda distances, demands, capacity, coordinates: mole_jameson_insertion_init(
            distances,
            demands,
            capacity,
            strain_criterion="all",
        ),
    )


def _cmt_two_phase() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy CMT two-phase",
        configuration_name="CMT79-2phase/default",
        _solve=lambda distances, demands, capacity, coordinates: cmt_2phase_init(
            distances,
            demands,
            capacity,
        ),
    )


def _rfcs() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy route-first cluster-second",
        configuration_name="Be83-RFCS/default",
        _solve=lambda distances, demands, capacity, coordinates: route_first_cluster_second_init(
            distances,
            demands,
            capacity,
        ),
    )


def _tyagi_nearest_neighbor() -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy Tyagi nearest neighbor grouping",
        configuration_name="Ty68-NN/default",
        _solve=lambda distances, demands, capacity, coordinates: tyagi_init(
            distances,
            demands,
            capacity,
        ),
    )


def _sequential_nearest_neighbor(seed_rule: str) -> SolverAdapter:
    return SolverAdapter(
        solver_name="VeRyPy sequential nearest neighbor",
        configuration_name=f"SNN/{seed_rule}-seed/both-route-ends",
        _solve=lambda distances, demands, capacity, coordinates: nearest_neighbor_init(
            distances,
            demands,
            capacity,
            emerging_route_count=1,
            initialize_routes_with=seed_rule,
            add_only_to_end=False,
        ),
    )


def _with_intra_route_2opt(base: SolverAdapter) -> SolverAdapter:
    def solve_with_2opt(
        distances: np.ndarray,
        demands: list[float],
        capacity: float,
        coordinates: np.ndarray,
    ) -> list[int] | None:
        raw = base._solve(distances, demands, capacity, coordinates)
        if raw is None:
            return None
        return do_local_search(
            [do_2opt_move],
            raw,
            distances,
            demands,
            capacity,
            operator_strategy=LSOPT.FIRST_ACCEPT,
            iteration_strategy=ITEROPT.ALL_ACCEPT,
            max_iterations=1,
        )

    return SolverAdapter(
        solver_name=f"{base.solver_name} + intra-route 2-opt",
        configuration_name=f"{base.configuration_name}+2opt1",
        _solve=solve_with_2opt,
    )
