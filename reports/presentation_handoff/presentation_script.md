# Presentation Script — "Learning Which VRP Solver Works Best"

Companion to `presentation.pptx` (17 talk slides + a backup divider + 3 backup slides, built on
the official TUM template `2111_Praesentationsvorlage_16-9.potx`). Every slide's narration is
also embedded in the deck's speaker notes. The talk is written for **two presenters** ("we"
throughout) — split the slides between you at the natural break after slide 9 (setup → results).

Per our supervisor's feedback, the deck gives particular weight to the **engineered features**:
slide 8 states the three feature-engineering hypotheses, slide 11 tests them against observed
importance (expected vs observed), and slide 12 connects instance characteristics to individual
solver behavior.

**Format**: ~30 minutes total → **~20 minutes talk + ~10 minutes Q&A**.

| # | Slide | Time | Cumulative |
|---|---|---|---|
| 1 | Title | 0:45 | 0:45 |
| 2 | The problem: CVRP | 1:15 | 2:00 |
| 3 | Exact solving hits a wall | 1:15 | 3:15 |
| 4 | No single heuristic wins | 1:15 | 4:30 |
| 5 | The solution: a learned meta-solver | 1:15 | 5:45 |
| 6 | The portfolio | 1:00 | 6:45 |
| 7 | 1,260 synthetic instances | 1:15 | 8:00 |
| 8 | 38 features — three hypotheses | 1:30 | 9:30 |
| 9 | How we measure a selector | 1:00 | 10:30 |
| 10 | Main result | 1:45 | 12:15 |
| 11 | Feature importance: expected vs observed | 1:30 | 13:45 |
| 12 | Which characteristics favor which solver | 1:15 | 15:00 |
| 13 | Where it works / struggles | 0:45 | 15:45 |
| 14 | Transfer to real benchmarks | 1:30 | 17:15 |
| 15 | Extension: HGS trade-off | 1:30 | 18:45 |
| 16 | Limitations & takeaways | 1:00 | 19:45 |
| 17 | Conclusion | 0:30 | 20:15 |

---

## Slide 1 — Title (0:45)

> Good morning everyone. Today we're presenting our project "Learning which VRP solver works
> best". The one-sentence summary: instead of picking one heuristic for the vehicle routing
> problem and hoping it's good, we trained a machine-learning model that looks at an instance
> first and then predicts which of five classical heuristics will solve it best within a fixed
> time budget. The methodology follows a 2024 paper by Asín-Achá and co-authors in *Networks*,
> scaled to a student project. We'll walk from the problem, through the pipeline, to the results —
> with particular attention to the features we engineered and what they reveal about solver
> behavior — plus an honest out-of-distribution test on real benchmarks and a
> speed-versus-quality extension.

*Transition: "Let us set up the problem first."*

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

## Slide 3 — Exact Solving Hits a Wall (1:15)

> First requirement of the project: introduce the problem by solving instances exactly with
> gurobipy and heuristically. We modelled CVRP as a mixed-integer program — a two-index arc
> formulation where load variables propagate along routes, which eliminates subtours and enforces
> capacity at the same time.
>
> The result is sobering. With **six customers**, Gurobi proves the optimum in a hundredth of a
> second, and all five heuristics match it. At **twenty customers**, after five full minutes
> Gurobi still cannot *prove* optimality — up to a two percent gap stays open — while the
> heuristics match or nearly match its best solution in under four hundredths of a second. At
> **fifty-one customers**, the model doesn't even fit the free license anymore.
>
> So exact solving gives us trustworthy reference points, but the real work has to be done by
> fast heuristics. The question becomes: *which one?*

## Slide 4 — No Single Heuristic Wins (1:15)

> Here is the core empirical fact that motivates the whole project. We ran five classical
> heuristics on all 1,260 instances of our dataset and asked: which one is best, per instance?
> The answer: **it depends**. Route-first-cluster-second wins about a quarter of the time,
> Clarke-Wright another quarter, Mole-Jameson a fifth — even the weakest still wins nearly one in
> ten. No solver dominates, and picking wrongly can cost up to **nineteen percent** extra route
> length. Which solver wins depends on the instance's geometry, depot position, and demand
> structure.
>
> This is exactly what the algorithm-selection literature addresses: don't pick one solver for
> all instances — learn a model that predicts the winner for *each* instance. That is the
> approach of the paper this project follows.

