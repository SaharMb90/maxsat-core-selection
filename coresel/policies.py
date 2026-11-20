"""Core-selection policies. Each policy returns the index of the candidate to relax."""
from __future__ import annotations

import json
import os
import random
import re
from collections import Counter


class FirstCore:
    name = "first"

    def choose(self, cands, wcnf, relaxed):
        return 0


class SmallestCore:
    name = "smallest"

    def choose(self, cands, wcnf, relaxed):
        return min(range(len(cands)), key=lambda i: len(cands[i].soft_ids))


class LargestCore:
    """Deliberately bad baseline, to show that the choice matters."""
    name = "largest"

    def choose(self, cands, wcnf, relaxed):
        return max(range(len(cands)), key=lambda i: len(cands[i].soft_ids))


class RandomCore:
    name = "random"

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def choose(self, cands, wcnf, relaxed):
        return self.rng.randrange(len(cands))


def core_features(cands, wcnf, relaxed):
    """Small, solver-agnostic description of each candidate core."""
    var_freq = Counter(abs(l) for cl in wcnf.soft for l in cl)
    feats = []
    for c in cands:
        clauses = [wcnf.soft[i] for i in c.soft_ids]
        vars_ = {abs(l) for cl in clauses for l in cl}
        feats.append({
            "size": len(c.soft_ids),
            "uses_bound": c.uses_bound,
            "distinct_vars": len(vars_),
            "mean_var_occurrence": round(
                sum(var_freq[v] for v in vars_) / max(len(vars_), 1), 2),
        })
    return feats


class LLMCore:
    """Asks a large language model to pick a core from a feature summary.

    Set ANTHROPIC_API_KEY to call the model (default model: claude-sonnet-4-5,
    override with CORESEL_LLM_MODEL). Without a key, or if the call fails, it
    falls back to a transparent feature-based rule so runs stay reproducible.
    """
    name = "llm"

    PROMPT = (
        "You are guiding a core-guided MaxSAT solver (MSU3). At each step one "
        "unsatisfiable core is relaxed, adding its soft clauses to a cardinality "
        "constraint. Smaller cores usually keep that constraint small, but cores "
        "over frequently occurring variables can resolve more conflicts at once.\n"
        "Iteration: {it}. Soft clauses already relaxed: {nrel}.\n"
        "Candidate cores (JSON):\n{feats}\n"
        "Reply with only the index of the core to relax."
    )

    def __init__(self, model=None):
        self.model = model or os.environ.get("CORESEL_LLM_MODEL", "claude-sonnet-4-5")
        self.client = None
        self.calls = 0
        self.fallbacks = 0
        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                self.client = anthropic.Anthropic()
            except Exception:
                self.client = None

    def _fallback(self, feats):
        self.fallbacks += 1
        return min(range(len(feats)), key=lambda i: (
            feats[i]["size"], -feats[i]["mean_var_occurrence"]))

    def choose(self, cands, wcnf, relaxed):
        if len(cands) == 1:
            return 0
        feats = core_features(cands, wcnf, relaxed)
        if self.client is None:
            return self._fallback(feats)
        prompt = self.PROMPT.format(
            it=len(relaxed), nrel=len(relaxed),
            feats=json.dumps(list(enumerate(feats))))
        try:
            self.calls += 1
            msg = self.client.messages.create(
                model=self.model, max_tokens=10,
                messages=[{"role": "user", "content": prompt}])
            m = re.search(r"\d+", msg.content[0].text)
            idx = int(m.group()) if m else -1
            return idx if 0 <= idx < len(cands) else self._fallback(feats)
        except Exception:
            return self._fallback(feats)


POLICIES = {
    "first": FirstCore,
    "smallest": SmallestCore,
    "largest": LargestCore,
    "random": RandomCore,
    "llm": LLMCore,
}
