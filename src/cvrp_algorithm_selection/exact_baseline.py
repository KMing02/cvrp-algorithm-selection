"""Problem-introduction experiment: solve instances with gurobipy and heuristically.

This module produces the artifacts for the report requirement to introduce the
CVRP by solving benchmark or self-created instances both exactly (gurobipy)
and heuristically (the VeRyPy portfolio):

- ``run_exact_vs_heuristic`` solves the tiny manual instance and two
  self-created synthetic instances with the gurobipy MIP model and with all
  five portfolio heuristics, reporting each heuristic's gap to the proven
  optimum.
- ``run_benchmark_selector_demo`` solves the CVRPLIB benchmark E-n51-k5 with
  the heuristic portfolio, compares against the best-known solution (521),
  attempts the exact model (honestly recording the size-limited-license
  failure if Gurobi's pip license cannot fit the model), and runs the trained
  Random Forest selector on the benchmark's features.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from cvrp_algorithm_selection.data import load_cvrplib_with_verypy, tiny_manual_instance
from cvrp_algorithm_selection.exact import solve_cvrp_with_gurobi
from cvrp_algorithm_selection.features import extract_instance_features
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.ml_experiment import RANDOM_STATE, train_frozen_random_forest
from cvrp_algorithm_selection.solvers import final_ml_solver_portfolio
from cvrp_algorithm_selection.synthetic import SyntheticCVRPConfig, generate_synthetic_instance


REPORT_DIR = Path("reports/exact_baseline")
FINAL_ML_DIR = Path("reports/final_ml_experiment")

# Proven optimal solution value for CVRPLIB E-n51-k5 (Christofides & Eilon,
# rounded EUC_2D distances), see http://vrp.galgos.inf.puc-rio.br/
BEST_KNOWN_E_N51_K5 = 521.0


def introduction_instances() -> list[CVRPInstance]:
    """The tiny manual instance plus two self-created synthetic instances.

    The synthetic instances reuse configurations from the final dataset
    design, so the exact baseline describes the same instance distribution the
    selector is trained on. Sizes stay small enough for Gurobi's size-limited
    pip license (21 nodes -> 440 variables, well below the 2000 limit).
    """

    configs = [
        SyntheticCVRPConfig(
            n_customers=20,
            spatial_family="uniform",
            depot_position="center",
            demand_regime="low_variance",
            seed=0,
            distance_convention="cvrplib_euc_2d",
            params={"dataset": "final", "generator_version": "2026-07-08-v1"},
        ),
        SyntheticCVRPConfig(
            n_customers=20,
            spatial_family="two_clusters",
            depot_position="corner",
            demand_regime="high_variance",
            seed=0,
            distance_convention="cvrplib_euc_2d",
            params={"dataset": "final", "generator_version": "2026-07-08-v1"},
        ),
    ]
    return [tiny_manual_instance()] + [generate_synthetic_instance(config) for config in configs]


def run_exact_vs_heuristic(
    output_dir: str | Path = REPORT_DIR,
    time_limit_seconds: float = 300.0,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for instance in introduction_instances():
        exact = solve_cvrp_with_gurobi(instance, time_limit_seconds=time_limit_seconds)
        exact_cost = exact.total_distance
        rows.append(
            {
                "instance": instance.name,
                "n_customers": len(instance.customer_indices),
                "method": "gurobipy-MTZ (exact)",
                "cost": exact_cost,
                "runtime_seconds": exact.runtime_seconds,
                "feasible": exact.feasible,
                "optimal": exact.optimal,
                "mip_gap": exact.mip_gap,
                "gap_to_exact_percent": 0.0 if exact.optimal else None,
                "n_variables": exact.n_variables,
                "n_constraints": exact.n_constraints,
                "failure_reason": exact.failure_reason,
            }
        )
        for solver in final_ml_solver_portfolio():
            result = solver.solve(instance, seed=0)
            gap = (
                (result.total_distance - exact_cost) / exact_cost * 100.0
                if result.feasible and result.total_distance is not None and exact_cost
                else None
            )
            rows.append(
                {
                    "instance": instance.name,
                    "n_customers": len(instance.customer_indices),
                    "method": solver.configuration_name,
                    "cost": result.total_distance,
                    "runtime_seconds": result.runtime_seconds,
                    "feasible": result.feasible,
                    "optimal": False,
                    "mip_gap": None,
                    "gap_to_exact_percent": gap,
                    "n_variables": None,
                    "n_constraints": None,
                    "failure_reason": result.failure_reason,
                }
            )

    frame = pd.DataFrame(rows)
    frame.to_csv(output / "exact_vs_heuristic.csv", index=False)
    summary = {
        "time_limit_seconds": time_limit_seconds,
        "instances": sorted(frame["instance"].unique().tolist()),
        "all_exact_solves_optimal": bool(
            frame[frame["method"] == "gurobipy-MTZ (exact)"]["optimal"].all()
        ),
        "rows": rows,
    }
    (output / "exact_vs_heuristic.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def run_benchmark_selector_demo(
    output_dir: str | Path = REPORT_DIR,
    benchmark_path: str | Path = "data/cvrplib/E-n51-k5.vrp",
    exact_time_limit_seconds: float = 60.0,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    instance = load_cvrplib_with_verypy(benchmark_path)

    heuristic_rows: list[dict[str, Any]] = []
    for solver in final_ml_solver_portfolio():
        result = solver.solve(instance, seed=0)
        heuristic_rows.append(
            {
                "method": solver.configuration_name,
                "cost": result.total_distance,
                "runtime_seconds": result.runtime_seconds,
                "feasible": result.feasible,
                "gap_to_best_known_percent": (
                    (result.total_distance - BEST_KNOWN_E_N51_K5) / BEST_KNOWN_E_N51_K5 * 100.0
                    if result.feasible and result.total_distance is not None
                    else None
                ),
                "failure_reason": result.failure_reason,
            }
        )
    feasible_rows = [row for row in heuristic_rows if row["feasible"]]
    if not feasible_rows:
        raise RuntimeError(
            f"no portfolio solver produced a feasible solution for {instance.name}: "
            f"{[row['failure_reason'] for row in heuristic_rows]}"
        )
    best_row = min(feasible_rows, key=lambda row: row["cost"])

    exact = solve_cvrp_with_gurobi(instance, time_limit_seconds=exact_time_limit_seconds)

    prediction = _predict_with_frozen_random_forest(instance)
    predicted_row = next(
        (row for row in heuristic_rows if row["method"] == prediction["predicted_solver"]),
        None,
    )

    demo = {
        "benchmark": instance.name,
        "n_customers": len(instance.customer_indices),
        "best_known_cost": BEST_KNOWN_E_N51_K5,
        "heuristics": heuristic_rows,
        "best_heuristic": best_row,
        "exact_attempt": asdict(exact) | {"routes": exact.routes},
        "selector": prediction
        | {
            "predicted_solver_result": predicted_row,
            "prediction_is_best_in_portfolio": bool(
                predicted_row is not None
                and predicted_row["feasible"]
                and abs(predicted_row["cost"] - best_row["cost"]) <= 1e-9
            ),
        },
    }
    (output / "benchmark_demo.json").write_text(json.dumps(demo, indent=2, sort_keys=True))
    return demo


def _predict_with_frozen_random_forest(instance: CVRPInstance) -> dict[str, Any]:
    """Train the reported Random Forest on the frozen training split and
    predict the best solver for one out-of-distribution instance."""

    model, features, train, _ = train_frozen_random_forest(FINAL_ML_DIR)

    instance_features = extract_instance_features(instance)
    X = pd.DataFrame([{name: instance_features[name] for name in features}])
    predicted = str(model.predict(X)[0])
    probabilities = {
        str(label): float(p)
        for label, p in zip(model.classes_, model.predict_proba(X)[0])
    }
    return {
        "model": "RandomForest (frozen training split, RANDOM_STATE=%d)" % RANDOM_STATE,
        "n_training_rows": int(len(train)),
        "predicted_solver": predicted,
        "class_probabilities": probabilities,
    }


def main() -> None:
    summary = run_exact_vs_heuristic()
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    demo = run_benchmark_selector_demo()
    print(
        json.dumps(
            {
                "benchmark": demo["benchmark"],
                "best_heuristic": demo["best_heuristic"],
                "selector_prediction": demo["selector"]["predicted_solver"],
                "prediction_is_best_in_portfolio": demo["selector"]["prediction_is_best_in_portfolio"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