*Transition: "Here's our solution as a pipeline."*

## Slide 5 — The Solution: A Learned Meta-Solver (1:15)

> A new instance comes in. We extract thirty-eight cheap features — statistics you can compute
> before any solving. A trained Random Forest looks at those features and predicts which portfolio
> heuristic will win. We run only that heuristic, and get routes back in about a fifth of a second
> on average.
>
> Four design choices matter. First, every solver runs under the same fixed **twenty-second
> budget**, so the training label literally means "best solution within the budget" — cost ties
> break toward the faster solver. Second, strict leakage discipline: features are pre-solution
> only, enforced by an explicit blocklist in code. Third, algorithm *configuration* becomes
> separate portfolio entries — the discretized version of what the paper does. Fourth, if the
> predicted solver ever fails, we fall back to the single best solver — the meta-solver never
> returns empty-handed.

## Slide 6 — The Portfolio (1:00)

> The portfolio: five classical construction heuristics from the VeRyPy library, spanning the
> classic families — savings, sweep, insertion, two-phase clustering, and
> route-first-cluster-second. We pin the library to a fixed commit, and every solution any solver
> returns is independently re-validated and re-costed by our own code, so no library quirk can
> leak into the labels.
>
> Two things are deliberately missing. Gaskell's savings variant won only 3 of 240 audit
> instances — a class with three examples is not learnable. And there's no genetic algorithm in
> the portfolio: a modern hybrid genetic search would win nearly every instance at this budget and
> collapse the label distribution. We benchmark it separately — we'll show you exactly what it
> buys at the end.

## Slide 7 — 1,260 Synthetic Instances (1:15)

> Where does training data come from? Following the paper, we generate it synthetically, with the
> explicit goal of spanning as much instance variation as possible. It's a balanced factorial
> design: five spatial families times three depot positions, times four demand regimes, times
> three sizes, times seven seeds. That's 1,260 instances and 6,300 timed solver runs; exactly one
> run ever exceeded the budget.
>
> Each instance is labelled with the solver that produced the lowest feasible cost within 20
> seconds. We split into 1,008 training and 252 test instances, stratified by label, disjoint by
> construction. And everything is reproducible — every instance regenerates from a stable ID, and
> the generation manifests are stored next to the results.

## Slide 8 — 38 Features: Three Hypotheses (1:30)

> What does the model actually see? Thirty-eight features in five groups, all computable from the
> raw instance in milliseconds. We engineered them around **three hypotheses** about what drives
> solver performance. First: **demand structure** — how large and how uneven the demands are, and
> how tightly they squeeze into the fleet; we capture that with capacity pressure and the demand
> distribution statistics. Second: **depot geometry** — how central the depot sits relative to
> the customers, plus the paper's signature feature, ring occupancy: the share of customers in
> five concentric rings around the depot. Third: **overall customer geometry and instance size**.
>
> Just as important is what the model does *not* see. Solver outcomes, labels, seeds, generator
> categories — all blocked by explicit checks; the pipeline throws an error if a prohibited
> column shows up. So the classifier learns instance characteristics, not leaked answers.
> Whether our three hypotheses were actually right is what the next two slides test.

## Slide 9 — How We Measure a Selector (1:00)

> Thirty seconds on measurement, because the field has two standard baselines. The **Single Best
> Solver** is the one solver that's best on average on training data — here, Mole-Jameson
> insertion. That's what you'd deploy without ML, so it's the baseline to beat. The **Virtual Best
> Solver** is an oracle that picks the true winner on every instance — the ceiling.
>
> The paper's normalized metric m-hat places a selector on the line between them: zero means you
> select like the oracle, one means you're no better than the baseline. Our selector lands at
> **0.741** — we'll unpack that now.

