"""Core-guided MaxSAT (MSU3-style, unweighted partial MaxSAT) with pluggable core selection.

At every UNSAT step the solver extracts several candidate unsatisfiable cores
(by re-ordering the assumptions), optionally trims them, and lets a *policy*
decide which core to relax. The optimum is the same for every policy; what
changes is the sequence of cores and therefore the cost of reaching it.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

from pysat.card import ITotalizer
from pysat.formula import WCNF
from pysat.solvers import Solver


@dataclass
class Candidate:
    soft_ids: frozenset          # indices of soft clauses in the core
    uses_bound: bool             # whether the cardinality bound took part


@dataclass
class SolveStats:
    cost: int | None = None
    model: list | None = None
    iterations: int = 0
    sat_calls: int = 0
    relaxed: int = 0
    time_s: float = 0.0
    core_sizes: list = field(default_factory=list)


class CoreGuidedMSU3:
    def __init__(self, wcnf: WCNF, policy, n_candidates: int = 4,
                 trim: bool = False, solver_name: str = "g4", seed: int = 0):
        if any(w != 1 for w in wcnf.wght):
            raise ValueError("this demo handles unweighted partial MaxSAT only")
        wcnf = wcnf.copy()               # never touch the caller's formula
        self.wcnf = wcnf
        self.policy = policy
        self.n_candidates = n_candidates
        self.trim = trim
        self.rng = random.Random(seed)
        self.stats = SolveStats()

        self.top = wcnf.nv
        self.oracle = Solver(name=solver_name, bootstrap_with=wcnf.hard)
        # selector a_i: when assumed true, soft clause i must hold
        self.sel = []
        for cl in wcnf.soft:
            self.top += 1
            self.sel.append(self.top)
            self.oracle.add_clause(cl + [-self.top])
        self.lit2soft = {a: i for i, a in enumerate(self.sel)}

    # ----------------------------------------------------------------- helpers
    def _call(self, assumptions):
        self.stats.sat_calls += 1
        return self.oracle.solve(assumptions=assumptions)

    def _candidates(self, soft_assumps, bound_assumps):
        seen, cands = set(), []
        for t in range(self.n_candidates):
            order = list(soft_assumps)
            if t > 0:
                self.rng.shuffle(order)
            if self._call(bound_assumps + order):
                return None                       # cannot happen after first UNSAT
            core = set(self.oracle.get_core() or [])
            ids = frozenset(self.lit2soft[l] for l in core if l in self.lit2soft)
            if self.trim and len(ids) > 1:
                ids = self._trim(ids, bound_assumps)
            if ids and ids not in seen:
                seen.add(ids)
                cands.append(Candidate(ids, any(l in core for l in bound_assumps)))
        return cands

    def _trim(self, ids, bound_assumps):
        """One pass of deletion-based core minimisation."""
        ids = set(ids)
        for i in sorted(ids):
            if len(ids) == 1:
                break
            trial = [self.sel[j] for j in ids if j != i]
            if not self._call(bound_assumps + trial):
                ids.discard(i)
        return frozenset(ids)

    # -------------------------------------------------------------------- main
    def solve(self) -> SolveStats:
        t0 = time.perf_counter()
        relaxed: list[int] = []
        k, tot = 0, None
        while True:
            soft_assumps = [a for i, a in enumerate(self.sel) if i not in relaxed]
            bound = [-tot.rhs[k]] if tot is not None and k < len(relaxed) else []
            if self._call(bound + soft_assumps):
                model = self.oracle.get_model()
                self.stats.model = model[: self.wcnf.nv]
                self.stats.cost = sum(
                    1 for cl in self.wcnf.soft
                    if not any(model[abs(l) - 1] == l for l in cl))
                break
            cands = self._candidates(soft_assumps, bound)
            if not cands:
                if not bound:
                    raise RuntimeError("hard clauses are unsatisfiable")
                cands = [Candidate(frozenset(), True)]
            choice = cands[self.policy.choose(cands, self.wcnf, relaxed)]
            self.stats.core_sizes.append(len(choice.soft_ids))
            relaxed.extend(sorted(choice.soft_ids))
            k += 1
            self.stats.iterations += 1
            if tot is not None:
                tot.delete()
            tot = ITotalizer(lits=[-self.sel[i] for i in relaxed], ubound=k + 1,
                             top_id=self.top)
            self.top = tot.top_id
            self.oracle.append_formula(tot.cnf.clauses)
        self.stats.relaxed = len(relaxed)
        self.stats.time_s = time.perf_counter() - t0
        self.oracle.delete()
        return self.stats
