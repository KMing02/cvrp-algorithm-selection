# Portfolio Audit Report

Pinned VeRyPy commit: `8698f910ffcfb4bc8743aedbf203d6de72fbe006`.

Development dataset: 240 synthetic instances, `cvrplib_euc_2d`, customer counts 20 and 50, seeds 0 and 1.

Full candidate audit runtime: 308.7 seconds.

## Candidate Comparison

| Solver/config | Success | Mean rt (s) | Median rt (s) | Mean gap | Median gap | Wins | Win % | <=1% | <=5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Be83-RFCS/default | 100.0% | 0.1663 | 0.0985 | 2.19% | 0.82% | 57 | 23.8% | 54.2% | 87.1% |
| WH72-sweep/both-directions | 100.0% | 0.2932 | 0.1629 | 2.13% | 1.00% | 52 | 21.7% | 50.0% | 87.5% |
| MJ76-insertion/all-strain | 100.0% | 0.0949 | 0.0716 | 1.87% | 1.16% | 46 | 19.2% | 46.7% | 90.4% |
| CMT79-2phase/default | 100.0% | 0.0068 | 0.0044 | 4.97% | 3.51% | 27 | 11.2% | 21.2% | 58.3% |
| CW64-PS/minimize-distance | 100.0% | 0.0033 | 0.0043 | 3.62% | 2.80% | 24 | 10.0% | 29.2% | 75.0% |
| CW64-PS/minimize-distance+2opt1 | 100.0% | 0.0036 | 0.0049 | 3.42% | 2.43% | 23 | 9.6% | 32.1% | 75.4% |
| GM74-sweep/both-directions | 100.0% | 0.6184 | 0.2587 | 6.57% | 4.32% | 6 | 2.5% | 22.5% | 54.6% |
| Gaskell-PS/both-savings | 100.0% | 0.0060 | 0.0056 | 4.93% | 4.10% | 3 | 1.2% | 8.8% | 62.5% |
| CW64-SS/farthest-seed | 100.0% | 0.0028 | 0.0033 | 10.67% | 9.62% | 1 | 0.4% | 5.8% | 29.2% |
| Ty68-NN/default | 100.0% | 0.0129 | 0.0044 | 18.70% | 17.26% | 1 | 0.4% | 0.8% | 7.1% |
| SNN/closest-seed/both-route-ends | 100.0% | 0.0012 | 0.0014 | 15.80% | 14.69% | 0 | 0.0% | 0.0% | 7.9% |
| SNN/farthest-seed/both-route-ends | 100.0% | 0.0012 | 0.0012 | 18.31% | 17.10% | 0 | 0.0% | 0.0% | 4.2% |
| CW64-SS/closest-seed | 100.0% | 0.0027 | 0.0035 | 19.73% | 19.20% | 0 | 0.0% | 0.0% | 4.6% |
| basic-sweep/both-directions/best-start+2opt1 | 100.0% | 0.0272 | 0.0370 | 31.02% | 24.92% | 0 | 0.0% | 0.0% | 1.7% |
| basic-sweep/both-directions/best-start | 100.0% | 0.0255 | 0.0259 | 33.17% | 26.91% | 0 | 0.0% | 0.0% | 0.8% |
| cheapest-insertion/sequential-farthest+2opt1 | 100.0% | 0.0061 | 0.0064 | 35.61% | 35.22% | 0 | 0.0% | 0.0% | 0.0% |
| cheapest-insertion/sequential-farthest | 100.0% | 0.0065 | 0.0078 | 37.30% | 36.68% | 0 | 0.0% | 0.0% | 0.0% |

## Recommended Portfolio

- `Be83-RFCS/default`: 59 wins (24.6%).
- `WH72-sweep/both-directions`: 55 wins (22.9%).
- `MJ76-insertion/all-strain`: 47 wins (19.6%).
- `CMT79-2phase/default`: 27 wins (11.2%).
- `CW64-PS/minimize-distance+2opt1`: 49 wins (20.4%).
- `Gaskell-PS/both-savings`: 3 wins (1.2%).

Expected label distribution for the recommended subset: Be83-RFCS/default: 59/240 (24.6%), WH72-sweep/both-directions: 55/240 (22.9%), CW64-PS/minimize-distance+2opt1: 49/240 (20.4%), MJ76-insertion/all-strain: 47/240 (19.6%), CMT79-2phase/default: 27/240 (11.2%), Gaskell-PS/both-savings: 3/240 (1.2%).

## Pairwise Dominance Highlights

- `CW64-PS/minimize-distance+2opt1` vs `CW64-PS/minimize-distance`: 123 / 0 wins, 117 ties; average relative improvement when first wins 0.38%, when second wins 0.00%.
- `WH72-sweep/both-directions` vs `GM74-sweep/both-directions`: 176 / 17 wins, 47 ties; average relative improvement when first wins 5.47%, when second wins 2.27%.
- `Be83-RFCS/default` vs `WH72-sweep/both-directions`: 99 / 106 wins, 35 ties; average relative improvement when first wins 3.07%, when second wins 2.97%.
- `Be83-RFCS/default` vs `MJ76-insertion/all-strain`: 115 / 102 wins, 23 ties; average relative improvement when first wins 2.42%, when second wins 3.34%.
- `WH72-sweep/both-directions` vs `MJ76-insertion/all-strain`: 109 / 105 wins, 26 ties; average relative improvement when first wins 2.68%, when second wins 3.30%.
- `MJ76-insertion/all-strain` vs `CMT79-2phase/default`: 163 / 54 wins, 23 ties; average relative improvement when first wins 4.81%, when second wins 2.05%.

