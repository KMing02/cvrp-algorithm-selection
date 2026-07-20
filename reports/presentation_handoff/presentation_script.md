# Presentation Script — "Learning Which VRP Solver Works Best"

Companion to `presentation.pptx` (17 talk slides + a backup divider + 3 backup slides, built on
the official TUM template `2111_Praesentationsvorlage_16-9.potx`). Every slide's narration is
also embedded in the deck's speaker notes, word for word. Written for **two presenters** ("we"
throughout) — a natural split point is after slide 9 (setup → results).

Per our supervisor's feedback, the features get the most weight: slide 8 states the three
feature-engineering guesses, slide 11 checks them against the observed importance, and slide 12
connects instance characteristics to individual solver behavior.

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
| 8 | 38 features — three guesses | 1:30 | 9:30 |
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

> Good morning everyone. Today we're going to show you our project, "Learning which VRP solver
> works best". In one sentence: instead of picking one heuristic for the vehicle routing problem
> and hoping it works, we trained a machine-learning model that first looks at the instance, and
> then predicts which of five classical heuristics will solve it best within a fixed time budget.
> We follow a 2024 paper by Asín-Achá and colleagues, scaled down to a student project. We'll
> start with the problem, then go through our pipeline, and then the results. We'll spend extra
> time on the features we built and what they tell us about how these solvers behave. And at the
> end, there's an honest test on real benchmarks and a speed-versus-quality comparison.

*Transition: "Let's set up the problem first."*

## Slide 2 — The Problem: CVRP (1:15)

> In the capacitated vehicle routing problem, we have a depot with a fleet of identical vehicles,
> and each vehicle can carry at most Q. Every customer needs a certain amount and has to be
> visited exactly once. Each route starts and ends at the depot, and the customers on one route
> can't need more than the vehicle can carry. The goal: make the total driving distance as short
> as possible. The picture on the right shows what a solution looks like: the square is the
> depot, and each colored loop is one vehicle's route.
>
> The problem is NP-hard — you have to decide at the same time how to *group* customers and in
> what *order* to visit them. And in real logistics you often need an answer in seconds. So the
> problem is hard, but the answer has to come fast — that tension drives this whole project.

*Transition: "So what happens if we just try to solve it exactly?"*

## Slide 3 — Exact Solving Hits a Wall (1:15)

> The first task in the project was to introduce the problem by solving instances exactly with
> gurobipy, and with heuristics. We wrote the CVRP as a mixed-integer program — a two-index
> formulation where load variables grow along each route. That trick removes subtours and
> enforces capacity at the same time.
>
> And the results are pretty humbling. With **six customers**, Gurobi proves the optimum in a
> hundredth of a second, and all five heuristics find the same solution. With **twenty
> customers**, Gurobi runs for five full minutes and still can't *prove* it's optimal — up to a
> two percent gap stays open. The heuristics get the same or almost the same answer in under four
> hundredths of a second. And with **fifty-one customers**, the model doesn't even fit into the
> free license anymore.
>
> So exact solving gives us reliable reference points on small instances, but the real work has
> to be done by fast heuristics. Which brings up the question: *which one?*

## Slide 4 — No Single Heuristic Wins (1:15)

> Here's the fact that motivates everything. We ran five classical heuristics on all 1,260
> instances in our dataset and asked: which one is best on each instance? The answer: **it
> depends**. Route-first-cluster-second wins about a quarter of the time. Clarke-Wright another
> quarter. Mole-Jameson about a fifth. Even the weakest one still wins almost one instance in
> ten. So no solver dominates. And if you pick the wrong one, it can cost you up to **nineteen
> percent** extra driving distance. Which solver wins depends on how the instance looks — the
> geometry, where the depot is, how the demands are spread.
>
> And this is exactly what the algorithm-selection literature says: don't pick one solver for
> everything — learn a model that predicts the winner for *each* instance. That's the approach
> of the paper we follow.

*Transition: "Here's our solution as a pipeline."*

## Slide 5 — The Solution: A Learned Meta-Solver (1:15)

