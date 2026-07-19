"""Hyperparameter grid search supplement for the frozen ML experiment.

Asín-Achá et al. (2024) adjust their models' parameters "by performing a grid
search, using k-fold cross validation, with k = 5". The frozen headline
experiment in this project used fixed, hand-chosen hyperparameters instead.
This module closes that methodological gap without touching the frozen
artifacts: it runs the paper-style grid search with 5-fold cross-validation on
the frozen *training* split only, then evaluates the tuned models once on the
frozen test split. This shows whether the fixed hyperparameters left
performance on the table.

Outputs (``reports/hyperparameter_tuning/``):

- ``grid_search_results.json``: best parameters and CV accuracy per model.
- ``tuned_test_metrics.csv``: test-split metrics of the tuned models next to
  the frozen fixed-parameter results.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from cvrp_algorithm_selection.ml_experiment import (
    RANDOM_STATE,
    choose_sbs,
    evaluate_predictions,
    final_solver_prefixes,
    train_frozen_random_forest,
)


REPORT_DIR = Path("reports/hyperparameter_tuning")


def model_grids() -> dict[str, tuple[Any, dict[str, list[Any]]]]:
    return {
        "RandomForest": (
            RandomForestClassifier(class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1),
            {
                "n_estimators": [100, 250, 400],
                "min_samples_leaf": [1, 2, 5],
                "max_features": ["sqrt", None],
            },
        ),
        "KNN": (
            Pipeline([("scaler", StandardScaler()), ("model", KNeighborsClassifier())]),
            {
                "model__n_neighbors": [3, 5, 7, 11, 15],
                "model__weights": ["uniform", "distance"],
            },
        ),
        "DecisionTree": (
            DecisionTreeClassifier(random_state=RANDOM_STATE),
            {
                "max_depth": [4, 8, 12, None],
                "min_samples_leaf": [1, 5, 10],
            },
        ),
        "GradientBoosting": (
            GradientBoostingClassifier(random_state=RANDOM_STATE),
            {
                "n_estimators": [100, 150],
                "learning_rate": [0.05, 0.1],
                "max_depth": [2, 3],
            },
        ),
    }


def run_grid_search(output_dir: str | Path = REPORT_DIR) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    _, features, train, test = train_frozen_random_forest()
    prefixes = final_solver_prefixes()
    sbs_solver = choose_sbs(train, prefixes)
    X_train, y_train = train[features], train["best_solver"]
    X_test, y_test = test[features], test["best_solver"]
    labels = sorted(pd.concat([y_train, y_test]).unique())
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    grid_results: dict[str, Any] = {}
    test_rows: list[dict[str, Any]] = []
    for name, (estimator, grid) in model_grids().items():
        started = time.perf_counter()
        search = GridSearchCV(estimator, grid, cv=cv, scoring="accuracy", n_jobs=-1)
        search.fit(X_train, y_train)
        search_time = time.perf_counter() - started

        started = time.perf_counter()
        predicted = search.best_estimator_.predict(X_test)
        predict_time = time.perf_counter() - started
        metrics = evaluate_predictions(
            f"{name}-tuned",
            np.asarray(predicted),
            y_test.to_numpy(),
            test,
            prefixes,
            train_time=search_time,
            predict_time=predict_time,
            labels=labels,
            fallback_solver=sbs_solver,
        )
        test_rows.append(metrics["summary"])
        grid_results[name] = {
            "best_params": search.best_params_,
            "cv_accuracy": float(search.best_score_),
            "n_candidates": int(len(search.cv_results_["params"])),
            "search_time_seconds": float(search_time),
        }
        print(f"tuned {name}: cv_accuracy={search.best_score_:.4f} params={search.best_params_}", flush=True)

    (output / "grid_search_results.json").write_text(json.dumps(grid_results, indent=2, sort_keys=True))
    tuned = pd.DataFrame(test_rows).sort_values("mean_regret")
    tuned.to_csv(output / "tuned_test_metrics.csv", index=False)
    summary = {
        "grid_search": grid_results,
        "tuned_test_metrics": test_rows,
        "note": (
            "5-fold stratified grid search on the frozen training split only; "
            "single evaluation on the frozen test split. The frozen headline "
            "experiment (reports/final_ml_experiment) keeps its fixed parameters."
        ),
    }
    (output / "tuning_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    summary = run_grid_search()
    print(json.dumps(summary["grid_search"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
