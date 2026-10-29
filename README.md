# CVRP Algorithm Selection

This repository contains a student-scale computational logistics project on machine-learning-based algorithm selection for the Capacitated Vehicle Routing Problem (CVRP). The project uses existing classical CVRP heuristics from VeRyPy, validates every solution independently, generates synthetic CVRP instances, extracts pre-solution features, and evaluates ML selectors against SBS and VBS baselines.

The repository contains the finalized experiment artifacts used for presentation and reporting.

## Scope

- Symmetric Euclidean CVRP only.
- One depot, homogeneous vehicle capacity, heterogeneous positive customer demands.
- Routes start and end at the depot.
- No VRPTW, pickup and delivery, heterogeneous fleets, exact solvers, Gurobi, reinforcement learning, OR-Tools production dependency, or custom HGS implementation.

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

The final experiment uses `cvrplib_euc_2d`. Solvers, validation, feature extraction, and independent cost recomputation use the same convention stored on the instance. Do not compare floating Euclidean costs against CVRPLIB integer best-known values.

## Final Solver Portfolio

The final ML selector uses five solver configurations:

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

| Method | Accuracy | Balanced accuracy | Mean regret | Within 1% of VBS | Within 5% of VBS |
|---|---:|---:|---:|---:|---:|
| Random Forest | 0.401 | 0.379 | 0.012 | 0.631 | 0.956 |
| SBS | 0.210 | 0.200 | 0.017 | 0.452 | 0.944 |

Random Forest improves mean regret over SBS, but runtime is reported separately and is not part of the main label objective.

## Main Artifacts

- `PROJECT_REPORT.md`: concise final project report.
- `cvrp_algorithm_selection.ipynb`: compact fast-mode notebook that loads saved outputs.
- `reports/final_ml_experiment/`: frozen final experiment tables, metrics, plots, and summaries.
- `reports/portfolio_audit/`: solver portfolio audit, including Gaskell.
- `reports/presentation_handoff/`: slide-oriented numbers, outline, and Q&A notes.

## Reproduction Commands

Run tests:

```bash
uv run pytest
```

Run the compact notebook code cells in fast mode without requiring Jupyter:

```bash
uv run python -c "import json; from pathlib import Path; ns={}; nb=json.loads(Path('cvrp_algorithm_selection.ipynb').read_text()); [exec(''.join(c['source']), ns) for c in nb['cells'] if c['cell_type']=='code']; print('notebook fast-mode code cells executed')"
```

Validate saved final labels and metric integrity:

```bash
uv run python -c "import math, pandas as pd; from pathlib import Path; from cvrp_algorithm_selection.ml_experiment import final_solver_prefixes, validate_label_minima; base=Path('reports/final_ml_experiment'); df=pd.read_csv(base/'experiment_table.csv'); validate_label_minima(df, final_solver_prefixes()); metrics=pd.read_csv(base/'model_metrics.csv'); assert len(df)==1260; assert metrics.select_dtypes(include='number').map(math.isfinite).all().all(); vbs=metrics[metrics.method=='VBS'].iloc[0]; assert abs(vbs.mean_regret)<1e-12 and abs(vbs.mean_cost_ratio-1.0)<1e-12; print('integrity ok')"
```

For a fast reproducibility check, the notebook loads the saved experiment outputs. Re-running the complete solver experiment is substantially slower.

## Project Structure

- `src/cvrp_algorithm_selection/instance.py`: `CVRPInstance` representation.
- `src/cvrp_algorithm_selection/distances.py`: distance matrix conventions.
- `src/cvrp_algorithm_selection/costs.py`: independent route and solution costs.
- `src/cvrp_algorithm_selection/validation.py`: independent feasibility checks.
- `src/cvrp_algorithm_selection/solvers.py`: VeRyPy solver adapters.
- `src/cvrp_algorithm_selection/synthetic.py`: synthetic CVRP generator.
- `src/cvrp_algorithm_selection/features.py`: pre-solution feature extraction.
- `src/cvrp_algorithm_selection/experiments.py`: batch solver experiment runner.
- `src/cvrp_algorithm_selection/ml_experiment.py`: final ML evaluation and integrity helpers.
- `tests/`: focused unit and integration tests.

## Methodological Limitations

- Results are based on synthetic instances, not a broad public benchmark suite.
- The VBS is an oracle over the selected heuristic portfolio, not an exact optimum.
- Runtime is reported separately from the route-cost objective.
- Feature importances are descriptive and predictive, not causal.