> A new instance comes in. We compute thirty-eight cheap features — statistics you can get
> before doing any solving. A trained Random Forest looks at them and predicts which heuristic
> will win. We run only that one, and we get routes back in about a fifth of a second on average.
>
> Four design choices matter here. First, every solver runs under the same fixed **twenty-second
> budget**. So the training label really means "best solution within the budget", and if two
> solvers tie on cost, the faster one wins. Second, no leakage: features only use information
> that's available before solving, and a blocklist in the code enforces that. Third, different
> settings of the same heuristic just become separate entries in the portfolio — that's the
> simplified version of what the paper calls algorithm configuration. And fourth, if the
> predicted solver ever fails, we fall back to the single best solver. So the meta-solver always
> returns something.

## Slide 6 — The Portfolio (1:00)

> Here's the portfolio: five classical construction heuristics from the VeRyPy library. They
> cover the classic families — savings, sweep, insertion, two-phase clustering, and
> route-first-cluster-second. We pinned the library to one fixed commit, and every solution that
> comes back gets re-checked and re-costed by our own code, so no library quirk can sneak into
> the labels.
>
> Two things are missing on purpose. Gaskell's savings variant won only 3 out of 240 instances in
> our audit — you can't learn a class from three examples. And there's no genetic algorithm in
> here. That's not an oversight: a modern hybrid genetic search would win almost every instance
> at this budget, the labels would collapse into one class, and there'd be nothing left to learn.
> We benchmark it separately instead — we'll show you at the end exactly what it buys.

## Slide 7 — 1,260 Synthetic Instances (1:15)

> Where does the training data come from? Like the paper, we generate it ourselves, and the goal
> is to cover as much variety as possible. It's a balanced grid: five spatial patterns — from
> uniform scatter to tight clusters to rings — times three depot positions, times four demand
> types, times three sizes, times seven random seeds. That's 1,260 instances and 6,300 timed
> solver runs. Exactly one run ever went over the budget.
>
> Each instance gets labelled with the solver that found the cheapest feasible solution within 20
> seconds. Then we split: 1,008 for training, 252 for testing, stratified by label, with no
> overlap. And it's all reproducible — every instance can be regenerated from a stable ID, and
> the generation settings are saved right next to the results.

## Slide 8 — 38 Features: Three Guesses (1:30)

> So what does the model actually see? Thirty-eight features in five groups, all computable in
> milliseconds. We built them around **three guesses** about what drives solver performance.
> Guess one: **demand structure** — how big the demands are, how uneven they are, and how tightly
> they fill the fleet. We capture that with capacity pressure and demand statistics. Guess two:
> **depot geometry** — how central the depot sits, plus the paper's signature feature, ring
> occupancy: the share of customers in five rings around the depot. Guess three: **overall
> customer layout and instance size**.
>
> Just as important is what the model does *not* see. Solver results, labels, seeds, generator
> categories — all blocked. The code throws an error if a forbidden column shows up. So the model
> learns instance characteristics, not leaked answers. Were our three guesses right? That's what
> the next two slides check.

## Slide 9 — How We Measure a Selector (1:00)

> Before the results, thirty seconds on how you measure a selector, because the field has two
> standard baselines. The **Single Best Solver**, SBS, is the one solver that's best on average
> on the training data — for us that's Mole-Jameson insertion. That's what you'd use without any
> machine learning, so that's the bar to beat. The **Virtual Best Solver**, VBS, is an oracle
> that picks the true winner on every single instance. Perfect selection — that's the ceiling.
>
> The paper's metric m-hat tells you where a selector sits between the two: zero means you pick
> like the oracle, one means you're no better than the baseline. Our selector lands at **0.741**
> — let's unpack that now. We also report regret — how many percent the chosen solver's route is
> above the best possible — and how often we land within one percent of it.

## Slide 10 — Main Result (1:45)

