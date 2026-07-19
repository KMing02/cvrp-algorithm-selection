# Presentation Script — "Learning Which VRP Solver Works Best"

Companion to `presentation.pptx` (16 main slides + a backup divider + 3 backup slides, built on
the official TUM template `2111_Praesentationsvorlage_16-9.potx`). Every slide's narration is
also embedded in the deck's speaker notes.

**Format**: ~30 minutes total → **~19 minutes talk + ~10 minutes Q&A**.
Speak at a calm pace; the per-slide times below add up to 19:00 with a small buffer.

| # | Slide | Time | Cumulative |
|---|---|---|---|
| 1 | Title | 0:45 | 0:45 |
| 2 | The problem: CVRP | 1:15 | 2:00 |
| 3 | Exact solving hits a wall | 1:30 | 3:30 |
| 4 | No single heuristic wins | 1:15 | 4:45 |
| 5 | The solution: a learned meta-solver | 1:30 | 6:15 |
| 6 | The portfolio | 1:15 | 7:30 |
| 7 | 1,260 synthetic instances | 1:15 | 8:45 |
| 8 | 38 features | 1:15 | 10:00 |
| 9 | How we measure a selector | 1:00 | 11:00 |
| 10 | Main result | 2:00 | 13:00 |
| 11 | What the model looks at | 1:00 | 14:00 |
| 12 | Where it works / struggles | 1:00 | 15:00 |
| 13 | Transfer to real benchmarks | 1:45 | 16:45 |
| 14 | Extension: HGS trade-off | 1:45 | 18:30 |
| 15 | Limitations & takeaways | 1:00 | 19:30 |
| 16 | Conclusion | 0:30 | 20:00 |

---

## Slide 1 — Title (0:45)

> Good morning everyone. Today I'm presenting my project "Learning which VRP solver works best".
> The one-sentence summary: instead of picking one heuristic for the vehicle routing problem and
> hoping it's good, I trained a machine-learning model that looks at an instance first and then
> predicts which of five classical heuristics will solve it best within a fixed time budget.
> The methodology follows a 2024 paper by Asín-Achá and co-authors in *Networks*, scaled to a
> student project. I'll walk from the problem, through the pipeline, to the results — including
> an honest out-of-distribution test on real benchmarks and a speed-versus-quality extension.

*Transition: "Let me set up the problem first."*

## Slide 2 — The Problem: CVRP (1:15)

> In the capacitated vehicle routing problem we have a depot with a fleet of identical vehicles,
> each with capacity Q. Every customer has a demand and must be visited exactly once. Each route
> starts and ends at the depot, and the customers on a route can't exceed the vehicle's capacity.
> We minimize total travelled distance. The picture on the right shows the shape of a solution:
> the square is the depot, each colored loop is one vehicle's route.
>
> The problem is NP-hard — you're deciding simultaneously how to *group* customers and in which
> *order* to visit them — and in logistics practice you often need an answer in seconds. That
> tension between hardness and speed drives everything in this project.

*Transition: "So what happens if we just try to solve it exactly?"*

## Slide 3 — Exact Solving Hits a Wall (1:30)

> First requirement of the project: introduce the problem by solving instances exactly with
> gurobipy and heuristically. I modelled CVRP as a mixed-integer program — a two-index arc
> formulation where load variables propagate along routes, which eliminates subtours and enforces
> capacity at the same time.
>
> The result is sobering. With **six customers**, Gurobi proves the optimum in a hundredth of a
> second, and all five heuristics match it. At **twenty customers**, after five full minutes
> Gurobi still cannot *prove* optimality — up to a two percent gap stays open — while the
> heuristics match or nearly match its best solution in under four hundredths of a second. And at
> **fifty-one customers**, the model doesn't even fit the free license anymore.
>
> So exact solving gives us trustworthy reference points on small instances, but the real work has
> to be done by fast heuristics. The question becomes: *which one?*

## Slide 4 — No Single Heuristic Wins (1:15)

> Here is the core empirical fact that motivates the whole project. I ran five classical
> heuristics on all 1,260 instances of my dataset and asked: which one is best, per instance?
> The answer: **it depends**. Route-first-cluster-second wins about a quarter of the time,
> Clarke-Wright another quarter, Mole-Jameson a fifth — even the weakest still wins nearly one in
> ten. No solver dominates, and picking wrongly can cost up to **nineteen percent** extra route
> length. Which solver wins depends on the instance's geometry, depot position, and demand
> structure.
>
> This is exactly what the algorithm-selection literature addresses: don't pick one solver for
> all instances — learn a model that predicts the winner for *each* instance. That is the
> approach of the paper this project follows.

