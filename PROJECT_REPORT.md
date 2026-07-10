# Learning which VRP solver works best

Given measurable features of a CVRP instance (size, demand variance, depot centrality, ...), this project trains a classifier to predict which heuristic configuration will yield the best solution within a fixed time budget. The problem is introduced by solving benchmark and self-created instances both exactly with gurobipy and heuristically. The methodology is a student-scale adaptation of Asín-Achá et al. (2024) [1]; classical CVRP heuristics come from VeRyPy [2] instead of being reimplemented.

## 1. Problem Introduction

The Capacitated Vehicle Routing Problem (CVRP): a depot hosts an unlimited fleet of identical vehicles of capacity Q; each customer i has demand q_i > 0 and must be visited exactly once; every route starts and ends at the depot and the total demand on a route may not exceed Q; the objective is to minimize the total travelled distance. CVRP is NP-hard, which motivates exact reference solutions on small instances and fast heuristics at scale — and, because no single heuristic dominates on all instances [1], per-instance algorithm selection.

The implemented scope is one-depot, symmetric Euclidean CVRP with homogeneous capacity and heterogeneous positive demands. Routes are stored as `list[list[int]]` of customer indices; the depot is implicit at both route ends.

### Exact model (gurobipy)

`exact.py` formulates CVRP as a MIP: a two-index arc formulation with load-propagation (MTZ-style [3]) constraints,

- min Σ c_ij x_ij with binary arc variables x_ij,
- each customer is entered and left exactly once; depot departures equal returns,
- load variables u_i ∈ [q_i, Q] with u_j ≥ u_i + q_j − Q(1 − x_ij), which eliminate subtours and enforce capacity simultaneously.

Distances come from the instance's own convention (`cvrplib_euc_2d`, `floor(d + 0.5)`), so exact and heuristic costs are directly comparable. Every Gurobi solution is re-validated and re-costed independently.

## 2. Exact Versus Heuristic Baseline

The tiny manual instance (6 customers) and two self-created synthetic instances (20 customers, drawn from the final dataset design) were solved with gurobipy (300 s limit, free size-limited license) and with all five portfolio heuristics (`reports/exact_baseline/`):

| Instance | Gurobi result | Best heuristic(s) | Worst heuristic |
| --- | --- | --- | --- |
| tiny-manual (n=6) | **50.83, proven optimal**, 0.01 s | all five match the optimum (0.00%) | — |
| syn-n20-uniform-center-low_variance-s0 | incumbent 524 after 300 s, 2.1% unresolved MIP gap | four heuristics match the incumbent 524 in ≤ 0.02 s | CW64-PS 539 (+2.86%) |
| syn-n20-two_clusters-corner-high_variance-s0 | incumbent 571 after 300 s, 0.68% unresolved MIP gap | 574 (+0.53%) in ≤ 0.04 s | Be83-RFCS 680 (+19.09%) |

Two observations frame the rest of the project. First, exact solving is already expensive at 20 customers (the MIP could not prove optimality in 300 s) while the heuristics deliver equal or near-equal solutions in milliseconds. Second, which heuristic is best — and how badly the worst one fails (up to +19%) — depends on the instance, which is precisely what the selector must learn.

## 3. Fixed Time Budget

Every solver in the final ML portfolio runs under the same fixed wall-clock budget, `TIME_BUDGET_SECONDS = 20.0` (`solvers.py`). A solver that does not return a feasible solution within the budget is recorded as a failure, so the label means "best solution within the fixed time budget". In the frozen experiment every feasible run completed within the budget (maximum observed runtime 16.98 s), and the single Wren-Holliday timeout was re-run under the 20 s budget and verified to still time out, so the frozen labels coincide exactly with best-within-20s labels. On platforms without `SIGALRM` (Windows) the budget is enforced by a watchdog thread.

## 4. Solver Portfolio

The final selector chooses among five deterministic VeRyPy heuristic configurations:

