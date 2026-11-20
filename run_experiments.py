"""Compare core-selection policies on generated benchmarks.

Every result is checked against PySAT's RC2 solver, so a wrong optimum fails loudly.

    python run_experiments.py --seeds 10 --out results.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict

from pysat.examples.rc2 import RC2

from coresel import FAMILIES, POLICIES, CoreGuidedMSU3

SIZES = {
    "max3sat": dict(n_vars=40, n_soft=220, n_hard=20),
    "max2sat": dict(n_vars=30, n_soft=150),
    "setcover": dict(n_elements=30, n_sets=25),
}


def reference_cost(wcnf):
    with RC2(wcnf.copy()) as rc2:      # RC2 may modify the formula it is given
        rc2.compute()
        return rc2.cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--candidates", type=int, default=4)
    ap.add_argument("--trim", action="store_true")
    ap.add_argument("--policies", default="first,smallest,largest,random,llm")
    ap.add_argument("--out", default="results.csv")
    args = ap.parse_args()

    rows = []
    for fam, gen in FAMILIES.items():
        for seed in range(args.seeds):
            w = gen(seed=seed, **SIZES[fam])
            opt = reference_cost(w)
            for pname in args.policies.split(","):
                policy = POLICIES[pname]()
                st = CoreGuidedMSU3(w, policy, n_candidates=args.candidates,
                                    trim=args.trim, seed=seed).solve()
                assert st.cost == opt, f"{fam}/{seed}/{pname}: {st.cost} != {opt}"
                rows.append(dict(family=fam, seed=seed, policy=pname, optimum=opt,
                                 iterations=st.iterations, sat_calls=st.sat_calls,
                                 relaxed=st.relaxed, time_s=round(st.time_s, 4)))

    with open(args.out, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=rows[0].keys())
        wr.writeheader()
        wr.writerows(rows)

    agg = defaultdict(list)
    for r in rows:
        agg[(r["family"], r["policy"])].append(r)
    print(f"All {len(rows)} runs match the RC2 optimum.\n")
    print(f"{'family':<9} {'policy':<9} {'relaxed':>8} {'SAT calls':>10} {'time ms':>8}")
    for (fam, pol), rs in agg.items():
        print(f"{fam:<9} {pol:<9} "
              f"{statistics.mean(r['relaxed'] for r in rs):>8.1f} "
              f"{statistics.mean(r['sat_calls'] for r in rs):>10.1f} "
              f"{1000 * statistics.mean(r['time_s'] for r in rs):>8.1f}")


if __name__ == "__main__":
    main()
