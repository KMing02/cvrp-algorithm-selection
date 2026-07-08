# CVRP Algorithm Selection Foundation

This repository currently contains the first project layer for a simplified
machine-learning-based CVRP algorithm-selection pipeline. It intentionally stops
at instance loading, classical heuristic adapters, independent validation, and
reproducible benchmarking.

## Scope

- Symmetric Euclidean CVRP only.
- One depot, homogeneous vehicle capacity, heterogeneous customer demands.
- Routes start and end at the depot.
- No machine learning, dataset generation, feature extraction, plots, notebooks,
  exact solvers, OR-Tools, or custom HGS implementation in this phase.

## Route Representation

The common solution representation is:

```python
list[list[int]]
```

Each inner list is one vehicle route containing customer indices only. The depot
must not appear inside stored routes. Cost calculation implicitly evaluates:

```text
depot -> first customer -> ... -> last customer -> depot
```

Empty routes are accepted by the validator with a warning and zero route cost.

## Distance Assumptions

All project-level costs use floating-point Euclidean distances computed from the
instance coordinates. The included CVRPLIB-style fixture declares `EUC_2D`,
whose TSPLIB convention is usually rounded integer distance. We load its
coordinates with VeRyPy's parser, but intentionally recompute floating Euclidean
distances for solver input and independent cost checks.

## Solver Portfolio

The selected foundation uses upstream VeRyPy pinned to the tested commit:

```text
git+https://github.com/yorak/VeRyPy.git@8698f910ffcfb4bc8743aedbf203d6de72fbe006
```

The PyPI package name is misleading: `verypy==1.0.5` is unrelated file hashing
code. The CVRP heuristic library installed from GitHub identifies as
`verypy==0.6.0`.

Current deterministic configurations:

- `CW64-PS/minimize-distance`: parallel Clarke-Wright savings.
- `basic-sweep/both-directions/best-start`: basic Sweep over both directions and
  all starts, selecting best distance.
- `SNN/farthest-seed/both-route-ends`: sequential nearest neighbor, farthest
  seed, insertion at either route end.

Each adapter returns a `SolverResult` with normalized routes, independent total
distance, runtime, feasibility, raw VeRyPy output, VeRyPy-reported cost, and any
cost discrepancy.

Rounded `E-n51-k5` solver costs under `cvrplib_euc_2d`:

- `CW64-PS/minimize-distance`: 580
- `basic-sweep/both-directions/best-start`: 806
- `SNN/farthest-seed/both-route-ends`: 691

## Distance Conventions

Instances carry `metadata["distance_convention"]`.

- `euclidean_float`: direct floating-point Euclidean distances.
- `cvrplib_euc_2d`: CVRPLIB/TSPLIB-style rounded Euclidean distance,
  implemented as `floor(distance + 0.5)`.

Solvers, validation, feature extraction, and independent cost recomputation all
use the same convention stored on the instance.

Do not compare floating Euclidean costs against CVRPLIB integer best-known
values.

## Synthetic Generator

Generation uses `numpy.random.Generator` with explicit seeds. Supported customer
counts are 20, 50, and 100.

Spatial families:

- `uniform`: customers sampled uniformly from `[0, 100] x [0, 100]`.
- `clustered`: 2-5 centres sampled from `[15, 85] x [15, 85]`; customers are
  Gaussian around assigned centres with standard deviation 7.5, clipped to the
  square.
- `two_clusters`: two separated centres near `(25, 25)` and `(75, 75)` with
  small centre noise; customers are Gaussian around one of the two centres.
- `radial`: customers sampled by random angle around `(50, 50)` and triangular
  radius with low 8, mode 45, high 70.
- `mixed`: about 60% clustered customers and 40% uniform customers.

Depot positions:

- `center`: `(50, 50)`.
- `corner`: `(0, 0)`.
- `random`: uniform in `[10, 90] x [10, 90]`.

Demand regimes:

- `low_variance`: rounded clipped normal demand, mean 8, std 1.5, clipped to
  4-12; capacity targets roughly `ceil(n / 8)` routes with 1.25 slack.
- `high_variance`: 30% large integer demands 18-35, otherwise 2-10; capacity
  targets roughly `ceil(n / 7)` routes with 1.15 slack.
- `high_pressure`: integer demands 8-23; capacity targets roughly `ceil(n / 5)`
  routes with 1.03 slack.
- `low_pressure`: integer demands 4-15; capacity targets roughly `ceil(n / 12)`
  routes with 1.45 slack.

Capacity is always at least the maximum customer demand and less than total
demand, so generated instances are valid but not one-route trivial.

## Development Experiment

The current development dataset configuration is:

- 5 spatial families.
- 3 depot positions.
- 4 demand regimes.
- customer counts 20 and 50.
- seeds 0 and 1.
- distance convention `cvrplib_euc_2d`.

This produces 240 instances. Outputs are written to
`reports/development_experiment/`:

- `generation_config.json`
- `experiment_table.csv`
- `summary.json`

Current diagnostic summary:

- valid rows: 240 / 240
- solver failures: 0 for all three solvers
- label counts: Clarke-Wright 230, Sweep 4, nearest neighbour 6
- label percentages: Clarke-Wright 95.83%, Sweep 1.67%, nearest neighbour 2.50%
- elapsed solver experiment time: about 6.93 seconds

This is a strong sign that the current algorithm portfolio lacks
complementarity: Clarke-Wright dominates far above the 70-80% warning threshold.
No feature contained NaN, infinity, or a constant value in this development run.

## Portfolio Audit

The portfolio-design audit is saved in `reports/portfolio_audit/`. The current
recommended solver portfolio is:

- `CW64-PS/minimize-distance+2opt1`
- `Gaskell-PS/both-savings`
- `MJ76-insertion/all-strain`
- `WH72-sweep/both-directions`
- `CMT79-2phase/default`
- `Be83-RFCS/default`

On the 240-instance development dataset, this subset gives an expected label
distribution of RFCS 59, Wren-Holliday sweep 55, Clarke-Wright + 2-opt 49,
Mole-Jameson insertion 47, CMT two-phase 27, and Gaskell savings 3. The largest
single share is 24.6%, so the portfolio is substantially more complementary
than the original three-solver set.

## Final ML Experiment

The final selector uses five solvers:

- `CW64-PS/minimize-distance+2opt1`
- `MJ76-insertion/all-strain`
- `WH72-sweep/both-directions`
- `CMT79-2phase/default`
- `Be83-RFCS/default`

`Gaskell-PS/both-savings` remains implemented and was evaluated in the audit,
but it is excluded from the main ML portfolio because it won only 3 of 240
development instances, giving too few samples for a learnable class.

The final synthetic dataset has 1,260 instances: 5 spatial families, 3 depot
positions, 4 demand regimes, 3 customer counts, and seeds 0-6 with
`cvrplib_euc_2d`.

Final label distribution:

- `Be83-RFCS/default`: 323
- `CW64-PS/minimize-distance+2opt1`: 314
- `MJ76-insertion/all-strain`: 266
- `WH72-sweep/both-directions`: 238
- `CMT79-2phase/default`: 119

Best ML model in the verified run: Random Forest. On the held-out test set it
has mean regret 1.24% versus 1.67% for SBS. Full artifacts are in
`reports/final_ml_experiment/`.

## Test Data

- `tiny-manual`: 6-customer manually defined instance, capacity 7, requiring at
  least two routes.
- `data/cvrplib/E-n51-k5.vrp`: small public CVRPLIB/TSPLIB-style fixture loaded
  through VeRyPy's parser.

## Running Tests

```bash
uv run pytest
```