> Here's the main result. We trained four model families, plus dummy classifiers as sanity
> checks. Random Forest came out on top — same as in the paper. The chart shows how often the
> chosen solver lands within one percent of the best possible result. The no-ML baseline: 45
> percent of instances. Random Forest: **63 percent**. Mean regret drops from 1.67 to 1.24
> percent. On the m-hat scale that's 0.741 — the selector closes about a quarter of the gap
> between baseline and oracle.
>
> Now you might say: only **40 percent accuracy** over five classes? Yes — and that's fine.
> Often several solvers are almost tied, so picking the "wrong" one barely costs anything. What
> counts is route quality, not the label. One nice detail: the plain Decision Tree has m-hat
> *above one*. A weak selector is actually worse than no selector — learning has to earn its
> place.

*Transition: "So the model works. But the more interesting question — the one our supervisor
asked us to focus on — is WHY: which features carry the prediction?"*

## Slide 11 — Feature Importance: Expected vs Observed (1:30)

> Now the question our supervisor found most interesting — and honestly, so do we: which
> features actually carried the prediction, and did that match what we expected? Permutation
> importance on held-out data gives a clear answer, and our three guesses came out three
> different ways.
>
> Guess one, **demand structure: confirmed**. Capacity pressure and demand spread are at the top
> of the tree-based ranking. Guess two, **depot geometry: confirmed, and stronger than we
> thought** — depot centrality is the single strongest held-out feature, with two ring shares
> right behind it. And guess three is the **surprise: raw instance size**, the most obvious
> feature of all, **barely matters**. It never makes the top ten. Looking back, that makes sense:
> all five heuristics handle a hundred customers just fine. What separates them is the *shape* of
> the instance, not its size.
>
> One caveat we always attach here: importance is about prediction, not causation. But we can go
> one step deeper and link characteristics to individual solvers — next slide.

## Slide 12 — Which Characteristics Favor Which Solver? (1:15)

> Let's make that concrete — for us this is the best result in the project. The demand type is
> the strongest signal. When demands are even, **route-first-cluster-second wins forty-one
> percent** of the instances. Makes sense: if everyone needs about the same, cutting one big tour
> into routes works cleanly. Flip to lumpy, high-variance demands, and **Clarke-Wright with
> 2-opt takes over at thirty-eight percent** — its greedy merges deal well with uneven demands.
> When capacity is tight, **Mole-Jameson insertion leads** — it checks feasibility at every step,
> and that pays off when the vehicles run full.
>
> Geometry tells the same kind of story. With a central depot or ring-shaped layouts, the
> **Wren-Holliday sweep peaks** — it cuts customers by angle around the depot, so it needs
> angular spread. Put the depot in a corner, and sweep fades while insertion takes over.
>
> So each heuristic wins exactly where its construction idea fits. That's the signal the Random
> Forest picks up — the features, not the fancy model, are the heart of this project.

## Slide 13 — Where It Works and Where It Struggles (0:45)

> Quickly, the same thing from the selector's point of view. By size: it does best on the
> hundred-customer instances and worst on the small ones — more structure gives our features
> more to work with. By demand type: tight capacity is the hardest case — when vehicles are full
> to the brim, solver behavior gets hard to predict. And random depot positions are the hardest —
> which fits what we just saw: the model leans on depot geometry, and random placement is where
> that signal moves around the most.

*Transition: "So far, everything was on our own data. Now the harder question."*

## Slide 14 — Does It Transfer to Real Benchmarks? (1:30)

> Now the question every ML project has to face: does it work outside its own data? We took the
> frozen selector — trained only on synthetic data — and tested it on **85 classic CVRPLIB
> benchmark instances**, sets A, B, E and P. Same budget, and we compared against the published
> optima.
>
> The honest answer: it transfers **partly**. The within-one-percent rate still clearly beats the
> baseline — 53 versus 43 percent, and better on every set, as the chart shows. But on mean
> regret, the edge mostly disappears: 1.84 versus 1.88 percent, m-hat basically one. The paper
> saw the same thing — these stylized benchmark families are hard if you trained on random
> synthetic data.
>
> Two good notes, though. The portfolio itself holds up on real data: its best solver is on
> average under two percent above the proven optima. And on E-n51-k5, the selector picks exactly
> the right heuristic — 0.19 percent above the optimum, in a sixth of a second.