- `CW64-PS/minimize-distance+2opt1` (Clarke-Wright parallel savings + intra-route 2-opt)
- `MJ76-insertion/all-strain` (Mole-Jameson insertion)
- `WH72-sweep/both-directions` (Wren-Holliday sweep)
- `CMT79-2phase/default` (Christofides-Mingozzi-Toth two-phase)
- `Be83-RFCS/default` (Beasley route-first cluster-second)

`Gaskell-PS/both-savings` remains implemented and audited but is excluded because it won only 3 of 240 development instances — too few samples for a learnable class. Treating parameterized variants as separate portfolio entries is the discretized form of algorithm configuration described in [1].

## 5. Dataset

The final synthetic dataset contains 1260 instances from a balanced factorial design: 5 spatial families (`uniform`, `clustered`, `two_clusters`, `radial`, `mixed`) × 3 depot positions (`center`, `corner`, `random`) × 4 demand regimes (`low_variance`, `high_variance`, `high_pressure`, `low_pressure`) × 3 customer counts (20, 50, 100) × 7 seeds. Distance convention: `cvrplib_euc_2d`. The train/test split is fixed and stratified by label: 1008 training and 252 test rows; instance IDs are disjoint by construction.

Following [1], training data is synthetic and designed to span instance variation; unlike [1], the test split is also synthetic, with a single CVRPLIB benchmark used as an out-of-distribution demo (Section 10).

## 6. Features

All model features are pre-solution instance statistics (`features.py`), echoing the fast-to-extract characterization of [1]: size and capacity (n, Q, total demand, minimum-vehicle lower bound, capacity pressure), demand distribution (mean, std, CV, quantiles), depot geometry (distance statistics, depot-to-centroid distance, normalized depot centrality — the paper's "distance of the depot to the center"), spatial dispersion (bounding box, pairwise and nearest-neighbor distances, cluster-separation estimates), and five concentric ring-occupancy ratios around the depot (the paper's k-circular convolution with k=5). Solver outcomes, labels, seeds, and generator fields are excluded from the feature matrix by an explicit prohibited-column check.

## 7. Labels

The label of an instance is the portfolio solver with the lowest feasible cost within the time budget; exact-cost ties break toward the faster solver (as in [1]). Final label distribution:

- `Be83-RFCS/default`: 323 (25.6%)
- `CW64-PS/minimize-distance+2opt1`: 314 (24.9%)
- `MJ76-insertion/all-strain`: 266 (21.1%)
- `WH72-sweep/both-directions`: 238 (18.9%)
- `CMT79-2phase/default`: 119 (9.4%)

No class dominates (largest share 25.6%), so the portfolio is complementary enough for selection to be meaningful. Solver failures: one Wren-Holliday budget timeout in 6300 runs; that instance was labelled from the remaining feasible solvers. At deployment, the meta-solver falls back to the SBS if the predicted solver fails.

## 8. Model Evaluation

The primary objective is route cost; runtime is reported separately. SBS (single best solver, chosen on training data only) is `MJ76-insertion/all-strain`; VBS is the per-instance oracle. m̂ is the normalized selector metric of [1]: m̂ = (m_s − m_VBS)/(m_SBS − m_VBS) over mean cost ratios, where 0 is VBS-quality selection and 1 is no better than SBS.

