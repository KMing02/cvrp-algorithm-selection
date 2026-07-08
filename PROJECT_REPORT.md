# CVRP Algorithm Selection Project Report

This project is a student-scale reproduction of a machine-learning-based algorithm-selection pipeline for symmetric Euclidean Capacitated Vehicle Routing Problems (CVRP). It deliberately uses existing classical heuristics from VeRyPy instead of reimplementing standard CVRP algorithms.

## Scope

The implemented scope is one-depot, homogeneous-capacity CVRP with heterogeneous positive customer demands. Routes start and end at the depot. The project does not include VRPTW, pickup and delivery, heterogeneous fleets, exact solvers, reinforcement learning, OR-Tools as a production dependency, or a custom HGS implementation.

## Reproducibility And Distance Convention

VeRyPy is pinned to the tested Git commit:

```text
git+https://github.com/yorak/VeRyPy.git@8698f910ffcfb4bc8743aedbf203d6de72fbe006
```

The final experiment uses `cvrplib_euc_2d`, the CVRPLIB/TSPLIB rounded Euclidean convention implemented as `floor(distance + 0.5)`. Earlier floating Euclidean support remains available as `euclidean_float`, but final costs and labels are not compared against floating-point CVRPLIB values.

## Internal Representation

Instances use `CVRPInstance` with a depot index, coordinates, demands, vehicle capacity, and metadata. Solutions use:

```python
list[list[int]]
```

Each inner list contains customer indices only. The depot is never stored inside a route; route cost implicitly includes `depot -> first customer -> ... -> last customer -> depot`.

## Final Solver Portfolio

The final machine-learning selector uses five VeRyPy-based solver configurations:

- `CW64-PS/minimize-distance+2opt1`
- `MJ76-insertion/all-strain`
- `WH72-sweep/both-directions`
- `CMT79-2phase/default`
- `Be83-RFCS/default`

`Gaskell-PS/both-savings` remains implemented and was evaluated during the portfolio audit, but it was excluded from the main ML selector because it won only 3 of 240 development instances, leaving too few samples for a learnable class.

## Dataset

The final synthetic dataset contains 1260 instances from a balanced factorial-style design:

- 5 spatial families: `uniform`, `clustered`, `two_clusters`, `radial`, `mixed`.
- 3 depot positions: `center`, `corner`, `random`.
- 4 demand regimes: `low_variance`, `high_variance`, `high_pressure`, `low_pressure`.
- 3 customer counts: 20, 50, 100.
- 7 seeds per configuration: 0-6.

The train/test split is fixed and stratified by the recomputed five-solver label: 1008 training rows and 252 test rows.

## Final Label Distribution

- `Be83-RFCS/default`: 323 (25.6%)
- `CMT79-2phase/default`: 119 (9.4%)
- `CW64-PS/minimize-distance+2opt1`: 314 (24.9%)
- `MJ76-insertion/all-strain`: 266 (21.1%)
- `WH72-sweep/both-directions`: 238 (18.9%)

The largest class is below the earlier 70-80% dominance warning threshold, so the portfolio has enough complementarity to make selector learning meaningful.

## Solver Failures

- `Be83-RFCS/default`: 0
- `CMT79-2phase/default`: 0
- `CW64-PS/minimize-distance+2opt1`: 0
- `MJ76-insertion/all-strain`: 0
- `WH72-sweep/both-directions`: 1

The single Wren-Holliday Sweep failure was handled as a solver failure; labels were computed from the remaining feasible solvers only.

## Model Evaluation

The primary objective is route cost. Runtime is reported separately as a secondary metric.

