"""Out-of-distribution evaluation of the frozen selector on CVRPLIB sets A, B, E, P.

The paper (Asín-Achá et al. 2024) trains on synthetic instances and tests on
public CVRPLIB benchmarks. This module mirrors that protocol at student scale:
the Random Forest selector is trained on the frozen synthetic training split
only, then evaluated on the classic CVRPLIB sets A, B, E, and P (87 instances,
32-101 nodes, rounded EUC_2D distances) that the model has never seen. Unlike
the paper we keep the original (non-unit) demands and file capacities.

For every instance, all five portfolio solvers run under the fixed 20-second
budget to establish the portfolio VBS and the ground-truth label; the selector
is scored on accuracy, routing regret against the portfolio VBS, and the
paper's normalized selector metric m-hat. Optimal values parsed from the
CVRPLIB ``.sol`` files provide the absolute quality reference.

Outputs (``reports/cvrplib_ood/``):

- ``cvrplib_ood.csv``: one row per benchmark instance (per-solver costs and
  runtimes, label, prediction, regret, gap to optimum).
- ``cvrplib_ood_summary.json``: aggregate and per-set metrics.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from cvrp_algorithm_selection.data import load_cvrplib_with_verypy
from cvrp_algorithm_selection.experiments import (
    DEFAULT_TIE_TOLERANCE,
    choose_best_solver,
    solver_column_prefix,
)
from cvrp_algorithm_selection.features import extract_instance_features
from cvrp_algorithm_selection.ml_experiment import (
    choose_sbs,
    final_solver_prefixes,
    train_frozen_random_forest,
)
from cvrp_algorithm_selection.solvers import final_ml_solver_portfolio


REPORT_DIR = Path("reports/cvrplib_ood")
DATA_DIR = Path("data/cvrplib")
BENCHMARK_SETS = ("A", "B", "E", "P")


def parse_sol_cost(path: Path) -> float | None:
    """Parse the ``Cost <value>`` line of a CVRPLIB ``.sol`` file."""

    if not path.exists():
        return None
    match = re.search(r"^Cost\s+(\d+(?:\.\d+)?)\s*$", path.read_text(), flags=re.MULTILINE | re.IGNORECASE)
    return float(match.group(1)) if match else None


def benchmark_instance_paths(data_dir: str | Path = DATA_DIR) -> tuple[list[Path], list[dict[str, str]]]:
    """All A/B/E/P instance paths with Euclidean coordinates, plus skip records.

    Instances with ``EDGE_WEIGHT_TYPE: EXPLICIT`` (distance matrix only, no
    coordinates) are skipped: the selector's features are coordinate-based.
    """

    base = Path(data_dir)
    paths: list[Path] = []
    skipped: list[dict[str, str]] = []
    for set_name in BENCHMARK_SETS:
        for path in sorted((base / set_name).glob("*.vrp")):
            header = path.read_text()[:2000]
            if "EUC_2D" in header:
                paths.append(path)
            else:
                skipped.append(
                    {
                        "instance": path.stem,
                        "benchmark_set": set_name,
                        "reason": "no Euclidean coordinates (EDGE_WEIGHT_TYPE is not EUC_2D)",
                    }
                )
    if not paths:
        raise FileNotFoundError(f"no benchmark instances found under {base}")
    return paths, skipped


def run_cvrplib_ood(
    output_dir: str | Path = REPORT_DIR,
    data_dir: str | Path = DATA_DIR,
    tie_tolerance: float = DEFAULT_TIE_TOLERANCE,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    model, features, train, _ = train_frozen_random_forest()
    prefixes = final_solver_prefixes()
    sbs_solver = choose_sbs(train, prefixes)
    portfolio = final_ml_solver_portfolio()

    checkpoint = output / "cvrplib_ood_checkpoint.csv"
    done: dict[str, dict[str, Any]] = {}
    if checkpoint.exists():
        done = {row["instance"]: row for row in pd.read_csv(checkpoint).to_dict(orient="records")}

    rows: list[dict[str, Any]] = []
    paths, skipped = benchmark_instance_paths(data_dir)
    for index, path in enumerate(paths, start=1):
        if path.stem in done:
            rows.append(done[path.stem])
            continue
        instance = load_cvrplib_with_verypy(path)
        row: dict[str, Any] = {
            "instance": instance.name,
            "benchmark_set": path.parent.name,
            "n_customers": len(instance.customer_indices),
            "optimal_cost": parse_sol_cost(path.with_suffix(".sol")),
        }

        instance_features = extract_instance_features(instance)
        X = pd.DataFrame([{name: instance_features[name] for name in features}])
        predicted = str(model.predict(X)[0])
        row["rf_predicted_solver"] = predicted

        results = []
        for solver in portfolio:
            result = solver.solve(instance, seed=0)
            results.append(result)
            prefix = solver_column_prefix(result)
            row[f"{prefix}_cost"] = result.total_distance
            row[f"{prefix}_runtime"] = result.runtime_seconds
            row[f"{prefix}_feasible"] = result.feasible

        label = choose_best_solver(results, tie_tolerance=tie_tolerance)
        if label is None:
            raise RuntimeError(f"no feasible portfolio solver on {instance.name}")
        row["best_solver"] = label.configuration_name
        row["best_cost"] = label.total_distance

        selected_cost = row.get(f"{prefixes[predicted]}_cost")
        selected_runtime = row.get(f"{prefixes[predicted]}_runtime")
        if selected_cost is None or not math.isfinite(float(selected_cost)):
            selected_cost = row[f"{prefixes[sbs_solver]}_cost"]
            selected_runtime = float(selected_runtime or 0.0) + float(row[f"{prefixes[sbs_solver]}_runtime"])
        row["rf_selected_cost"] = float(selected_cost)
        row["rf_selected_runtime"] = float(selected_runtime)
        row["sbs_cost"] = float(row[f"{prefixes[sbs_solver]}_cost"])
        row["rf_correct"] = predicted == row["best_solver"]
        row["rf_regret"] = (row["rf_selected_cost"] - row["best_cost"]) / row["best_cost"]
        row["sbs_regret"] = (row["sbs_cost"] - row["best_cost"]) / row["best_cost"]
        if row["optimal_cost"]:
            row["rf_gap_to_optimal_percent"] = (row["rf_selected_cost"] - row["optimal_cost"]) / row["optimal_cost"] * 100.0
            row["vbs_gap_to_optimal_percent"] = (row["best_cost"] - row["optimal_cost"]) / row["optimal_cost"] * 100.0
        else:
            row["rf_gap_to_optimal_percent"] = None
            row["vbs_gap_to_optimal_percent"] = None

        rows.append(row)
        pd.DataFrame(rows).to_csv(checkpoint, index=False)
        print(f"OOD {index}/{len(paths)}: {instance.name}", flush=True)

    frame = pd.DataFrame(rows)
    frame.to_csv(output / "cvrplib_ood.csv", index=False)
    summary = _summarize(frame, sbs_solver)
    summary["skipped_instances"] = skipped
    (output / "cvrplib_ood_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def _summarize(frame: pd.DataFrame, sbs_solver: str) -> dict[str, Any]:
    def _metrics(group: pd.DataFrame) -> dict[str, Any]:
        rf_ratio = float((group["rf_selected_cost"] / group["best_cost"]).mean())
        sbs_ratio = float((group["sbs_cost"] / group["best_cost"]).mean())
        m_hat = (rf_ratio - 1.0) / (sbs_ratio - 1.0) if sbs_ratio > 1.0 else None
        return {
            "n": int(len(group)),
            "rf_accuracy": float(group["rf_correct"].mean()),
            "rf_mean_regret": float(group["rf_regret"].mean()),
            "sbs_mean_regret": float(group["sbs_regret"].mean()),
            "rf_within_1_percent": float((group["rf_regret"] <= 0.01).mean()),
            "sbs_within_1_percent": float((group["sbs_regret"] <= 0.01).mean()),
            "rf_mean_cost_ratio": rf_ratio,
            "sbs_mean_cost_ratio": sbs_ratio,
            "m_hat": m_hat,
            "rf_mean_gap_to_optimal_percent": (
                float(group["rf_gap_to_optimal_percent"].dropna().mean())
                if group["rf_gap_to_optimal_percent"].notna().any()
                else None
            ),
            "vbs_mean_gap_to_optimal_percent": (
                float(group["vbs_gap_to_optimal_percent"].dropna().mean())
                if group["vbs_gap_to_optimal_percent"].notna().any()
                else None
            ),
        }

    summary: dict[str, Any] = {
        "sbs_solver": sbs_solver,
        "overall": _metrics(frame),
        "per_set": {name: _metrics(group) for name, group in frame.groupby("benchmark_set")},
        "label_counts": frame["best_solver"].value_counts().to_dict(),
        "prediction_counts": frame["rf_predicted_solver"].value_counts().to_dict(),
    }
    return summary


def main() -> None:
    summary = run_cvrplib_ood()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
