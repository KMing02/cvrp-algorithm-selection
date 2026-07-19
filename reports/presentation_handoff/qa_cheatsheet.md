# Q&A Cheatsheet

## How do the heuristics compare against exact optima?
Small instances are solved exactly with gurobipy (MTZ-style MIP, `reports/exact_baseline/`): on the tiny manual instance all five heuristics match the proven optimum; on 20-customer instances the heuristics match or come within ~0.5% of Gurobi's 300-second incumbent in milliseconds; on E-n51-k5 the best heuristic is 0.19% above the proven optimum 521. Selector labels remain the virtual best solver within the portfolio, not exact optima, because exact solving does not scale to the full dataset.

## What does the fixed time budget mean?
Every portfolio solver runs under the same 20-second wall-clock budget (`TIME_BUDGET_SECONDS`); a solver that fails to finish is recorded as a failure. All feasible runs in the frozen experiment finished within the budget (max 16.98 s), so the labels are exactly "best solution within 20 s".

## Why exclude Gaskell?
It was evaluated and remains implemented, but won only 3 of 240 development instances. Keeping it in the main classifier would create a class with too few examples for reliable supervised learning.

## Why use `cvrplib_euc_2d`?
The project includes CVRPLIB-style instances and uses the TSPLIB rounded Euclidean convention to avoid silently comparing floating-point costs with integer benchmark conventions.

## Is there feature leakage?
The model feature matrix is built from an explicit feature allowlist/blocklist and excludes solver costs, runtimes, feasibility flags, labels, IDs, seeds, and generator category names.

## Why does accuracy look modest?
Several solvers are close in cost, so misclassification is not always expensive. Routing regret is the more relevant metric for this project.

## Does ML beat SBS?
Yes on the held-out test set for routing quality: Random Forest mean regret is 1.24% versus SBS 1.67%; within-1% of VBS is 63.1% versus 45.2%.

## Does ML beat SBS on runtime?
No. Runtime is secondary here. Random Forest selected solvers average 0.463s versus SBS 0.214s.

## What is VBS?
The Virtual Best Solver is an oracle that picks the lowest-cost feasible solver per test instance. It is not a trained model and should be treated as the upper-bound portfolio performance.

## Does the selector generalise beyond synthetic data?
Yes, this is now measured directly: the frozen-split Random Forest was evaluated on 87 classic CVRPLIB instances (sets A, B, E, P; 32-101 nodes) it never saw during training, with all five portfolio solvers re-run under the same 20 s budget. See `reports/cvrplib_ood/` for accuracy, regret, and the m-hat metric per set.

## Why is a genetic algorithm not in the portfolio?
PyVRP's hybrid genetic search (HGS) was benchmarked at the same 20-second budget (`reports/hgs_benchmark/`). It wins essentially every instance at that budget, so including it would collapse the label distribution into one dominant class and trivialise the learning problem (the frozen pipeline enforces a dominance ceiling of 80%). Instead HGS serves as the heavyweight reference quantifying the speed-quality trade-off: the ML-selected classical heuristic answers in well under a second, HGS spends the full 20 s for a few percent better routes.

## Were hyperparameters tuned?
The frozen headline experiment uses fixed, hand-chosen hyperparameters. A paper-style grid search with 5-fold cross-validation on the frozen training split (`reports/hyperparameter_tuning/`) was run as a supplement: tuned models land within noise of the fixed-parameter results, confirming the fixed choices were reasonable.

## What is the largest limitation?
The main experiment's dataset is synthetic, and labels are only as good as the heuristic portfolio. The CVRPLIB out-of-distribution evaluation (sets A, B, E, P) bounds this concern but larger benchmark families (M, Golden, X) remain untested.