*Transition: "Here's the solution as a pipeline."*

## Slide 5 — The Solution: A Learned Meta-Solver (1:30)

> A new instance comes in. We extract thirty-eight cheap features — statistics you can compute
> before any solving. A trained Random Forest looks at those features and predicts which portfolio
> heuristic will win. We run only that heuristic, and get routes back in about a fifth of a second
> on average.
>
> Four design choices matter. First, every solver runs under the same fixed **twenty-second
> budget**, so the training label literally means "best solution within the budget" — cost ties
> break toward the faster solver. Second, strict leakage discipline: features are pre-solution
> only, enforced by an explicit blocklist in code. Third, algorithm *configuration* — the same
> heuristic with different settings — becomes separate portfolio entries; that's the discretized
> version of what the paper does. Fourth, if the predicted solver ever fails, we fall back to the
> single best solver — the meta-solver never returns empty-handed.

## Slide 6 — The Portfolio (1:15)

> The portfolio: five classical construction heuristics from the VeRyPy library, spanning the
> classic families — savings, sweep, insertion, two-phase clustering, and
> route-first-cluster-second. I pin the library to a fixed commit, and every solution any solver
> returns is independently re-validated and re-costed by my own code, so no library quirk can leak
> into the labels.
>
> Two things are deliberately missing. Gaskell's savings variant was audited but won only 3 of 240
> development instances — a class with three examples is not learnable. And there's no genetic
> algorithm in the portfolio. That's not an oversight: a modern hybrid genetic search would win
> nearly every instance at this budget, the label distribution would collapse, and there'd be
> nothing left to learn. I benchmark it separately — I'll show you exactly what it buys at the end.

## Slide 7 — 1,260 Synthetic Instances (1:15)

> Where does training data come from? Following the paper, I generate it synthetically, with the
> explicit goal of spanning as much instance variation as possible. It's a balanced factorial
> design: five spatial families — uniform scatter, clusters, two clusters, rings, mixed — times
> three depot positions, times four demand regimes, times three sizes, times seven seeds. That's
> 1,260 instances and 6,300 timed solver runs; exactly one run ever exceeded the budget.
>
> Each instance is labelled with the solver that produced the lowest feasible cost within 20
> seconds. I split into 1,008 training and 252 test instances, stratified by label, disjoint by
> construction. And everything is reproducible — every instance regenerates from a stable ID, and
> the generation manifests are stored next to the results.

## Slide 8 — 38 Features (1:15)

> What does the model actually see? Thirty-eight features in five groups, all computable in
> milliseconds. Size and capacity — including *capacity pressure*, how tightly total demand
> squeezes into the fleet. The shape of the demand distribution. Depot geometry — especially how
> central the depot is relative to the customers. Customer geometry — spread, nearest-neighbor
> distances, cluster separation. And the paper's signature feature: **ring occupancy** — the share
> of customers in five concentric rings around the depot.
>
> Just as important is what the model does *not* see. Solver outcomes, labels, seeds, generator
> categories — all blocked by explicit checks; the pipeline throws an error if a prohibited column
> shows up. The classifier learns geometry, not leaked answers.

## Slide 9 — How We Measure a Selector (1:00)

> Thirty seconds on measurement, because the field has two standard baselines. The **Single Best
> Solver** is the one solver that's best on average on training data — here, Mole-Jameson
> insertion. That's what you'd deploy without ML, so it's the baseline to beat. The **Virtual Best
> Solver** is an oracle that picks the true winner on every instance — the ceiling.
>
> The paper's normalized metric m-hat places a selector on the line between them: zero means you
> select like the oracle, one means you're no better than the baseline. My selector lands at
> **0.741** — let me unpack that now.

## Slide 10 — Main Result (2:00)

> I trained four model families, with dummy-classifier sanity baselines; Random Forest came out
> best — same as in the paper. The chart shows the share of test instances where the chosen
> solver lands within one percent of the best possible portfolio result. The no-ML baseline:
> 45 percent. Random Forest: **63 percent**. Mean regret drops from 1.67 to 1.24 percent. On the
> m-hat scale that's 0.741 — the selector closes about a quarter of the gap between baseline and
> oracle.
>
> Now, you might ask: only **40 percent accuracy** over five classes? Yes — and that's fine.
> Several solvers are often nearly tied, so a misclassification is usually cheap. What matters is
> route quality, not label accuracy. One instructive detail: the plain Decision Tree has m-hat
> *above one* — a weak selector is actively worse than no selector. Learning has to earn its place.

## Slide 11 — What the Model Looks At (1:00)