## Slide 10 — Main Result (1:45)

> The main result. We trained four model families, with dummy-classifier sanity baselines; Random
> Forest came out best — same as in the paper. The chart shows the share of test instances where
> the chosen solver lands within one percent of the best possible portfolio result. The no-ML
> baseline: 45 percent. Random Forest: **63 percent**. Mean regret drops from 1.67 to 1.24
> percent. On the m-hat scale that's 0.741 — the selector closes about a quarter of the gap
> between baseline and oracle.
>
> You might ask: only **40 percent accuracy** over five classes? Yes — and that's fine. Several
> solvers are often nearly tied, so a misclassification is usually cheap; what matters is route
> quality. One instructive detail: the plain Decision Tree has m-hat *above one* — a weak
> selector is actively worse than no selector. Learning has to earn its place.

*Transition: "So the model works. But the more interesting question — and the one our supervisor
asked us to emphasize — is WHY: which features carry the prediction?"*

## Slide 11 — Feature Importance: Expected vs Observed (1:30)

> So which of our engineered features actually carried the prediction — and did that match our
> expectations? Held-out permutation importance gives a clear answer, and it splits our three
> hypotheses three ways.
>
> Hypothesis one, **demand structure: confirmed**. Capacity pressure and demand spread rank at the
> very top of the tree-based importance ranking. Hypothesis two, **depot geometry: not just
> confirmed but stronger than we anticipated** — depot centrality is the single strongest held-out
> feature, with two of the ring-occupancy shares right behind it. And hypothesis three is the
> **surprise: raw instance size**, the most obvious feature of all, **is nearly irrelevant** — it
> never enters the top ten. In hindsight that makes sense: all five heuristics scale fine to a
> hundred customers, so what separates them is the *shape* of the instance, not its size.
>
> One caveat we keep attached to this slide: importances are predictive associations, not causal
> explanations. But we can go one level deeper and connect the characteristics to individual
> solvers — that's the next slide.

## Slide 12 — Which Characteristics Favor Which Solver? (1:15)

> Let us make that concrete — for us, the most interesting result of the project. The demand
> regime is the strongest signal. With even, low-variance demands, **route-first-cluster-second
> wins forty-one percent** of instances: when every customer needs about the same amount, cutting
> one giant tour into routes is clean. Flip to lumpy, high-variance demands and **Clarke-Wright
> with 2-opt takes over at thirty-eight percent** — greedy savings merges absorb uneven demands
> well. Under tight capacity, **Mole-Jameson insertion leads** — it checks feasibility at every
> insertion, which pays off when vehicles run full.
>
> Geometry tells the matching story: with a central depot or radial layouts, the **Wren-Holliday
> sweep peaks** — it partitions customers by angle around the depot, so it needs angular spread to
> work with. Put the depot in a corner and sweep fades while insertion takes the lead.
>
> Each heuristic's win region matches its construction principle — and this is exactly the signal
> the Random Forest exploits. The engineered features, not the model class, are the heart of the
> project.

## Slide 13 — Where It Works and Where It Struggles (0:45)

> Briefly, the same analysis from the selector's side. By size, it is best on the hundred-customer
> instances and weakest on the small ones — more geometric structure gives our features more to
> grab onto. By demand regime, high capacity pressure is clearly hardest — when vehicles are
> squeezed to the limit, solver behavior becomes hard to predict. And randomly placed depots are
> hardest by position, which fits the importance story we just saw: the model leans on depot
> geometry, and random placement is exactly where that signal is most variable.

*Transition: "So far, everything was in-distribution. Now the harder question."*

## Slide 14 — Does It Transfer to Real Benchmarks? (1:30)