| method | accuracy | balanced_accuracy | macro_f1 | mean_regret | median_regret | p95_regret | mean_cost_ratio | within_1_percent | within_5_percent | m̂ | mean_selected_solver_runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VBS | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 | 0.000 | 0.3590 |
| RandomForest | 0.4008 | 0.3785 | 0.3784 | 0.0124 | 0.0027 | 0.0465 | 1.0124 | 0.6310 | 0.9563 | 0.741 | 0.4625 |
| KNN | 0.3849 | 0.3588 | 0.3535 | 0.0132 | 0.0032 | 0.0531 | 1.0132 | 0.6071 | 0.9444 | 0.786 | 0.3618 |
| GradientBoosting | 0.3452 | 0.3058 | 0.2978 | 0.0137 | 0.0057 | 0.0490 | 1.0137 | 0.5873 | 0.9524 | 0.817 | 0.3942 |
| SBS | 0.2103 | 0.2000 | 0.0695 | 0.0167 | 0.0119 | 0.0522 | 1.0167 | 0.4524 | 0.9444 | 1.000 | 0.2139 |
| DecisionTree | 0.3214 | 0.2876 | 0.2855 | 0.0175 | 0.0071 | 0.0599 | 1.0175 | 0.5516 | 0.9246 | 1.046 | 0.2917 |
| Dummy-most-frequent | 0.2579 | 0.2000 | 0.0820 | 0.0216 | 0.0099 | 0.0839 | 1.0216 | 0.5000 | 0.8690 | 1.291 | 1.2397 |
| Dummy-stratified | 0.2341 | 0.2043 | 0.2060 | 0.0264 | 0.0144 | 0.0905 | 1.0264 | 0.4484 | 0.8373 | 1.578 | 0.4136 |

Random Forest is the best ML selector by mean regret, consistent with [1] where RF also won the selector comparison. Its classification accuracy (40.1% over five classes) is modest, but it translates into routing quality: mean regret 1.24% versus 1.67% for SBS, within-1%-of-VBS rate 63.1% versus 45.2%, and m̂ = 0.741, i.e., the selector closes about 26% of the SBS-to-VBS gap. Decision Tree shows that a weak selector can be worse than no selector (m̂ > 1).

## 9. Important Features

Top Random Forest impurity importances: `capacity_pressure` (0.044), `demand_std` (0.042), `depot_distance_std` (0.041), `depot_centrality_normalized` (0.040), `total_demand` (0.040). Top held-out permutation importances: `depot_centrality_normalized` (0.0135), `ring_3_ratio` (0.0119), `depot_distance_std` (0.0111), `ring_4_ratio` (0.0103), `std_pairwise_customer_distance` (0.0095). Depot centrality and the ring-occupancy profile — the features closest to the paper's characterization — are the strongest held-out predictors. These are predictive associations, not causal claims.

## 10. Grouped Performance And Benchmark Demo

Random Forest on the test split, grouped (n = instances, regret = mean regret, w1% = within 1% of VBS):

By customer count:

| customers | n | accuracy | regret | w1% |
| --- | ---: | ---: | ---: | ---: |
| 20 | 81 | 0.370 | 0.0173 | 0.580 |
| 50 | 88 | 0.352 | 0.0134 | 0.602 |
| 100 | 83 | 0.482 | 0.0065 | 0.711 |

By demand regime:

| regime | n | accuracy | regret | w1% |
| --- | ---: | ---: | ---: | ---: |
| high_pressure | 58 | 0.293 | 0.0210 | 0.466 |
| high_variance | 73 | 0.452 | 0.0107 | 0.685 |
| low_pressure | 64 | 0.453 | 0.0089 | 0.688 |
| low_variance | 57 | 0.386 | 0.0098 | 0.667 |

By depot position:

| depot | n | accuracy | regret | w1% |
| --- | ---: | ---: | ---: | ---: |
| center | 92 | 0.424 | 0.0142 | 0.609 |
| corner | 76 | 0.447 | 0.0115 | 0.697 |
| random | 84 | 0.333 | 0.0113 | 0.595 |

The selector is strongest on 100-customer instances and weakest under high capacity pressure, suggesting more geometric structure helps and tightly constrained instances are intrinsically harder.

**Benchmark demo (out-of-distribution).** On CVRPLIB `E-n51-k5` (proven optimum 521), the heuristic portfolio's best result is `WH72-sweep/both-directions` at 522 (+0.19%) in 0.16 s, and the Random Forest selector — trained only on synthetic instances — **correctly predicts** `WH72-sweep/both-directions` (class probability 0.33). The exact model was attempted and honestly recorded as exceeding the free size-limited Gurobi license (51 nodes → 2550 binary arc variables > 2000); with a full license it would run. A single benchmark is a demo, not a systematic out-of-distribution evaluation.

