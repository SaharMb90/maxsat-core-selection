# Core selection in core-guided MaxSAT

A small, tested research prototype that asks one question:
**when a core-guided MaxSAT solver can choose between several unsatisfiable cores, does the choice change how hard the solve is, and can a learned or LLM-based policy make that choice?**

Core-guided solvers turn MaxSAT into a sequence of SAT calls. Each UNSAT answer returns a core, and the solver relaxes it. The optimum does not depend on which cores are relaxed, but the *sequence* of cores sets the size of the cardinality constraints and so the cost of later SAT calls. This prototype makes that choice explicit and pluggable.

## What it does

- `coresel/solver.py` implements an MSU3-style core-guided solver for unweighted partial MaxSAT on top of PySAT (Glucose 4 oracle, iterative totalizer encoding).
- At every UNSAT step it extracts up to *k* candidate cores by re-ordering the assumptions, optionally trims each one (deletion-based minimisation), and hands them to a **policy**.
- `coresel/policies.py` provides five policies:
  - `first`: take the core the SAT solver returns first (the usual behaviour)
  - `smallest`: take the core with the fewest soft clauses
  - `largest`: a deliberately poor baseline
  - `random`: pick one at random
  - `llm`: describe each core by a few features (size, distinct variables, mean variable occurrence) and ask an LLM to pick one. Without an `ANTHROPIC_API_KEY` it falls back to a transparent feature rule (smallest core, ties broken by variable occurrence), so every run is reproducible.
- `coresel/instances.py` generates three reproducible families: partial random Max-3-SAT with a satisfiable hard part, random Max-2-SAT, and minimum set cover.
- Every result is checked against PySAT's RC2 solver. A wrong optimum fails the run.

## Results

10 instances per family, 4 candidate cores per step, no trimming (`python run_experiments.py --seeds 10`). All 150 runs matched the RC2 optimum.

| Family | Policy | Soft clauses relaxed | Time (ms) |
|---|---|---|---|
| Max-2-SAT | first | 147.3 | 127.4 |
| Max-2-SAT | smallest | 143.7 | 66.9 |
| Max-2-SAT | largest | 147.8 | 193.3 |
| Max-2-SAT | random | 147.3 | 173.2 |
| Max-2-SAT | llm (offline fallback rule) | 143.8 | 47.8 |
| Max-3-SAT | first | 214.3 | 94.2 |
| Max-3-SAT | smallest | 212.9 | 98.7 |
| Set cover | first | 22.9 | 1.1 |
| Set cover | smallest | 22.4 | 1.0 |

What this shows, and what it does not:

- On Max-2-SAT, preferring small cores roughly halves solve time compared with the default first core, and the deliberately poor `largest` policy is about 3x slower than `smallest`. So the core sequence does matter.
- On these random Max-3-SAT and set-cover instances the effect is small: the cores are large and similar, so there is little to choose between.
- The `llm` row here uses the offline fallback rule, not a live model. Running with an API key tests whether an LLM adds anything beyond that rule; I have not yet run that comparison.
- The instances are small and generated. The next step is the MaxSAT Evaluation benchmarks and a stronger base algorithm (OLL / RC2-style) where core choice interacts with stratification and weights.

Full per-run results are in `results.csv` (and `results_trim.csv` with `--trim`).

## Run it

```bash
pip install -r requirements.txt
python -m pytest -q                       # 32 tests, compare every policy with RC2
python run_experiments.py --seeds 10      # prints the summary table, writes results.csv
python run_experiments.py --seeds 10 --trim
export ANTHROPIC_API_KEY=...              # optional: use a live LLM for the llm policy
python run_experiments.py --policies first,smallest,llm
```

## Why I built this

This is a first step towards the research question of selecting effective core sequences in core-guided MaxSAT, and towards using language models to guide solver decisions. It is meant to show that I can implement, test and measure solver behaviour, not to claim new results.

Author: Sahar Mirzabaki · [GitHub](https://github.com/SaharMb90) · [LinkedIn](https://www.linkedin.com/in/sahar-mirzabaki)