> Is the model learning something sensible? Permutation importance on held-out data says yes. The
> top feature is **depot centrality**, followed by two ring-occupancy shares and the spread of
> depot distances — precisely the geometric quantities the reference paper builds its
> characterization around. The broader pattern: geometry beats bookkeeping. Where customers sit
> relative to the depot tells you more about which heuristic wins than raw size does. One caveat I
> keep attached to this slide: importances are predictive associations, not causal explanations.

## Slide 12 — Where It Works and Where It Struggles (1:00)

> Slicing the test results: by size, the selector is best on hundred-customer instances —
> 71 percent within one percent — and weakest on the small ones; more geometric structure gives
> the features more to grab onto. By demand regime, **high capacity pressure** is clearly hardest —
> 47 percent versus roughly two-thirds elsewhere; when vehicles are squeezed to the limit, solver
> behavior becomes hard to predict. And randomly placed depots are hardest by position — which
> fits the importance story: the model leans on depot geometry, and random placement is where that
> signal varies most.

*Transition: "So far, everything was in-distribution. Now the harder question."*

## Slide 13 — Does It Transfer to Real Benchmarks? (1:45)

> Every ML project must answer: does it generalize beyond its own data distribution? I evaluated
> the frozen selector — trained purely on synthetic instances — on **85 classic CVRPLIB benchmark
> instances** from sets A, B, E and P, re-running the whole portfolio under the same budget, and
> anchoring against published proven optima.
>
> The honest answer: transfer is **partial**. The within-one-percent rate still clearly beats the
> baseline — 53 versus 43 percent overall, better on every set. But on mean regret the edge
> largely fades: 1.84 versus 1.88 percent — m-hat essentially one. The paper reports the same
> phenomenon: stylized benchmark families are hard when you trained on randomized synthetic data.
>
> Two silver linings. The portfolio itself is strong on real data — its best solver averages under
> two percent above proven optima. And on E-n51-k5, the selector picks exactly the right
> heuristic, landing 0.19 percent above the proven optimum in a sixth of a second.

## Slide 14 — Extension: What Does 20 s of Compute Buy? (1:45)

> Final piece — an extension beyond the course requirements that puts everything in perspective.
> If we spent the entire twenty-second budget on one solver, what would that buy? I benchmarked
> PyVRP's **hybrid genetic search** on a stratified sample of 45 test instances plus the CVRPLIB
> benchmark.
>
> Results: HGS wins or ties the portfolio oracle on **every single instance**, delivering on
> average **3.5 percent** shorter routes than the ML-selected heuristic — and it finds the proven
> optimum on E-n51-k5. But it consumes the full twenty seconds, while the ML-selected heuristic
> answers in a fifth of a second — roughly **ninety times** less compute.
>
> This is exactly why HGS is not in the portfolio: as a label it would swallow the dataset. As a
> reference, it prices the trade-off cleanly. Real-time answers or warm starts for a bigger
> optimizer → use the selector. Twenty seconds per instance affordable → just run HGS. Both
> answers are useful; they serve different operational regimes.

## Slide 15 — Limitations and Takeaways (1:00)

> Let me state the limitations as plainly as the results. Trained on synthetic data — and on real
> benchmarks the regret advantage largely disappears; I showed you that rather than hiding it.
> Labels are the portfolio's best, not true optima. The budget bounds runtime but doesn't reward
> speed. The exact baseline is a deliberately simple formulation under a free license.
>
> Against that: per-instance selection genuinely beats the single-best-solver baseline
> in-distribution. Cheap pre-solution features — above all depot geometry — carry real signal.
> Every number in this talk comes from frozen, integrity-checked artifacts anyone can re-run. And
> the speed-quality trade-off is now *measured*, not asserted.

## Slide 16 — Conclusion (0:30)

> To conclude in one sentence: **look at the instance first, then pick the solver.** A Random
> Forest over thirty-eight cheap features turns five sixty-year-old heuristics into a meta-solver
> that beats the standard baseline, transfers — partially and honestly measured — to real
> benchmarks, and sits at a well-understood point of the speed-quality spectrum. Exact where it
> proves, heuristic where it scales, learned where it chooses. Thank you — I'm happy to take
> questions.

---

## Q&A Preparation (~10 minutes)

**Q: Accuracy is only 40% — isn't the model just bad?**
Five classes, and several solvers are often nearly tied in cost, so the *label* is almost
arbitrary between them while the *cost* difference is tiny. That's why the evaluation centers on
regret and within-1% rate — the quantities a dispatcher actually cares about. On those, the
selector clearly beats the baseline. (Slide 10's note: Decision Tree shows what a genuinely bad
selector looks like — m̂ > 1.)

