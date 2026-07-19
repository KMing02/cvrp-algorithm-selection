"""Speed-versus-quality extension: PyVRP hybrid genetic search as a heavyweight reference.

This experiment benchmarks PyVRP's hybrid genetic search (HGS) at the same
fixed 20-second budget used by the classical-heuristic portfolio, on a
stratified subsample of the frozen test split plus the CVRPLIB benchmark
E-n51-k5. HGS is deliberately kept *outside* the ML selector's portfolio: it
wins nearly every instance when allowed the full budget, which would collapse
the label distribution into one dominant class and trivialise the selection
problem. Instead, HGS quantifies the trade-off between the ML-selected fast
heuristic (sub-second answers) and a state-of-the-art metaheuristic that
consumes the entire budget.

Every HGS solution is converted to the project's canonical route
representation, revalidated by the independent validator, and re-costed by the
independent cost function under the instance's own distance convention, so
HGS costs are directly comparable to the frozen portfolio costs.

Outputs (``reports/hgs_benchmark/``):

- ``hgs_benchmark.csv``: one row per sampled instance with VBS cost,
  RF-selected solver cost/runtime, SBS cost, HGS cost/runtime, and gaps.
- ``hgs_summary.json``: aggregate quality gains, win rates, runtime ratios,
  environment versions, and the E-n51-k5 result.
"""

from __future__ import annotations

import json
import math
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cvrp_algorithm_selection.costs import solution_cost
from cvrp_algorithm_selection.data import load_cvrplib_with_verypy
from cvrp_algorithm_selection.distances import distance_matrix
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.ml_experiment import (
    choose_sbs,
    final_solver_prefixes,
    train_frozen_random_forest,
)
from cvrp_algorithm_selection.solvers import TIME_BUDGET_SECONDS, verypy_solution_to_routes
from cvrp_algorithm_selection.synthetic import SyntheticCVRPConfig, generate_synthetic_instance
from cvrp_algorithm_selection.validation import validate_solution


REPORT_DIR = Path("reports/hgs_benchmark")
FINAL_ML_DIR = Path("reports/final_ml_experiment")
HGS_SEED = 0
SAMPLES_PER_CELL = 3  # per (customer_count, spatial_family) cell of the test split


def solve_with_pyvrp_hgs(
    instance: CVRPInstance,
    time_budget_seconds: float = TIME_BUDGET_SECONDS,
    seed: int = HGS_SEED,
) -> dict[str, Any]:
    """Run PyVRP HGS on one instance under a wall-clock budget.

    The model uses the instance's own (integer) distance matrix as explicit
    edges, so HGS optimises exactly the same objective as the portfolio
    solvers. The returned cost is recomputed independently.
    """

    from pyvrp import Model
    from pyvrp.stop import MaxRuntime

    if instance.depot_index != 0:
        raise ValueError("PyVRP adapter assumes depot_index == 0")

    distances = distance_matrix(instance)
    if not np.allclose(distances, np.rint(distances)):
        raise ValueError("PyVRP requires integer distances; use cvrplib_euc_2d instances")
    demands = [int(round(d)) for d in instance.demands]
    if any(abs(d - round(d)) > 1e-9 for d in instance.demands):
        raise ValueError("PyVRP requires integer demands")

    model = Model()
    # Coordinates are cosmetic once explicit edges are given; scale to ints.
    locations = [
        model.add_depot(
            x=int(round(instance.coordinates[0][0] * 1000)),
            y=int(round(instance.coordinates[0][1] * 1000)),
        )
    ]
    for node in instance.customer_indices:
        x, y = instance.coordinates[node]
        locations.append(
            model.add_client(x=int(round(x * 1000)), y=int(round(y * 1000)), delivery=[demands[node]])
        )
    model.add_vehicle_type(
        len(instance.customer_indices),
        capacity=[int(round(instance.vehicle_capacity))],
    )
    for i, frm in enumerate(locations):
        for j, to in enumerate(locations):
            if i != j:
                model.add_edge(frm, to, distance=int(round(distances[i, j])))

    started = time.perf_counter()
    result = model.solve(stop=MaxRuntime(time_budget_seconds), seed=seed, display=False)
    runtime = time.perf_counter() - started

    if not result.is_feasible():
        return {"feasible": False, "cost": None, "runtime_seconds": runtime, "n_routes": None}

    routes = verypy_solution_to_routes(
        [0] + [visit for route in result.best.routes() for visit in list(route.visits()) + [0]],
        depot_index=0,
    )
    validation = validate_solution(instance, routes)
    if not validation.feasible:
        raise RuntimeError(f"PyVRP solution failed independent validation: {validation.errors}")
    independent_cost = solution_cost(instance, routes, distances)
    if abs(independent_cost - float(result.cost())) > 1e-6:
        raise RuntimeError(
            f"independent cost {independent_cost} differs from PyVRP cost {result.cost()}"
        )
    return {
        "feasible": True,
        "cost": float(independent_cost),
        "runtime_seconds": runtime,
        "n_routes": len(routes),
    }