| method | accuracy | balanced_accuracy | macro_f1 | mean_regret | median_regret | p95_regret | mean_cost_ratio | within_1_percent | within_5_percent | mean_selected_solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VBS | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3590 |
| RandomForest | 0.4008 | 0.3785 | 0.3784 | 0.0124 | 0.0027 | 0.0465 | 1.0124 | 0.6310 | 0.9563 | 0.4625 |
| KNN | 0.3849 | 0.3588 | 0.3535 | 0.0132 | 0.0032 | 0.0531 | 1.0132 | 0.6071 | 0.9444 | 0.3618 |
| GradientBoosting | 0.3452 | 0.3058 | 0.2978 | 0.0137 | 0.0057 | 0.0490 | 1.0137 | 0.5873 | 0.9524 | 0.3942 |
| SBS | 0.2103 | 0.2000 | 0.0695 | 0.0167 | 0.0119 | 0.0522 | 1.0167 | 0.4524 | 0.9444 | 0.2139 |
| DecisionTree | 0.3214 | 0.2876 | 0.2855 | 0.0175 | 0.0071 | 0.0599 | 1.0175 | 0.5516 | 0.9246 | 0.2917 |
| Dummy-most-frequent | 0.2579 | 0.2000 | 0.0820 | 0.0216 | 0.0099 | 0.0839 | 1.0216 | 0.5000 | 0.8690 | 1.2397 |
| Dummy-stratified | 0.2341 | 0.2043 | 0.2060 | 0.0264 | 0.0144 | 0.0905 | 1.0264 | 0.4484 | 0.8373 | 0.4136 |

Random Forest is the best verified ML model by mean regret. It improves over SBS in routing-quality metrics: mean regret 0.0124 versus 0.0167, and within-1% rate 63.1% versus 45.2%. Its classification accuracy is 40.1%; this is modest but above the SBS-classification baseline and translates into lower routing regret.

## Important Features

Top Random Forest impurity importances:

- `capacity_pressure`: 0.0439
- `demand_std`: 0.0419
- `depot_distance_std`: 0.0408
- `depot_centrality_normalized`: 0.0402
- `total_demand`: 0.0396
- `depot_to_centroid_distance`: 0.0367
- `demand_mean`: 0.0358
- `depot_distance_mean`: 0.0342
- `demand_cv`: 0.0326
- `depot_distance_max`: 0.0318

Top held-out permutation importances:

- `depot_centrality_normalized`: 0.0135
- `ring_3_ratio`: 0.0119
- `depot_distance_std`: 0.0111
- `ring_4_ratio`: 0.0103
- `std_pairwise_customer_distance`: 0.0095
- `depot_distance_min`: 0.0087
- `total_demand`: 0.0063
- `capacity_pressure`: 0.0048
- `mean_nearest_neighbor_distance`: 0.0048
- `demand_min`: 0.0040

These should be interpreted as predictive associations, not causal claims.

## Grouped Performance

By customer count:

|  |
|  |
|  |
|  |
|  |
|  |

By demand regime:

|  |
|  |
|  |
|  |
|  |
|  |

By depot position:

|  |
|  |
|  |
|  |
|  |
|  |

The best model performs best on 100-customer instances and worst on high-pressure demand regimes. This suggests that capacity pressure is a harder regime and that the selector generalises better when there is more geometric structure to measure.

## Integrity Checks

The pipeline includes checks that final labels equal the minimum feasible solver cost among the five-solver portfolio, train/test instance IDs are disjoint, VBS regret is zero, VBS cost ratio is one, prohibited solver/result/label columns do not enter the model feature matrix, and metrics are finite.

## Limitations

- The dataset is synthetic, not a broad CVRPLIB benchmark.
- Labels are generated by a small classical-heuristic portfolio, not by exact optima.
- Random Forest improves regret over SBS, but the margin is moderate.
- Runtime is not part of the label objective, so faster-but-costlier choices are not directly rewarded.
- VeRyPy algorithms occasionally require timeout handling on generated instances.

## Conclusion

The results are strong enough for a project presentation: the solver portfolio is complementary, the features are pre-solution only, leakage checks are explicit, the best ML selector beats SBS on mean regret and within-1% quality, and all final artifacts are saved for reproducible reporting. The next phase should be presentation material, not additional model training.