## Slide 15 — Extension: What Does 20 s of Compute Buy? (1:30)

> Last piece — an extension beyond the course requirements that puts everything in perspective.
> What if we spent the whole twenty-second budget on a single solver? We benchmarked PyVRP's
> **hybrid genetic search** on a stratified sample of 45 test instances, plus the benchmark.
>
> The result: HGS wins or ties our portfolio's oracle on **every single instance**. On average
> its routes are **3.5 percent** shorter than the ML-selected heuristic's, and it even finds the
> proven optimum on E-n51-k5. But it uses the full twenty seconds — while our ML-selected
> heuristic answers in a fifth of a second. That's about **ninety times** less compute.
>
> And that's exactly why HGS is not in the portfolio: as a label it would swallow the whole
> dataset. As a reference, it prices the trade-off nicely. Need answers in real time, or starting
> points for a bigger optimizer? Use the selector. Can you afford twenty seconds per instance?
> Just run HGS. Different tools for different situations.

## Slide 16 — Limitations and Takeaways (1:00)

> Let's be as plain about the limitations as about the results. We trained on synthetic data, and
> on real benchmarks the regret advantage mostly disappears — we showed you that instead of
> hiding it. Our labels are the portfolio's best, not true optima — though that best is only
> about two percent above the proven optima on real instances. The budget caps runtime but
> doesn't reward speed. And the exact baseline is a deliberately simple formulation on a free
> license.
>
> On the plus side: per-instance selection really does beat the single-best-solver baseline on
> our data. Cheap pre-solve features carry real signal — above all depot geometry and demand
> structure — and the importance ranking matches how the heuristics are built. Every number in
> this talk comes from frozen, integrity-checked results anyone can re-run. And the speed-quality
> trade-off is measured, not just claimed.

## Slide 17 — Conclusion (0:30)

> So, in one sentence: **look at the instance first, then pick the solver.** Thirty-eight
> engineered features — mainly depot geometry and demand structure, whose importance matched how
> each heuristic is built — turn five sixty-year-old heuristics into a meta-solver that beats
> the standard baseline, transfers partly — and honestly measured — to real benchmarks, and sits
> at a clear point on the speed-quality spectrum: a fifth of a second for routes within about
> three and a half percent of what a modern genetic search gets with ninety times the compute.
> Exact where it proves, heuristic where it scales, learned where it chooses. Thank you — we're
> happy to take questions.

*(Slide 18 is a "Backup Slides" divider — end here; only go past it when a question calls for
the details on slides 19–21.)*

---

## Q&A Preparation (~10 minutes)