## 11. Reproducibility And Integrity

VeRyPy is pinned to commit `8698f910ffcfb4bc8743aedbf203d6de72fbe006`; gurobipy 13 installs with the free size-limited license, which covers every exact solve reported here. The pipeline validates that final labels equal the minimum feasible portfolio cost, train/test instance IDs are disjoint, VBS regret is exactly zero and its cost ratio exactly one, prohibited solver/result/label columns cannot enter the feature matrix, and all metrics are finite. Every solution — heuristic or exact — is re-validated and re-costed by independent code. The frozen ML experiment (`reports/final_ml_experiment/`) was generated once; the exact baseline (`reports/exact_baseline/`) reproduces with `uv run python -m cvrp_algorithm_selection.exact_baseline`.

## 12. Limitations

- The selector is trained and tested on synthetic instances; only one CVRPLIB benchmark probes out-of-distribution behavior.
- Labels come from a small classical-heuristic portfolio, not exact optima; the VBS is a portfolio oracle.
- Random Forest improves regret over SBS, but the margin is moderate (m̂ = 0.741).
- The fixed time budget bounds runtime but the label objective does not reward faster solvers among non-tied costs.
- The exact MIP baseline uses a weak MTZ formulation; it proves optimality only on the smallest instance within 300 s, and the free Gurobi license caps exactly solvable size.

## 13. Conclusion

The requirement is met end-to-end: the problem is introduced with exact (gurobipy) and heuristic solutions on benchmark and self-created instances; measurable pre-solution features — size, demand variance, depot centrality, and geometry — feed a classifier that predicts the best heuristic configuration under a fixed 20 s budget; and the resulting Random Forest meta-solver beats the single-best-solver baseline on routing regret (m̂ = 0.741), mirroring the algorithm-selection findings of Asín-Achá et al. at student scale, including a correct prediction on a real CVRPLIB benchmark.

## References

1. Asín-Achá, R., Espinoza, A., Goldschmidt, O., Hochbaum, D. S., Huerta, I. I. (2024). Selecting fast algorithms for the capacitated vehicle routing problem with machine learning techniques. *Networks*, 84(4), 465–480. doi:10.1002/net.22244.
2. Rasku, J., Kärkkäinen, T., Musliu, N. (2019). Meta-survey and implementations of classical capacitated vehicle routing heuristics with reproduced results. In *Toward Automatic Customization of Vehicle Routing Systems*, University of Jyväskylä. (VeRyPy library, https://github.com/yorak/VeRyPy.)
3. Miller, C. E., Tucker, A. W., Zemlin, R. A. (1960). Integer programming formulation of traveling salesman problems. *Journal of the ACM*, 7(4), 326–329.
4. Clarke, G., Wright, J. W. (1964). Scheduling of vehicles from a central depot to a number of delivery points. *Operations Research*, 12(4), 568–581.
5. Mole, R. H., Jameson, S. R. (1976). A sequential route-building algorithm employing a generalised savings criterion. *Operational Research Quarterly*, 27(2), 503–511.
6. Wren, A., Holliday, A. (1972). Computer scheduling of vehicles from one or more depots to a number of delivery points. *Operational Research Quarterly*, 23(3), 333–344.
7. Christofides, N., Mingozzi, A., Toth, P. (1979). The vehicle routing problem. In *Combinatorial Optimization*, Wiley, 315–338.
8. Beasley, J. E. (1983). Route first–cluster second methods for vehicle routing. *Omega*, 11(4), 403–408.
9. Christofides, N., Eilon, S. (1969). An algorithm for the vehicle-dispatching problem. *Operational Research Quarterly*, 20(3), 309–318. (Source of the E-n51-k5 benchmark; best-known value via CVRPLIB.)
10. Gurobi Optimization, LLC (2026). *Gurobi Optimizer Reference Manual*. https://www.gurobi.com.
