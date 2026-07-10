# Slide Content Outline

## 1. Motivation
- CVRP has many fast heuristics, but no single heuristic is universally best.
- Goal: learn a selector from instance features before solving.

## 2. Problem Scope
- Symmetric Euclidean CVRP.
- One depot, homogeneous capacity, positive heterogeneous demands.
- Exact solving (gurobipy MIP) only as a small-instance baseline; no advanced custom metaheuristics.

## 3. Solver Foundation
- Reused VeRyPy classical heuristics.
- Independent route conversion, validation, and cost recomputation.
- Distance convention fixed to `cvrplib_euc_2d`.

## 4. Portfolio Audit
- Initial three-solver portfolio was dominated by Clarke-Wright.
- Expanded audit produced a complementary portfolio.
- Gaskell excluded from ML because it had too few wins.

## 5. Final Portfolio
- `CW64-PS/minimize-distance+2opt1`
- `MJ76-insertion/all-strain`
- `WH72-sweep/both-directions`
- `CMT79-2phase/default`
- `Be83-RFCS/default`

## 6. Synthetic Dataset
- 1260 instances.
- 5 spatial families, 3 depot positions, 4 demand regimes, 3 customer counts, 7 seeds.
- Stable IDs and saved generation manifests.

## 7. Feature Extraction
- Size/capacity features.
- Demand distribution.
- Depot geometry.
- Customer geometry.
- Five radial ring ratios.
- No solver outcomes or generator category labels in the feature matrix.

## 8. Label Distribution
- Show `reports/final_ml_experiment/plots/label_distribution.png`.
- Largest class remains well below dominance threshold.

## 9. Baselines And Models
- Dummy classifiers.
- SBS from training data only.
- VBS oracle.
- KNN, Decision Tree, Random Forest, Gradient Boosting.

## 10. Main Results
- Show accuracy/balanced accuracy plot.
- Random Forest is best by mean regret.
- RF mean regret: 1.24%; SBS mean regret: 1.67%.

## 11. Routing Quality
- Show mean regret and within-threshold plots.
- RF within 1%: 63.1%; SBS within 1%: 45.2%.

## 12. Confusion Matrix
- Show Random Forest confusion matrix.
- Explain class imbalance and close-cost alternatives.

## 13. Feature Importance
- Show RF feature importance.
- Emphasise predictive, not causal, interpretation.

## 14. Grouped Findings
- Best on 100-customer instances.
- High-pressure demand is hardest.
- Random depot position has lower accuracy.

## 15. Limitations And Next Work
- Synthetic data only.
- Heuristic labels are not true optima.
- Runtime not part of objective.
- Possible next step: broader benchmark instances and cost-runtime multi-objective labels.