> Every ML project must answer: does it generalize beyond its own data distribution? We evaluated
> the frozen selector — trained purely on synthetic instances — on **85 classic CVRPLIB
> instances** from sets A, B, E and P, re-running the whole portfolio under the same budget and
> anchoring against published proven optima.
>
> The honest answer: transfer is **partial**. The within-one-percent rate still clearly beats the
> baseline — 53 versus 43 percent, better on every set. But on mean regret the edge largely
> fades: 1.84 versus 1.88 percent — m-hat essentially one. The paper reports the same
> phenomenon on stylized benchmark families. Two silver linings: the portfolio itself is strong on
> real data — its best solver averages under two percent above proven optima — and on E-n51-k5
> the selector picks exactly the right heuristic, landing 0.19 percent above the optimum in a
> sixth of a second.

## Slide 15 — Extension: What Does 20 s of Compute Buy? (1:30)

> Final piece — an extension beyond the course requirements that puts everything in perspective.
> If we spent the entire twenty-second budget on one solver, what would that buy? We benchmarked
> PyVRP's **hybrid genetic search** on a stratified sample of 45 test instances plus the CVRPLIB
> benchmark.
>
> HGS wins or ties the portfolio oracle on **every single instance**, delivering on average
> **3.5 percent** shorter routes than the ML-selected heuristic — and it finds the proven optimum
> on E-n51-k5. But it consumes the full twenty seconds, while the ML-selected heuristic answers in
> a fifth of a second — roughly **ninety times** less compute.
>
> That's exactly why HGS is not in the portfolio: as a label it would swallow the dataset. As a
> reference, it prices the trade-off cleanly. Real-time answers or warm starts → use the
> selector. Twenty seconds per instance affordable → just run HGS. Different tools for different
> operational regimes.

## Slide 16 — Limitations and Takeaways (1:00)

> Let us state the limitations as plainly as the results. Trained on synthetic data — and on real
> benchmarks the regret advantage largely disappears; we showed you that rather than hiding it.
> Labels are the portfolio's best, not true optima. The budget bounds runtime but doesn't reward
> speed. The exact baseline is a deliberately simple formulation under a free license.
>
> Against that: per-instance selection genuinely beats the single-best-solver baseline
> in-distribution. Cheap pre-solution features — above all depot geometry and demand structure —
> carry real signal, and their importance ranking matches each heuristic's construction principle.
> Every number in this talk comes from frozen, integrity-checked artifacts anyone can re-run. And
> the speed-quality trade-off is *measured*, not asserted.

## Slide 17 — Conclusion (0:30)

> To conclude in one sentence: **look at the instance first, then pick the solver.** Thirty-eight
> engineered features — above all depot geometry and demand structure, whose importance matched
> each heuristic's construction principle — turn five sixty-year-old heuristics into a
> meta-solver that beats the standard baseline, transfers — partially and honestly measured — to
> real benchmarks, and sits at a well-understood point of the speed-quality spectrum. Exact where
> it proves, heuristic where it scales, learned where it chooses. Thank you — we're happy to take
> questions.

*(Slide 18 is a "Backup Slides" divider — end here; only go past it when a question calls for
the details on slides 19–21.)*

---

## Q&A Preparation (~10 minutes)

