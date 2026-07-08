"""Final ML experiment pipeline for CVRP algorithm selection."""

from __future__ import annotations

import json
import math
import time
import csv
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from cvrp_algorithm_selection.experiments import (
    DEFAULT_TIE_TOLERANCE,
    run_experiment_table,
    solver_column_prefix,
    write_experiment_outputs,
)
from cvrp_algorithm_selection.solvers import SolverAdapter, final_ml_solver_portfolio
from cvrp_algorithm_selection.synthetic import final_dataset_configs, generate_synthetic_instance


RANDOM_STATE = 20260708
REPORT_DIR = Path("reports/final_ml_experiment")

PROHIBITED_FEATURE_EXACT = {
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
PROHIBITED_FEATURE_SUFFIXES = ("_cost", "_runtime", "_feasible", "_failure_reason")


def final_solver_prefixes(solvers: list[SolverAdapter] | None = None) -> dict[str, str]:
    portfolio = solvers if solvers is not None else final_ml_solver_portfolio()
    return {solver.configuration_name: solver_column_prefix(solver) for solver in portfolio}


def recompute_development_labels(output_dir: str | Path = REPORT_DIR / "development_relabel") -> dict[str, Any]:
    from cvrp_algorithm_selection.synthetic import development_dataset_configs

    output = Path(output_dir)
    table_path = output / "experiment_table.csv"
    summary_path = output / "summary.json"
    if table_path.exists() and summary_path.exists():
        df = pd.read_csv(table_path)
        validate_label_minima(df, final_solver_prefixes())
        return json.loads(summary_path.read_text())

    configs = development_dataset_configs()
    instances = [generate_synthetic_instance(config) for config in configs]
    rows = run_experiment_table(instances, solvers=final_ml_solver_portfolio(), seed=0)
    summary = write_experiment_outputs(rows, output, generation_configs=configs)
    validate_label_minima(pd.DataFrame(rows), final_solver_prefixes())
    return summary


def run_final_solver_experiment(output_dir: str | Path = REPORT_DIR) -> tuple[pd.DataFrame, dict[str, Any]]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    configs = final_dataset_configs()
    checkpoint = output / "experiment_table_checkpoint.csv"
    rows = _load_checkpoint_rows(checkpoint)
    completed_ids = {row["instance_id"] for row in rows}
    started = time.perf_counter()
    for index, config in enumerate(configs, start=1):
        instance_id = config.stable_id()
        if instance_id in completed_ids:
            continue
        instance = generate_synthetic_instance(config)
        new_row = run_experiment_table([instance], solvers=final_ml_solver_portfolio(), seed=0)[0]
        rows.append(new_row)
        completed_ids.add(instance_id)
        _write_checkpoint_rows(checkpoint, rows)
        if index % 25 == 0:
            print(f"completed {len(rows)}/{len(configs)} final instances", flush=True)
    elapsed = time.perf_counter() - started
    summary = write_experiment_outputs(rows, output, generation_configs=configs, elapsed_seconds=elapsed)
    generation_manifest = {
        "n_instances": len(rows),
        "seed_range": [0, 6],
        "distance_convention": "cvrplib_euc_2d",
        "generator_version": "2026-07-08-v1",
        "config_count": len(configs),
        "instance_ids": [row["instance_id"] for row in rows],
    }
    (output / "generation_manifest.json").write_text(json.dumps(generation_manifest, indent=2, sort_keys=True))
    df = pd.DataFrame(rows)
    validate_label_minima(df, final_solver_prefixes())
    return df, summary


def _load_checkpoint_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pd.read_csv(path).replace({np.nan: None}).to_dict(orient="records")


def _write_checkpoint_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_or_run_final_experiment(output_dir: str | Path = REPORT_DIR) -> tuple[pd.DataFrame, dict[str, Any]]:
    output = Path(output_dir)
    table_path = output / "experiment_table.csv"
    summary_path = output / "summary.json"
    if table_path.exists() and summary_path.exists():
        df = pd.read_csv(table_path)
        summary = json.loads(summary_path.read_text())
        validate_label_minima(df, final_solver_prefixes())
        return df, summary
    return run_final_solver_experiment(output)


def feature_columns(df: pd.DataFrame) -> list[str]:
    columns = []
    for column in df.columns:
        if column in PROHIBITED_FEATURE_EXACT:
            continue
        if column.endswith(PROHIBITED_FEATURE_SUFFIXES):
            continue
        if pd.api.types.is_numeric_dtype(df[column]):
            columns.append(column)
    validate_feature_columns(columns)
    return columns


def validate_feature_columns(columns: list[str]) -> None:
    bad = [
        column
        for column in columns
        if column in PROHIBITED_FEATURE_EXACT or column.endswith(PROHIBITED_FEATURE_SUFFIXES)
    ]
    if bad:
        raise ValueError(f"prohibited model feature columns: {bad}")


def make_train_test_split(df: pd.DataFrame, output_dir: str | Path = REPORT_DIR) -> dict[str, Any]:
    counts = df["best_solver"].value_counts()
    if (counts < 2).any():
        raise ValueError(f"too few samples for stratified split: {counts.to_dict()}")
    train_idx, test_idx = train_test_split(
        np.arange(len(df)),
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=df["best_solver"],
    )
    manifest = {
        "random_state": RANDOM_STATE,
        "test_size": 0.2,
        "stratify": "best_solver",
        "train_instance_ids": df.iloc[train_idx]["instance_id"].tolist(),
        "test_instance_ids": df.iloc[test_idx]["instance_id"].tolist(),
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "split_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    if set(manifest["train_instance_ids"]) & set(manifest["test_instance_ids"]):
        raise ValueError("train/test split contains overlapping instance IDs")
    return {"train_idx": train_idx, "test_idx": test_idx, "manifest": manifest}


def run_ml_evaluation(output_dir: str | Path = REPORT_DIR) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    plots_dir = output / "plots"
    plots_dir.mkdir(exist_ok=True)

    dev_summary = recompute_development_labels(output / "development_relabel")
    df, experiment_summary = load_or_run_final_experiment(output)
    prefixes = final_solver_prefixes()
    validate_label_minima(df, prefixes)
    if _dominant_label_share(df) > 0.8:
        raise RuntimeError(f"dominant label share exceeds 80%: {df['best_solver'].value_counts(normalize=True).to_dict()}")

    features = feature_columns(df)
    (output / "feature_columns.json").write_text(json.dumps(features, indent=2))
    split = make_train_test_split(df, output)
    train = df.iloc[split["train_idx"]].reset_index(drop=True)
    test = df.iloc[split["test_idx"]].reset_index(drop=True)
    X_train = train[features]
    y_train = train["best_solver"]
    X_test = test[features]
    y_test = test["best_solver"]

    sbs_solver = choose_sbs(train, prefixes)
    methods: dict[str, Any] = {
        "Dummy-most-frequent": DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE),
        "Dummy-stratified": DummyClassifier(strategy="stratified", random_state=RANDOM_STATE),
        "KNN": Pipeline([("scaler", StandardScaler()), ("model", KNeighborsClassifier(n_neighbors=7, weights="distance"))]),
        "DecisionTree": DecisionTreeClassifier(max_depth=8, min_samples_leaf=5, random_state=RANDOM_STATE),
        "RandomForest": RandomForestClassifier(
            n_estimators=250,
            max_depth=None,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=3,
            random_state=RANDOM_STATE,
        ),
    }

    model_results: list[dict[str, Any]] = []
    per_class: dict[str, Any] = {}
    confusion_matrices: dict[str, Any] = {}
    fitted_models: dict[str, Any] = {}
    selected_params: dict[str, Any] = {}
    labels = sorted(df["best_solver"].unique())

    model_predictions: dict[str, np.ndarray] = {
        "SBS": np.asarray([sbs_solver] * len(test)),
        "VBS": y_test.to_numpy(),
    }
    model_train_times = {"SBS": 0.0, "VBS": 0.0}
    model_predict_times = {"SBS": 0.0, "VBS": 0.0}

    for name, model in methods.items():
        started = time.perf_counter()
        model.fit(X_train, y_train)
        train_time = time.perf_counter() - started
        started = time.perf_counter()
        pred = model.predict(X_test)
        predict_time = time.perf_counter() - started
        model_predictions[name] = np.asarray(pred)
        model_train_times[name] = train_time
        model_predict_times[name] = predict_time
        fitted_models[name] = model
        selected_params[name] = _model_params(model)

    selected_params["SBS"] = {"solver": sbs_solver, "definition": "lowest mean cost ratio to VBS on training data"}
    selected_params["VBS"] = {"definition": "oracle minimum feasible cost per test instance"}

    for name, pred in model_predictions.items():
        metrics = evaluate_predictions(
            name,
            pred,
            y_test.to_numpy(),
            test,
            prefixes,
            model_train_times[name],
            model_predict_times[name],
            labels,
        )
        model_results.append(metrics["summary"])
        per_class[name] = metrics["per_class"]
        confusion_matrices[name] = metrics["confusion_matrix"]

    metrics_df = pd.DataFrame(model_results).sort_values(["mean_regret", "balanced_accuracy"], ascending=[True, False])
    metrics_df.to_csv(output / "model_metrics.csv", index=False)
    (output / "model_metrics.json").write_text(json.dumps(model_results, indent=2, sort_keys=True))
    (output / "per_class_metrics.json").write_text(json.dumps(per_class, indent=2, sort_keys=True))
    (output / "confusion_matrices.json").write_text(json.dumps(confusion_matrices, indent=2, sort_keys=True))
    (output / "selected_model_parameters.json").write_text(json.dumps(selected_params, indent=2, sort_keys=True))

    best_ml_name = _best_ml_model(metrics_df)
    grouped = grouped_metrics(test, model_predictions[best_ml_name], prefixes)
    (output / "grouped_metrics.json").write_text(json.dumps(grouped, indent=2, sort_keys=True))

    importance = feature_importance_reports(fitted_models["RandomForest"], X_test, y_test, features, output)
    create_plots(df, metrics_df, confusion_matrices[best_ml_name], labels, importance, output / "plots")
    summary = {
        "development_relabel_summary": dev_summary,
        "experiment_summary": experiment_summary,
        "n_rows": len(df),
        "train_rows": len(train),
        "test_rows": len(test),
        "label_counts": df["best_solver"].value_counts().to_dict(),
        "label_percentages": df["best_solver"].value_counts(normalize=True).to_dict(),
        "solver_failure_counts": {
            name: int((~df[f"{prefix}_feasible"].astype(bool)).sum()) for name, prefix in prefixes.items()
        },
        "sbs_solver": sbs_solver,
        "best_ml_model": best_ml_name,
        "feature_columns": features,
        "feature_importance": importance,
    }
    (output / "label_distribution_summary.json").write_text(
        json.dumps({"counts": summary["label_counts"], "percentages": summary["label_percentages"]}, indent=2, sort_keys=True)
    )
    (output / "experiment_summary.md").write_text(_summary_markdown(summary, metrics_df, grouped))
    (output / "ml_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def validate_label_minima(df: pd.DataFrame, prefixes: dict[str, str], tolerance: float = DEFAULT_TIE_TOLERANCE) -> None:
    for _, row in df.iterrows():
        feasible = []
        for name, prefix in prefixes.items():
            if bool(row[f"{prefix}_feasible"]) and pd.notna(row[f"{prefix}_cost"]):
                feasible.append((name, float(row[f"{prefix}_cost"]), float(row[f"{prefix}_runtime"])))
        if not feasible:
            if bool(row.get("valid_label", False)):
                raise ValueError(f"row {row.get('instance_id')} has label but no feasible solver")
            continue
        best_cost = min(cost for _, cost, _ in feasible)
        tied = [item for item in feasible if abs(item[1] - best_cost) <= tolerance]
        expected = min(tied, key=lambda item: item[2])
        if row["best_solver"] != expected[0] or abs(float(row["best_cost"]) - expected[1]) > tolerance:
            raise ValueError(
                f"label mismatch for {row.get('instance_id')}: got {(row['best_solver'], row['best_cost'])}, expected {expected}"
            )


def choose_sbs(train: pd.DataFrame, prefixes: dict[str, str]) -> str:
    ratios = {}
    for name, prefix in prefixes.items():
        ratios[name] = np.mean(train[f"{prefix}_cost"].astype(float) / train["best_cost"].astype(float))
    return min(ratios.items(), key=lambda item: item[1])[0]


def evaluate_predictions(
    method: str,
    predicted: np.ndarray,
    true: np.ndarray,
    test: pd.DataFrame,
    prefixes: dict[str, str],
    train_time: float,
    predict_time: float,
    labels: list[str],
) -> dict[str, Any]:
    selected_costs = np.asarray([float(test.iloc[i][f"{prefixes[pred]}_cost"]) for i, pred in enumerate(predicted)])
    selected_runtimes = np.asarray([float(test.iloc[i][f"{prefixes[pred]}_runtime"]) for i, pred in enumerate(predicted)])
    vbs_costs = test["best_cost"].astype(float).to_numpy()
    regrets = (selected_costs - vbs_costs) / vbs_costs
    ratios = selected_costs / vbs_costs
    if method == "VBS":
        if not np.allclose(regrets, 0.0) or not np.allclose(ratios, 1.0):
            raise ValueError("VBS regret/cost-ratio integrity check failed")

    precision, recall, f1, support = precision_recall_fscore_support(
        true, predicted, labels=labels, zero_division=0
    )
    per_class = {
        label: {
            "precision": float(precision[idx]),
            "recall": float(recall[idx]),
            "f1": float(f1[idx]),
            "support": int(support[idx]),
        }
        for idx, label in enumerate(labels)
    }
    summary = {
        "method": method,
        "accuracy": float(accuracy_score(true, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(true, predicted)),
        "macro_f1": float(f1_score(true, predicted, average="macro", zero_division=0)),
        "mean_regret": float(np.mean(regrets)),
        "median_regret": float(np.median(regrets)),
        "max_regret": float(np.max(regrets)),
        "p90_regret": float(np.quantile(regrets, 0.90)),
        "p95_regret": float(np.quantile(regrets, 0.95)),
        "mean_cost_ratio": float(np.mean(ratios)),
        "within_1_percent": float(np.mean(regrets <= 0.01)),
        "within_5_percent": float(np.mean(regrets <= 0.05)),
        "mean_selected_solver_runtime": float(np.mean(selected_runtimes)),
        "median_selected_solver_runtime": float(np.median(selected_runtimes)),
        "train_time_seconds": float(train_time),
        "predict_time_seconds": float(predict_time),
    }
    _assert_finite(summary)
    return {
        "summary": summary,
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(true, predicted, labels=labels).tolist(),
    }


def grouped_metrics(test: pd.DataFrame, predicted: np.ndarray, prefixes: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in ("spatial_family", "depot_position", "demand_regime", "customer_count", "best_solver"):
        result[field] = {}
        for value, group in test.assign(_pred=predicted).groupby(field):
            selected = np.asarray([float(row[f"{prefixes[row['_pred']]}_cost"]) for _, row in group.iterrows()])
            vbs = group["best_cost"].astype(float).to_numpy()
            regret = (selected - vbs) / vbs
            result[field][str(value)] = {
                "n": int(len(group)),
                "accuracy": float(np.mean(group["_pred"].to_numpy() == group["best_solver"].to_numpy())),
                "mean_regret": float(np.mean(regret)),
                "within_1_percent": float(np.mean(regret <= 0.01)),
            }
    return result


def feature_importance_reports(model: Any, X_test: pd.DataFrame, y_test: pd.Series, features: list[str], output: Path) -> dict[str, Any]:
    rf = model
    importances = pd.DataFrame(
        {"feature": features, "importance": rf.feature_importances_}
    ).sort_values("importance", ascending=False)
    importances.to_csv(output / "random_forest_feature_importance.csv", index=False)
    perm = permutation_importance(rf, X_test, y_test, n_repeats=5, random_state=RANDOM_STATE, n_jobs=-1)
    perm_df = pd.DataFrame(
        {"feature": features, "importance_mean": perm.importances_mean, "importance_std": perm.importances_std}
    ).sort_values("importance_mean", ascending=False)
    perm_df.to_csv(output / "permutation_importance.csv", index=False)
    return {
        "random_forest_top10": importances.head(10).to_dict(orient="records"),
        "permutation_top10": perm_df.head(10).to_dict(orient="records"),
    }


def create_plots(
    df: pd.DataFrame,
    metrics: pd.DataFrame,
    best_confusion: list[list[int]],
    labels: list[str],
    importance: dict[str, Any],
    output: Path,
) -> None:
    _bar(df["best_solver"].value_counts(), output / "label_distribution.png", "Solver", "Count")
    _metric_bar(metrics, ["accuracy", "balanced_accuracy"], output / "accuracy_balanced_accuracy.png")
    _metric_bar(metrics, ["mean_regret"], output / "mean_regret.png")
    _metric_bar(metrics, ["mean_cost_ratio"], output / "mean_cost_ratio.png")
    _metric_bar(metrics, ["within_1_percent", "within_5_percent"], output / "within_thresholds.png")
    _confusion_plot(best_confusion, labels, output / "best_model_confusion_matrix.png")
    _importance_plot(importance["random_forest_top10"], output / "random_forest_feature_importance.png")
    _regret_plot(metrics, output / "method_regret_summary.png")


def _bar(series: pd.Series, path: Path, xlabel: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    series.plot(kind="bar", ax=ax)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _metric_bar(metrics: pd.DataFrame, columns: list[str], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    metrics.set_index("method")[columns].plot(kind="bar", ax=ax)
    ax.set_ylabel("Value")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _confusion_plot(matrix: list[list[int]], labels: list[str], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels=labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels=labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            ax.text(j, i, str(value), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _importance_plot(records: list[dict[str, Any]], path: Path) -> None:
    frame = pd.DataFrame(records).sort_values("importance")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(frame["feature"], frame["importance"])
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _regret_plot(metrics: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    metrics.set_index("method")[["median_regret", "p90_regret", "p95_regret"]].plot(kind="bar", ax=ax)
    ax.set_ylabel("Regret")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _best_ml_model(metrics: pd.DataFrame) -> str:
    ml = metrics[~metrics["method"].isin(["SBS", "VBS"])]
    return str(ml.sort_values(["mean_regret", "balanced_accuracy"], ascending=[True, False]).iloc[0]["method"])


def _model_params(model: Any) -> dict[str, Any]:
    params = model.get_params()
    cleaned = {}
    for key, value in params.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            cleaned[key] = value
    return cleaned


def _dominant_label_share(df: pd.DataFrame) -> float:
    return float(df["best_solver"].value_counts(normalize=True).max())


def _assert_finite(values: dict[str, Any]) -> None:
    bad = [key for key, value in values.items() if isinstance(value, float) and not math.isfinite(value)]
    if bad:
        raise ValueError(f"non-finite metrics: {bad}")


def _summary_markdown(summary: dict[str, Any], metrics: pd.DataFrame, grouped: dict[str, Any]) -> str:
    lines = [
        "# Final ML Experiment Summary",
        "",
        f"Rows: {summary['n_rows']}; train: {summary['train_rows']}; test: {summary['test_rows']}.",
        f"SBS: `{summary['sbs_solver']}`.",
        f"Best ML model by mean regret: `{summary['best_ml_model']}`.",
        "",
        "## Label Distribution",
    ]
    for label, count in summary["label_counts"].items():
        lines.append(f"- `{label}`: {count} ({summary['label_percentages'][label]:.1%})")
    lines.append("")
    lines.append("## Model Metrics")
    lines.append("```text")
    lines.append(metrics.to_string(index=False))
    lines.append("```")
    lines.append("")
    lines.append("## Top Random Forest Features")
    for record in summary["feature_importance"]["random_forest_top10"]:
        lines.append(f"- `{record['feature']}`: {record['importance']:.4f}")
    return "\n".join(lines)
