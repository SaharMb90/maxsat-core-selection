"""Reproducible unweighted partial MaxSAT instance generators."""
from __future__ import annotations

import random

from pysat.formula import WCNF


def random_partial_max3sat(n_vars=40, n_soft=200, n_hard=20, seed=0) -> WCNF:
    """Over-constrained random 3-clauses as soft clauses, plus hard 3-clauses
    satisfied by a planted assignment (so the hard part is always SAT)."""
    rng = random.Random(seed)
    planted = {v: rng.choice([True, False]) for v in range(1, n_vars + 1)}

    def clause():
        vs = rng.sample(range(1, n_vars + 1), 3)
        return [v if rng.random() < 0.5 else -v for v in vs]

    w = WCNF()
    added = 0
    while added < n_hard:
        cl = clause()
        if any((l > 0) == planted[abs(l)] for l in cl):
            w.append(cl)
            added += 1
    for _ in range(n_soft):
        w.append(clause(), weight=1)
    return w


def random_max2sat(n_vars=30, n_soft=150, seed=0) -> WCNF:
    rng = random.Random(seed)
    w = WCNF()
    for _ in range(n_soft):
        vs = rng.sample(range(1, n_vars + 1), 2)
        w.append([v if rng.random() < 0.5 else -v for v in vs], weight=1)
    return w


def set_cover(n_elements=30, n_sets=25, seed=0) -> WCNF:
    """Minimum set cover: every element covered (hard), each chosen set costs 1 (soft)."""
    rng = random.Random(seed)
    sets = [set(rng.sample(range(n_elements), rng.randint(3, 7))) for _ in range(n_sets)]
    for e in range(n_elements):              # make sure the instance is feasible
        if not any(e in s for s in sets):
            rng.choice(sets).add(e)
    w = WCNF()
    for e in range(n_elements):
        w.append([j + 1 for j, s in enumerate(sets) if e in s])
    for j in range(n_sets):
        w.append([-(j + 1)], weight=1)
    return w


FAMILIES = {
    "max3sat": random_partial_max3sat,
    "max2sat": random_max2sat,
    "setcover": set_cover,
}