**Q: Did the feature importances match your expectations?** *(supervisor's favorite — own it)*
Partially, and the mismatches are the interesting part. We engineered features around three
hypotheses: demand structure, depot geometry, and size. Demand structure was confirmed (capacity
pressure and demand spread top the impurity ranking). Depot geometry was *stronger* than expected
— depot centrality plus the ring-occupancy profile are the top held-out predictors. And size,
the most obvious feature, turned out nearly irrelevant: all five heuristics scale fine at this
range, so shape separates them, not scale. The win-rate breakdowns confirm the mechanism:
each heuristic wins exactly where its construction principle fits (sweep needs angular spread,
route-first needs even demands, insertion handles tight capacity).

**Q: Accuracy is only 40% — isn't the model just bad?**
Five classes, and several solvers are often nearly tied in cost, so the *label* is almost
arbitrary between them while the *cost* difference is tiny. That's why we evaluate on regret and
within-1% rate — the quantities a dispatcher cares about. On those, the selector clearly beats
the baseline; and the Decision Tree (m̂ > 1) shows what a genuinely bad selector looks like.

**Q: Why keep the genetic algorithm out of the portfolio? Isn't that cherry-picking?**
The opposite — it keeps the learning problem meaningful. HGS wins or ties the oracle on 100% of
sampled instances at this budget; as a label class it would exceed our pipeline's 80% dominance
ceiling and leave nothing to select. The paper does the analogous thing: its portfolio uses HGS
only until the *first feasible solution*. We benchmark full-budget HGS separately and report the
trade-off (`reports/hgs_benchmark/`).

**Q: Does it generalize to real data?**
Partially, and we measured it rather than claiming it: on 85 CVRPLIB instances the within-1% rate
still beats SBS (52.9% vs 43.5%) and set B shows a real regret gain (m̂ = 0.85), but overall mean
regret is essentially tied (m̂ = 0.98). Consistent with the paper's own error analysis. The fix
would be training data that mimics benchmark structure.

**Q: Why train on synthetic data at all?**
Labelling requires running the *whole portfolio* on every instance — thousands of timed solver
runs. Synthetic generation gives unlimited labelled data with controlled variation, and it's the
protocol of the reference paper (train synthetic, test public benchmarks).

**Q: How do you prevent feature leakage?**
An explicit blocklist: solver costs, runtimes, feasibility flags, labels, seeds, and generator
category names are rejected by code (`feature_columns()` raises on prohibited columns), and the
notebook re-checks the saved feature manifest. Features are computable before any solver runs.

**Q: Were hyperparameters tuned?**
The frozen headline used fixed ones; we later ran the paper-style 5-fold grid search on the
training split as a supplement (backup slide 19). All CV accuracies land within ~1 point; tuned
test regrets straddle the frozen RF's. Fixed choices confirmed reasonable.

**Q: How does the exact model avoid subtours?**
MTZ-style load propagation: u_j ≥ u_i + q_j − Q(1−x_ij) forces load to increase along
customer-customer arcs, so any cycle must pass through the depot; the same constraint enforces
capacity (backup slide 20 has the full model).

**Q: Why is runtime not part of the objective?**
Scope decision: quality-within-budget is the label; runtime only breaks exact-cost ties. A
cost-runtime multi-objective label is the natural next step.

**Q: What's different from the paper?**
Portfolio (their 3 solvers incl. an ML-configured sweep + first-feasible HGS vs our 5 VeRyPy
classics), configuration (their regression configurator vs our discretized configs), test data
(their 264 CVRPLIB instances vs our synthetic test + 85-instance OOD supplement), and demands
(they convert to unit demands; we keep originals). Same framework and metrics.

**Q: Is any of this reproducible?**
Aggressively so: pinned VeRyPy commit, stable instance IDs, saved generation and split manifests,
label-integrity checks that re-derive every label from raw costs at load time, and documented
`uv run` commands for every experiment.

---

## Delivery Notes

- **Two presenters**: a natural handover point is after slide 9 (one of you owns problem + setup,
  the other owns results + extensions). Decide in advance who answers which Q&A themes
  (features/ML vs solvers/exact model).
- **Practice against the timer once**: ~20 min at a calm 140 wpm. If running long, compress
  slides 13 and 3 (say only the bolded sentences) — saves ~1.5 min. Do **not** cut slides 11–12;
  they carry the supervisor's requested emphasis.
- The narration is embedded in each slide's **speaker notes** — presenter view is enough; this
  file is for rehearsal.
- **Check the presentation machine**: this laptop has no PowerPoint/WPS installed, so the deck was
  validated programmatically but not visually rendered here. Open it once on the machine you'll
  present with. The deck uses the official TUM template (Arial, TUM-blue palette) — no special
  fonts needed.
- **Add your names** on the title slide (under the subtitle block).
- Numbers to know by heart: **63% vs 45%** (within-1%), **1.24% vs 1.67%** (regret),
  **m̂ = 0.741**, **40%** accuracy, **41% / 38% / 34%** (RFCS-even / CW-lumpy / MJ-tight demand
  wins), **52.9% vs 43.5%** (OOD), **+3.5% / 91×** (HGS), **20 s** budget, **1,260 / 85**
  instances.
