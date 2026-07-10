# Learning which VRP solver works best

This repository contains a computational logistics project on machine-learning-based algorithm selection for the Capacitated Vehicle Routing Problem (CVRP). Given measurable features of an instance (size, demand variance, depot centrality, ...), a classifier predicts which heuristic configuration will yield the best solution within a fixed time budget. The project introduces the problem by solving benchmark and self-created instances both exactly (gurobipy) and heuristically, uses classical CVRP heuristics from VeRyPy as the solver portfolio, validates every solution independently, generates synthetic CVRP instances, extracts pre-solution features, and evaluates ML selectors against SBS and VBS baselines.

The methodology follows Asín-Achá et al. (2024), "Selecting fast algorithms for the capacitated vehicle routing problem with machine learning techniques", *Networks* 84(4):465-480, at student scale.

The main ML experiment is complete and frozen for presentation/reporting. Do not treat the saved result files as scratch outputs.

## Scope

- Symmetric Euclidean CVRP only.
- One depot, homogeneous vehicle capacity, heterogeneous positive customer demands, unlimited fleet.
- Routes start and end at the depot.
- Exact solving with gurobipy is used only for the problem-introduction baseline on small instances; labels for the ML selector come from the heuristic portfolio.
- No VRPTW, pickup and delivery, heterogeneous fleets, reinforcement learning, OR-Tools production dependency, or custom HGS implementation.

## Setup

This project uses `uv` for dependency management.

```bash
uv sync
```

VeRyPy is installed from the tested Git commit:

```text
git+https://github.com/yorak/VeRyPy.git@8698f910ffcfb4bc8743aedbf203d6de72fbe006
```

The PyPI package named `verypy==1.0.5` is unrelated file-hashing code; this project uses the CVRP heuristic library from GitHub.

`gurobipy` installs with a free size-limited license (at most 2000 variables and 2000 constraints), which is sufficient for every exact solve in this project. A full license is only needed to solve larger instances exactly.

## Fixed Time Budget

Every solver in the final ML portfolio runs under the same fixed wall-clock budget:

```python
from cvrp_algorithm_selection.solvers import TIME_BUDGET_SECONDS  # 20.0 seconds
```

A solver that does not return a feasible solution within the budget is recorded as a failure, so the label `best_solver` means "best solution within the fixed time budget". In the frozen final experiment every feasible run completed within the budget (maximum observed runtime 16.98 s), and the single Wren-Holliday timeout was verified to still exceed 20 s when re-run, so the frozen labels coincide exactly with best-within-20s labels. On platforms without `SIGALRM` (Windows) the budget is enforced by a watchdog thread; the abandoned worker cannot be killed and may keep consuming CPU until the underlying VeRyPy call returns.

## Route Representation

The common solution representation is:

```python
list[list[int]]
```

Each inner list is one vehicle route containing customer indices only. The depot must not appear inside stored routes. Cost calculation implicitly evaluates:

```text
depot -> first customer -> ... -> last customer -> depot
```

## Distance Conventions

Instances carry `metadata["distance_convention"]`.

- `euclidean_float`: direct floating-point Euclidean distances.
- `cvrplib_euc_2d`: CVRPLIB/TSPLIB-style rounded Euclidean distance, implemented as `floor(distance + 0.5)`.

The final experiment uses `cvrplib_euc_2d`. Solvers (exact and heuristic), validation, feature extraction, and independent cost recomputation use the same convention stored on the instance. Do not compare floating Euclidean costs against CVRPLIB integer best-known values.

## Exact Baseline (gurobipy)

`src/cvrp_algorithm_selection/exact.py` solves CVRP as a MIP with gurobipy: a two-index arc formulation with load-propagation (MTZ-style) constraints that eliminate subtours and enforce capacity simultaneously. `src/cvrp_algorithm_selection/exact_baseline.py` runs the problem-introduction experiment:

- The tiny manual instance and two self-created synthetic instances (20 customers) are solved to proven optimality with gurobipy and with all five portfolio heuristics; each heuristic's optimality gap is reported.
- The CVRPLIB benchmark `E-n51-k5` is solved heuristically and compared against the proven optimum 521; the exact model is attempted and the size-limited-license failure is recorded honestly; the trained Random Forest selector predicts the best portfolio solver for the benchmark.

Artifacts are stored in `reports/exact_baseline/`. Reproduce with:

```bash
uv run python -m cvrp_algorithm_selection.exact_baseline
```

## Final Solver Portfolio

The final ML selector uses five solver configurations, all under the 20 s budget:

- `CW64-PS/minimize-distance+2opt1`
- `MJ76-insertion/all-strain`
- `WH72-sweep/both-directions`
- `CMT79-2phase/default`
- `Be83-RFCS/default`

`Gaskell-PS/both-savings` remains implemented and was evaluated during the portfolio audit, but it is excluded from the main ML portfolio because it won only 3 of 240 development instances.

## Synthetic Dataset

The final dataset contains 1260 synthetic instances:

- 5 spatial families: `uniform`, `clustered`, `two_clusters`, `radial`, `mixed`.
- 3 depot positions: `center`, `corner`, `random`.
- 4 demand regimes: `low_variance`, `high_variance`, `high_pressure`, `low_pressure`.
- 3 customer counts: 20, 50, 100.
- 7 seeds per configuration: 0-6.
- Distance convention: `cvrplib_euc_2d`.

Generation configuration and manifests are saved in `reports/final_ml_experiment/`.

## Final Results

Final label distribution:

- `Be83-RFCS/default`: 323 (25.6%)
- `CMT79-2phase/default`: 119 (9.4%)
- `CW64-PS/minimize-distance+2opt1`: 314 (24.9%)
- `MJ76-insertion/all-strain`: 266 (21.1%)
- `WH72-sweep/both-directions`: 238 (18.9%)

Selected SBS from training data only: `MJ76-insertion/all-strain`.

Best ML model: `RandomForest`.

| Method | Accuracy | Balanced accuracy | Mean regret | Within 1% of VBS | Within 5% of VBS | m&#770; (paper metric) |
|---|---:|---:|---:|---:|---:|---:|
| VBS | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 0.000 |
| Random Forest | 0.401 | 0.379 | 0.012 | 0.631 | 0.956 | 0.741 |
| SBS | 0.210 | 0.200 | 0.017 | 0.452 | 0.944 | 1.000 |

m&#770; is the normalized selector metric from Asín-Achá et al. (2024): 0 means VBS-quality selection, 1 means no better than SBS. The Random Forest selector closes about 26% of the SBS-to-VBS gap. If the predicted solver fails on an instance, the meta-solver falls back to the SBS (this fallback never triggers on the frozen test set).

## Main Artifacts

- `PROJECT_REPORT.md`: final project report ("Learning which VRP solver works best").
- `cvrp_algorithm_selection.ipynb`: compact fast-mode notebook that loads saved outputs.
- `reports/final_ml_experiment/`: frozen final experiment tables, metrics, plots, and summaries.
- `reports/exact_baseline/`: gurobipy exact-vs-heuristic baseline and benchmark selector demo.
- `reports/portfolio_audit/`: solver portfolio audit, including Gaskell.
- `reports/presentation_handoff/`: slide-oriented numbers, outline, and Q&A notes.

## Reproduction Commands

Run tests:

```bash
uv run pytest
```

Re-run the exact baseline and benchmark demo:

```bash
uv run python -m cvrp_algorithm_selection.exact_baseline
```

Run the compact notebook code cells in fast mode without requiring Jupyter:

```bash
uv run python -c "import json; from pathlib import Path; ns={}; nb=json.loads(Path('cvrp_algorithm_selection.ipynb').read_text()); [exec(''.join(c['source']), ns) for c in nb['cells'] if c['cell_type']=='code']; print('notebook fast-mode code cells executed')"
```

Validate saved final labels and metric integrity:

```bash
uv run python -c "import math, pandas as pd; from pathlib import Path; from cvrp_algorithm_selection.ml_experiment import final_solver_prefixes, validate_label_minima; base=Path('reports/final_ml_experiment'); df=pd.read_csv(base/'experiment_table.csv'); validate_label_minima(df, final_solver_prefixes()); metrics=pd.read_csv(base/'model_metrics.csv'); assert len(df)==1260; assert metrics.select_dtypes(include='number').map(math.isfinite).all().all(); vbs=metrics[metrics.method=='VBS'].iloc[0]; assert abs(vbs.mean_regret)<1e-12 and abs(vbs.mean_cost_ratio-1.0)<1e-12; print('integrity ok')"
```

Re-running the complete final solver experiment is intentionally not part of the fast reproduction path; it is substantially slower than loading the frozen outputs.

## Project Structure

- `src/cvrp_algorithm_selection/instance.py`: `CVRPInstance` representation.
- `src/cvrp_algorithm_selection/distances.py`: distance matrix conventions.
- `src/cvrp_algorithm_selection/costs.py`: independent route and solution costs.
- `src/cvrp_algorithm_selection/validation.py`: independent feasibility checks.
- `src/cvrp_algorithm_selection/solvers.py`: VeRyPy solver adapters and the fixed time budget.
- `src/cvrp_algorithm_selection/exact.py`: gurobipy MIP model (two-index + load constraints).
- `src/cvrp_algorithm_selection/exact_baseline.py`: exact-vs-heuristic experiment and benchmark selector demo.
- `src/cvrp_algorithm_selection/synthetic.py`: synthetic CVRP generator.
- `src/cvrp_algorithm_selection/features.py`: pre-solution feature extraction.
- `src/cvrp_algorithm_selection/experiments.py`: batch solver experiment runner.
- `src/cvrp_algorithm_selection/ml_experiment.py`: final ML evaluation and integrity helpers.
- `tests/`: focused unit and integration tests.

## Methodological Limitations

- The ML selector is trained and tested on synthetic instances; only a single CVRPLIB benchmark demo probes out-of-distribution behavior.
- The VBS is an oracle over the selected heuristic portfolio, not an exact optimum.
- Runtime is reported separately from the route-cost objective; the fixed time budget bounds it but does not reward faster solvers.
- Feature importances are descriptive and predictive, not causal.
