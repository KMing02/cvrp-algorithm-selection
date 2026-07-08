# Q&A Cheatsheet

## Why not compare against exact optima?
The project target is algorithm selection among fast classical heuristics, not optimality proof. Labels are the virtual best solver within the selected portfolio.

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

## What is the largest limitation?
The final dataset is synthetic, and labels are only as good as the heuristic portfolio. Generalisation to public benchmarks should be tested before making stronger claims.