**Q: Did the feature importances match your expectations?** *(supervisor's favorite — own it)*
Partly — and the mismatches are the interesting part. We built the features around three
guesses: demand structure, depot geometry, and size. Demand structure was confirmed — capacity
pressure and demand spread top the tree-based ranking. Depot geometry came out *stronger* than
expected — depot centrality plus the ring shares are the top held-out predictors. And size, the
most obvious feature, turned out to barely matter: all five heuristics handle these sizes fine,
so it's the shape that separates them, not the scale. The win-rate breakdowns back this up: each
heuristic wins exactly where its construction idea fits — sweep needs angular spread,
route-first needs even demands, insertion handles tight capacity.

**Q: Accuracy is only 40% — isn't the model just bad?**
Five classes, and several solvers are often nearly tied on cost. So the *label* is almost a coin
flip between them, while the *cost* difference is tiny. That's why we measure regret and the
within-1% rate — the numbers a dispatcher actually cares about. On those, the selector clearly
beats the baseline. And the Decision Tree (m̂ > 1) shows what a genuinely bad selector looks
like.

**Q: Why keep the genetic algorithm out of the portfolio? Isn't that cherry-picking?**
The opposite — it's what keeps the learning problem meaningful. HGS wins or ties the oracle on
100% of sampled instances at this budget. As a label class it would blow past our 80% dominance
limit and there'd be nothing left to select. The paper does the same kind of thing: it only uses
HGS up to the *first feasible solution*, not the full budget. We benchmark full-budget HGS
separately and report the trade-off (`reports/hgs_benchmark/`).

**Q: Does it generalize to real data?**
Partly — and we measured it instead of claiming it. On 85 CVRPLIB instances the within-1% rate
still beats SBS (52.9% vs 43.5%), and set B shows a real regret gain (m̂ = 0.85). But overall
mean regret is basically tied (m̂ = 0.98). That matches the paper's own error analysis. The fix
would be training data that looks more like the benchmarks.

**Q: Why train on synthetic data at all?**
Because labelling means running the *whole portfolio* on every instance — thousands of timed
solver runs. Synthetic generation gives us unlimited labelled data with controlled variety. And
it's the protocol of the reference paper: train synthetic, test on public benchmarks.

**Q: How do you prevent feature leakage?**
With an explicit blocklist: solver costs, runtimes, feasibility flags, labels, seeds, and
generator category names are rejected by code — `feature_columns()` raises an error on
prohibited columns — and the notebook re-checks the saved feature list. All features can be
computed before any solver runs.

**Q: Were hyperparameters tuned?**
The frozen headline used fixed ones. We later ran the paper-style 5-fold grid search on the
training split as a supplement (backup slide 19). All CV accuracies land within about one point,
and tuned test regrets sit right around the frozen Random Forest's. So the fixed choices were
fine.

**Q: How does the exact model avoid subtours?**
Through the load variables: u_j ≥ u_i + q_j − Q(1−x_ij) forces the load to grow along
customer-to-customer arcs, so any cycle has to pass through the depot. The same constraint
enforces capacity. Backup slide 20 has the full model.

**Q: Why is runtime not part of the objective?**
Scope decision: the label is quality within the budget; runtime only breaks exact-cost ties. A
combined cost-runtime label is the natural next step.

**Q: What's different from the paper?**
The portfolio (their 3 solvers, including an ML-configured sweep and first-feasible HGS, versus
our 5 VeRyPy classics), the configuration (their regression configurator versus our discretized
configs), the test data (their 264 CVRPLIB instances versus our synthetic test plus an
85-instance benchmark supplement), and the demands (they convert to unit demands; we keep the
originals). Same framework and same metrics.

**Q: Is any of this reproducible?**
Very much so: pinned VeRyPy commit, stable instance IDs, saved generation and split manifests,
integrity checks that re-derive every label from raw costs at load time, and documented
`uv run` commands for every experiment.

---

## Delivery Notes

- **Two presenters**: a natural handover point is after slide 9 (one of you owns problem +
  setup, the other owns results + extensions). Decide in advance who answers which Q&A themes
  (features/ML vs solvers/exact model).
- **Practice against the timer once**: ~20 min at a calm 140 wpm. If running long, compress
  slides 3 and 13 (say only the bolded sentences) — saves ~1.5 min. Do **not** cut slides 11–12;
  they carry the supervisor's requested emphasis.
- The narration is embedded word for word in each slide's **speaker notes** — presenter view is
  enough; this file is for rehearsal.
- **Check the presentation machine**: this laptop has no PowerPoint/WPS installed, so the deck
  was validated programmatically but not visually rendered here. Open it once on the machine
  you'll present with. The deck uses the official TUM template (Arial, TUM-blue palette) — no
  special fonts needed.
- **Add your names** on the title slide (under the subtitle block).
- Numbers to know by heart: **63% vs 45%** (within-1%), **1.24% vs 1.67%** (regret),
  **m̂ = 0.741**, **40%** accuracy, **41% / 38% / 34%** (RFCS-even / CW-lumpy / MJ-tight demand
  wins), **52.9% vs 43.5%** (OOD), **+3.5% / 91×** (HGS), **20 s** budget, **1,260 / 85**
  instances.
