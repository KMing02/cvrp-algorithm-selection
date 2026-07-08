# Presentation Brief

## One-Sentence Claim

A small Random Forest selector using only pre-solution CVRP instance features can choose among five classical VeRyPy heuristics and reduce mean routing regret versus the training-set Single Best Solver.

## Key Numbers

- Final dataset: 1260 synthetic CVRP instances.
- Train/test split: 1008 / 252, stratified by best solver.
- Distance convention: `cvrplib_euc_2d`.
- Final portfolio size: 5 solvers.
- Best model: Random Forest.
- Random Forest accuracy: 40.1%.
- Random Forest mean regret: 1.24%.
- SBS mean regret: 1.67%.
- Random Forest within 1% of VBS: 63.1%.
- SBS within 1% of VBS: 45.2%.
- Random Forest within 5% of VBS: 95.6%.

## Final Portfolio

- `CW64-PS/minimize-distance+2opt1`
- `MJ76-insertion/all-strain`
- `WH72-sweep/both-directions`
- `CMT79-2phase/default`
- `Be83-RFCS/default`

Gaskell was evaluated in the six-solver audit but excluded from the main selector because it won only 3/240 development instances.

## Main Caveat

The selector optimises route cost only. Solver runtime is reported separately and Random Forest tends to select slower solvers than SBS on average.