## Family-Level Win Patterns

### customer_count
- `20`: Be83-RFCS/default: 33, WH72-sweep/both-directions: 27, CMT79-2phase/default: 19, MJ76-insertion/all-strain: 15, CW64-PS/minimize-distance: 13
- `50`: MJ76-insertion/all-strain: 31, WH72-sweep/both-directions: 25, Be83-RFCS/default: 24, CW64-PS/minimize-distance+2opt1: 13, CW64-PS/minimize-distance: 11
### demand_regime
- `high_pressure`: MJ76-insertion/all-strain: 18, WH72-sweep/both-directions: 15, CW64-PS/minimize-distance: 8, Be83-RFCS/default: 7, CW64-PS/minimize-distance+2opt1: 6
- `high_variance`: MJ76-insertion/all-strain: 14, CW64-PS/minimize-distance+2opt1: 10, Be83-RFCS/default: 9, CW64-PS/minimize-distance: 9, WH72-sweep/both-directions: 9
- `low_pressure`: Be83-RFCS/default: 22, WH72-sweep/both-directions: 17, CMT79-2phase/default: 12, MJ76-insertion/all-strain: 3, CW64-PS/minimize-distance: 2
- `low_variance`: Be83-RFCS/default: 19, MJ76-insertion/all-strain: 11, WH72-sweep/both-directions: 11, CMT79-2phase/default: 5, CW64-PS/minimize-distance: 5
### depot_position
- `center`: Be83-RFCS/default: 23, WH72-sweep/both-directions: 18, MJ76-insertion/all-strain: 14, CMT79-2phase/default: 9, CW64-PS/minimize-distance: 8
- `corner`: MJ76-insertion/all-strain: 18, Be83-RFCS/default: 16, WH72-sweep/both-directions: 16, CMT79-2phase/default: 12, CW64-PS/minimize-distance+2opt1: 7
- `random`: Be83-RFCS/default: 18, WH72-sweep/both-directions: 18, MJ76-insertion/all-strain: 14, CW64-PS/minimize-distance+2opt1: 11, CW64-PS/minimize-distance: 10
### spatial_family
- `clustered`: Be83-RFCS/default: 12, WH72-sweep/both-directions: 12, MJ76-insertion/all-strain: 9, CMT79-2phase/default: 8, CW64-PS/minimize-distance+2opt1: 3
- `mixed`: WH72-sweep/both-directions: 14, Be83-RFCS/default: 10, MJ76-insertion/all-strain: 10, CW64-PS/minimize-distance: 8, CMT79-2phase/default: 3
- `radial`: Be83-RFCS/default: 10, WH72-sweep/both-directions: 10, CW64-PS/minimize-distance+2opt1: 9, CMT79-2phase/default: 6, MJ76-insertion/all-strain: 6
- `two_clusters`: WH72-sweep/both-directions: 12, MJ76-insertion/all-strain: 11, CMT79-2phase/default: 8, Be83-RFCS/default: 7, CW64-PS/minimize-distance: 5
- `uniform`: Be83-RFCS/default: 18, MJ76-insertion/all-strain: 10, CW64-PS/minimize-distance: 6, CW64-PS/minimize-distance+2opt1: 5, WH72-sweep/both-directions: 4

## Inspected Candidate Modules

- `verypy.classic_heuristics.parallel_savings.parallel_savings_init`
- `verypy.classic_heuristics.sequential_savings.sequential_savings_init`
- `verypy.classic_heuristics.gaskell_savings.gaskell_savings_init`
- `verypy.classic_heuristics.sweep.sweep_init`
- `verypy.classic_heuristics.gillet_miller_sweep.gillet_miller_init`
- `verypy.classic_heuristics.wren_holliday_sweep.wren_holliday_init`
- `verypy.classic_heuristics.cheapest_insertion.cheapest_insertion_init`
- `verypy.classic_heuristics.mole_jameson_insertion.mole_jameson_insertion_init`
- `verypy.classic_heuristics.cmt_2phase.cmt_2phase_init`
- `verypy.classic_heuristics.rfcs.route_first_cluster_second_init`
- `verypy.classic_heuristics.tyagi_nearest_neighbor.tyagi_init`
- `verypy.classic_heuristics.lr3opt.lr3opt_init`
- `verypy.classic_heuristics.matchingvrp`, `petalvrp`, `gapvrp`

## Rejections / Concerns

- `matchingvrp`, `petalvrp`, and `gapvrp` import `gurobipy`; rejected under no proprietary solver constraint.
- `lr3opt_init` was feasible but too slow for the dev dataset scale in this phase (~11s on `E-n51-k5`).
- `GM74-sweep/both-directions` was feasible and had 6 wins, but mean runtime was high (0.618s/instance) and it was dominated for practical purposes by Wren-Holliday/RFCS/MJ quality-runtime tradeoffs.
- Cheapest insertion and basic Sweep variants were reliable but dominated in quality on this dataset.
- CMT/RFCS/Tyagi use VeRyPy internal TSP fallback because external TSP executables are not installed; results may differ from published variants.