**Q: Why keep the genetic algorithm out of the portfolio? Isn't that cherry-picking?**
The opposite — it's what keeps the learning problem meaningful. HGS wins or ties the oracle on
100% of sampled instances at this budget; as a label class it would exceed the pipeline's 80%
dominance ceiling and there would be nothing to select. The paper does the analogous thing: its
portfolio uses HGS only until the *first feasible solution*, not full-budget HGS. I benchmark
full-budget HGS separately and report the trade-off (backup: `reports/hgs_benchmark/`).

**Q: Does it generalize to real data?**
Partially, and I measured it rather than claiming it: on 85 CVRPLIB instances the within-1% rate
still beats SBS (52.9% vs 43.5%) and set B shows a real regret gain (m̂ = 0.85), but overall mean
regret is essentially tied (m̂ = 0.98). Consistent with the paper's own error analysis on
stylized benchmark families. The fix would be training data that mimics benchmark structure.

**Q: Why train on synthetic data at all?**
Labelling requires running the *whole portfolio* on every instance — thousands of timed solver
runs. Synthetic generation gives unlimited labelled data with controlled variation, and it's the
protocol of the reference paper (train synthetic, test public benchmarks). My OOD section is
exactly that protocol's test.

**Q: How do you prevent feature leakage?**
An explicit blocklist: solver costs, runtimes, feasibility flags, labels, seeds, and generator
category names are rejected by code (`feature_columns()` raises on prohibited columns), and the
notebook re-checks the saved feature manifest. Features are computable before any solver runs.

**Q: Were hyperparameters tuned?**
The frozen headline used fixed ones; I later ran the paper-style 5-fold grid search on the
training split as a supplement (backup slide). All CV accuracies land within ~1 point; tuned test
regrets straddle the frozen RF's. Fixed choices confirmed reasonable, frozen results unchanged.

**Q: How does the exact model avoid subtours?**
MTZ-style load propagation: u_j ≥ u_i + q_j − Q(1−x_ij) forces load to increase along
customer-customer arcs, so any cycle must pass through the depot; the same constraint enforces
capacity. Weak formulation but simple and correct — it's a baseline, not a contribution (backup
slide has the full model).

**Q: Why is runtime not part of the objective?**
Scope decision: quality-within-budget is the label, runtime only breaks exact-cost ties. The
budget bounds worst-case time. A cost-runtime multi-objective label is the natural next step and
is listed as future work.

**Q: What's different from the paper?**
Portfolio (their 3 solvers incl. an ML-configured sweep + first-feasible HGS vs my 5 VeRyPy
classics), configuration (their regression configurator vs my discretized configs as portfolio
entries), test data (their 264 CVRPLIB incl. huge instances vs my synthetic test + 85-instance
OOD supplement), and demands (they convert to unit demands; I keep originals). Same framework:
features → classifier → per-instance selection, evaluated by accuracy and m̂ against SBS/VBS.

**Q: How expensive is feature extraction?**
Milliseconds at these sizes. It computes an O(n²) distance matrix, so it would grow for n in the
thousands, but the portfolio solvers grow faster — extraction stays negligible in relative terms.

**Q: Is any of this reproducible?**
Yes, aggressively: pinned VeRyPy commit, stable instance IDs, saved generation manifests and
split manifests, label-integrity checks that re-derive every label from raw costs at load time,
and documented `uv run` commands for every experiment.

---

## Delivery Notes

- **Practice against the timer once**: the script is ~2,700 words ≈ 19 min at a calm 140 wpm.
- If running long, compress slides 11 and 12 (say only the bolded sentences) — saves ~1.5 min.
- The narration is embedded in each slide's **speaker notes** — presenter view is enough; this
  file is for rehearsal.
- **Check the presentation machine**: this laptop currently has no PowerPoint/WPS installed, so
  the deck was validated programmatically but not visually rendered here. Open it once on the
  machine you'll present with (or any PowerPoint/WPS/Google Slides) the day before. The deck uses
  the official TUM template (Arial throughout, TUM-blue palette), so it needs no special fonts.
- **Add your name**: the title slide shows course, date, and subtitle but no presenter name —
  add it under the subtitle. Slide 17 is a "Backup Slides" divider; end your talk on slide 16 and
  only go past it when a question calls for the details.
- Numbers you must be able to say from memory: **63% vs 45%** (within-1%), **1.24% vs 1.67%**
  (regret), **m̂ = 0.741**, **40%** accuracy, **52.9% vs 43.5%** (OOD), **+3.5% / 91×** (HGS),
  **20 s** budget, **1,260 / 85** instances.