def sample_test_instances(test: pd.DataFrame, per_cell: int = SAMPLES_PER_CELL) -> pd.DataFrame:
    """Deterministic stratified subsample over (customer_count, spatial_family)."""

    return (
        test.sort_values("instance_id")
        .groupby(["customer_count", "spatial_family"], sort=True)
        .head(per_cell)
        .reset_index(drop=True)
    )


def _instance_from_frozen_config(instance_id: str, configs: dict[str, SyntheticCVRPConfig]) -> CVRPInstance:
    if instance_id not in configs:
        raise KeyError(f"instance {instance_id} not found in frozen generation_config.json")
    return generate_synthetic_instance(configs[instance_id])


def _load_frozen_configs() -> dict[str, SyntheticCVRPConfig]:
    raw = json.loads((FINAL_ML_DIR / "generation_config.json").read_text())
    configs = {}
    for entry in raw:
        config = SyntheticCVRPConfig(**entry)
        configs[config.stable_id()] = config
    return configs


def run_hgs_benchmark(
    output_dir: str | Path = REPORT_DIR,
    time_budget_seconds: float = TIME_BUDGET_SECONDS,
    per_cell: int = SAMPLES_PER_CELL,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    model, features, train, test = train_frozen_random_forest(FINAL_ML_DIR)
    prefixes = final_solver_prefixes()
    sbs_solver = choose_sbs(train, prefixes)
    sampled = sample_test_instances(test, per_cell=per_cell)
    predictions = model.predict(sampled[features])
    configs = _load_frozen_configs()

    checkpoint = output / "hgs_benchmark_checkpoint.csv"
    done: dict[str, dict[str, Any]] = {}
    if checkpoint.exists():
        done = {row["instance_id"]: row for row in pd.read_csv(checkpoint).to_dict(orient="records")}

    rows: list[dict[str, Any]] = []
    for (_, row), predicted in zip(sampled.iterrows(), predictions):
        instance_id = row["instance_id"]
        if instance_id in done:
            rows.append(done[instance_id])
            continue
        instance = _instance_from_frozen_config(instance_id, configs)
        hgs = solve_with_pyvrp_hgs(instance, time_budget_seconds=time_budget_seconds)

        selected_prefix = prefixes[predicted]
        selected_cost = float(row[f"{selected_prefix}_cost"])
        selected_runtime = float(row[f"{selected_prefix}_runtime"])
        if not math.isfinite(selected_cost):  # deployment fallback, as in evaluation
            selected_cost = float(row[f"{prefixes[sbs_solver]}_cost"])
            selected_runtime += float(row[f"{prefixes[sbs_solver]}_runtime"])
        vbs_cost = float(row["best_cost"])
        sbs_cost = float(row[f"{prefixes[sbs_solver]}_cost"])
        hgs_cost = hgs["cost"]

        record = {
            "instance_id": instance_id,
            "customer_count": int(row["customer_count"]),
            "spatial_family": row["spatial_family"],
            "depot_position": row["depot_position"],
            "demand_regime": row["demand_regime"],
            "vbs_cost": vbs_cost,
            "sbs_cost": sbs_cost,
            "rf_predicted_solver": predicted,
            "rf_selected_cost": selected_cost,
            "rf_selected_runtime": selected_runtime,
            "hgs_feasible": hgs["feasible"],
            "hgs_cost": hgs_cost,
            "hgs_runtime": hgs["runtime_seconds"],
            "hgs_n_routes": hgs["n_routes"],
            "hgs_gain_vs_rf_selected": (
                (selected_cost - hgs_cost) / selected_cost if hgs_cost is not None else None
            ),
            "hgs_gain_vs_vbs": ((vbs_cost - hgs_cost) / vbs_cost if hgs_cost is not None else None),
            "hgs_beats_or_ties_vbs": (hgs_cost is not None and hgs_cost <= vbs_cost + 1e-9),
        }
        rows.append(record)
        pd.DataFrame(rows).to_csv(checkpoint, index=False)
        print(f"HGS {len(rows)}/{len(sampled)}: {instance_id}", flush=True)

    frame = pd.DataFrame(rows)
    frame.to_csv(output / "hgs_benchmark.csv", index=False)

    feasible = frame[frame["hgs_feasible"].astype(bool)]
    summary = {
        "n_instances": int(len(frame)),
        "n_hgs_feasible": int(len(feasible)),
        "time_budget_seconds": time_budget_seconds,
        "hgs_seed": HGS_SEED,
        "sampling": f"first {per_cell} instances by instance_id per (customer_count, spatial_family) cell of the frozen test split",
        "sbs_solver": sbs_solver,
        "mean_hgs_gain_vs_rf_selected": float(feasible["hgs_gain_vs_rf_selected"].mean()),
        "median_hgs_gain_vs_rf_selected": float(feasible["hgs_gain_vs_rf_selected"].median()),
        "mean_hgs_gain_vs_vbs": float(feasible["hgs_gain_vs_vbs"].mean()),
        "hgs_win_or_tie_rate_vs_vbs": float(feasible["hgs_beats_or_ties_vbs"].mean()),
        "mean_hgs_runtime": float(feasible["hgs_runtime"].mean()),
        "mean_rf_selected_runtime": float(frame["rf_selected_runtime"].mean()),
        "runtime_ratio_hgs_over_rf_selected": float(
            feasible["hgs_runtime"].mean() / frame["rf_selected_runtime"].mean()
        ),
        "environment": _environment_versions(),
    }
    (output / "hgs_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def run_hgs_on_benchmark_instance(
    output_dir: str | Path = REPORT_DIR,
    benchmark_path: str | Path = "data/cvrplib/E-n51-k5.vrp",
    best_known_cost: float = 521.0,
    time_budget_seconds: float = TIME_BUDGET_SECONDS,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    instance = load_cvrplib_with_verypy(benchmark_path)
    hgs = solve_with_pyvrp_hgs(instance, time_budget_seconds=time_budget_seconds)
    result = {
        "benchmark": instance.name,
        "best_known_cost": best_known_cost,
        "hgs": hgs,
        "hgs_gap_to_best_known_percent": (
            (hgs["cost"] - best_known_cost) / best_known_cost * 100.0
            if hgs["feasible"]
            else None
        ),
        "time_budget_seconds": time_budget_seconds,
    }
    (output / "hgs_e_n51_k5.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def _environment_versions() -> dict[str, str]:
    import pyvrp
    import sklearn

    return {
        "python": platform.python_version(),
        "pyvrp": _package_version("pyvrp"),
        "scikit_learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }


def _package_version(name: str) -> str:
    from importlib.metadata import version

    return version(name)


def main() -> None:
    summary = run_hgs_benchmark()
    print(json.dumps({k: v for k, v in summary.items() if k != "environment"}, indent=2))
    demo = run_hgs_on_benchmark_instance()
    print(json.dumps(demo, indent=2))


if __name__ == "__main__":
    main()
