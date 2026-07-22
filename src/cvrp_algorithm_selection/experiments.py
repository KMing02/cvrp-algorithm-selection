"""Batch experiment runner for solver portfolio comparison."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cvrp_algorithm_selection.distances import instance_distance_convention
from cvrp_algorithm_selection.features import extract_instance_features
from cvrp_algorithm_selection.instance import CVRPInstance
from cvrp_algorithm_selection.solvers import SolverAdapter, SolverResult, selected_solver_portfolio
from cvrp_algorithm_selection.validation import validate_solution


DEFAULT_TIE_TOLERANCE = 1e-9


def solver_column_prefix(result_or_solver: SolverResult | SolverAdapter) -> str:
    name = result_or_solver.configuration_name
    return (
        name.lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace("+", "_plus_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def run_experiment_table(
    instances: Iterable[CVRPInstance],
    solvers: list[SolverAdapter] | None = None,
    seed: int | None = None,
    tie_tolerance: float = DEFAULT_TIE_TOLERANCE,
) -> list[dict[str, Any]]:
    portfolio = solvers if solvers is not None else selected_solver_portfolio()
    rows: list[dict[str, Any]] = []
    for instance in instances:
        row = _base_row(instance)
        row.update(extract_instance_features(instance))
        results: list[SolverResult] = []
        for solver in portfolio:
            result = solver.solve(instance, seed=seed)
            result = _revalidate_result(instance, result)
            results.append(result)
            prefix = solver_column_prefix(result)
            row[f"{prefix}_cost"] = result.total_distance
            row[f"{prefix}_runtime"] = result.runtime_seconds
            row[f"{prefix}_feasible"] = result.feasible
            row[f"{prefix}_failure_reason"] = result.failure_reason

        label = choose_best_solver(results, tie_tolerance=tie_tolerance)
        row["tie_tolerance"] = tie_tolerance
        if label is None:
            row["valid_label"] = False
            row["best_solver"] = None
            row["best_cost"] = None
            row["best_runtime_among_tied_costs"] = None
        else:
            row["valid_label"] = True
            row["best_solver"] = label.configuration_name
            row["best_cost"] = label.total_distance
            row["best_runtime_among_tied_costs"] = label.runtime_seconds
        rows.append(row)
    return rows


def choose_best_solver(
    results: list[SolverResult],
    tie_tolerance: float = DEFAULT_TIE_TOLERANCE,
) -> SolverResult | None:
    feasible = [r for r in results if r.feasible and r.total_distance is not None]
    if not feasible:
        return None
    best_cost = min(float(r.total_distance) for r in feasible)
    tied = [r for r in feasible if abs(float(r.total_distance) - best_cost) <= tie_tolerance]
    return min(tied, key=lambda r: r.runtime_seconds)


def write_experiment_outputs(
    rows: list[dict[str, Any]],
    output_dir: str | Path,
    generation_configs: list[Any] | None = None,
    elapsed_seconds: float | None = None,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    schema = sorted({key for row in rows for key in row})
    table_path = output / "experiment_table.csv"
    with table_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=schema)
        writer.writeheader()
        writer.writerows(rows)

    if generation_configs is not None:
        config_path = output / "generation_config.json"
        with config_path.open("w", encoding="utf-8") as handle:
            json.dump([asdict(config) for config in generation_configs], handle, indent=2, sort_keys=True)

    summary = summarize_experiment(rows)
    if elapsed_seconds is not None:
        summary["elapsed_seconds"] = elapsed_seconds
    summary_path = output / "summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    return summary


def summarize_experiment(rows: list[dict[str, Any]]) -> dict[str, Any]:
    solver_prefixes = _solver_prefixes(rows)
    label_counts = Counter(row["best_solver"] for row in rows if row.get("valid_label"))
    valid_rows = sum(1 for row in rows if row.get("valid_label"))

    summary: dict[str, Any] = {
        "number_of_instances": len(rows),
        "valid_experiment_rows": valid_rows,
        "successful_solver_runs": 0,
        "failed_solver_runs": 0,
        "failure_count_by_solver": {},
        "label_counts": dict(label_counts),
        "label_percentages": {
            key: (value / valid_rows if valid_rows else 0.0) for key, value in label_counts.items()
        },
        "mean_cost_per_solver": {},
        "mean_runtime_per_solver": {},
    }

    for prefix in solver_prefixes:
        feasible_key = f"{prefix}_feasible"
        cost_key = f"{prefix}_cost"
        runtime_key = f"{prefix}_runtime"
        successes = [row for row in rows if row.get(feasible_key)]
        failures = len(rows) - len(successes)
        summary["successful_solver_runs"] += len(successes)
        summary["failed_solver_runs"] += failures
        summary["failure_count_by_solver"][prefix] = failures
        summary["mean_cost_per_solver"][prefix] = _mean(row.get(cost_key) for row in successes)
        summary["mean_runtime_per_solver"][prefix] = _mean(row.get(runtime_key) for row in rows)

    summary["label_breakdowns"] = {
        field: _label_breakdown(rows, field)
        for field in ("spatial_family", "depot_position", "demand_regime", "customer_count")
    }
    summary["solver_gap_summary"] = solver_gap_summary(rows)
    summary["feature_quality"] = feature_quality_report(rows)
    return summary


def solver_gap_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    solver_prefixes = _solver_prefixes(rows)
    summary: dict[str, dict[str, float]] = {}
    valid_rows = [row for row in rows if row.get("valid_label") and row.get("best_cost")]
    for prefix in solver_prefixes:
        gaps = []
        within_1 = 0
        within_5 = 0
        best_count = 0
        for row in valid_rows:
            cost = row.get(f"{prefix}_cost")
            best = row.get("best_cost")
            if cost is None or best is None:
                continue
            gap = (float(cost) - float(best)) / float(best)
            gaps.append(gap)
            if gap <= 0.01:
                within_1 += 1
            if gap <= 0.05:
                within_5 += 1
            if row.get("best_solver") and solver_column_prefix_name(row["best_solver"]) == prefix:
                best_count += 1
        summary[prefix] = {
            "mean_relative_cost_gap": _mean(gaps),
            "median_relative_cost_gap": float(_median(gaps)) if gaps else 0.0,
            "best_frequency": best_count / len(valid_rows) if valid_rows else 0.0,
            "within_1_percent_frequency": within_1 / len(valid_rows) if valid_rows else 0.0,
            "within_5_percent_frequency": within_5 / len(valid_rows) if valid_rows else 0.0,
        }
    return summary


def feature_quality_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metadata_and_solver_prefixes = {
        "instance_id",
        "seed",
        "spatial_family",
        "depot_position",
        "demand_regime",
        "customer_count",
        "distance_convention",
        "tie_tolerance",
        "valid_label",
        "best_solver",
        "best_cost",
        "best_runtime_among_tied_costs",
    }
    numeric_keys = [
        key
        for key in rows[0].keys()
        if key not in metadata_and_solver_prefixes
        and not key.endswith(("_cost", "_runtime", "_feasible", "_failure_reason"))
        and isinstance(rows[0].get(key), (int, float))
    ] if rows else []
    non_finite = []
    constant = []
    for key in numeric_keys:
        values = [float(row[key]) for row in rows if isinstance(row.get(key), (int, float))]
        if any(not math.isfinite(value) for value in values):
            non_finite.append(key)
        if values and max(values) == min(values):
            constant.append(key)
    return {"non_finite_features": non_finite, "constant_features": constant}


def _base_row(instance: CVRPInstance) -> dict[str, Any]:
    metadata = instance.metadata
    return {
        "instance_id": metadata.get("instance_id", instance.name),
        "seed": metadata.get("seed"),
        "spatial_family": metadata.get("spatial_family"),
        "depot_position": metadata.get("depot_position"),
        "demand_regime": metadata.get("demand_regime"),
        "customer_count": len(instance.customer_indices),
        "distance_convention": instance_distance_convention(instance),
    }


def _revalidate_result(instance: CVRPInstance, result: SolverResult) -> SolverResult:
    if not result.feasible:
        return result
    validation = validate_solution(instance, result.routes)
    if validation.feasible:
        return result
    return SolverResult(
        solver_name=result.solver_name,
        configuration_name=result.configuration_name,
        routes=result.routes,
        total_distance=None,
        runtime_seconds=result.runtime_seconds,
        feasible=False,
        raw_output=result.raw_output,
        warning=result.warning,
        failure_reason="; ".join(validation.errors),
        library_cost=result.library_cost,
        cost_discrepancy=result.cost_discrepancy,
    )


def _solver_prefixes(rows: list[dict[str, Any]]) -> list[str]:
    prefixes = set()
    for row in rows:
        for key in row:
            if key.endswith("_feasible"):
                prefixes.add(key[: -len("_feasible")])
    return sorted(prefixes)


def solver_column_prefix_name(configuration_name: str) -> str:
    return (
        configuration_name.lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace("+", "_plus_")
        .replace(" ", "_")
        .replace("__", "_")
    )


def _label_breakdown(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        if row.get("valid_label"):
            grouped[str(row.get(field))][str(row.get("best_solver"))] += 1
    return {key: dict(counter) for key, counter in grouped.items()}


def _mean(values: Iterable[Any]) -> float:
    finite = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return float(sum(finite) / len(finite)) if finite else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0
