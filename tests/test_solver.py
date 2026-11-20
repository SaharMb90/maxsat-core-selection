import pytest
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF

from coresel import FAMILIES, POLICIES, CoreGuidedMSU3


def rc2_cost(w):
    with RC2(w.copy()) as s:
        s.compute()
        return s.cost


@pytest.mark.parametrize("family", list(FAMILIES))
@pytest.mark.parametrize("policy", list(POLICIES))
@pytest.mark.parametrize("trim", [False, True])
def test_matches_rc2(family, policy, trim):
    for seed in range(3):
        w = FAMILIES[family](seed=seed)
        st = CoreGuidedMSU3(w, POLICIES[policy](), trim=trim, seed=seed).solve()
        assert st.cost == rc2_cost(w)


def test_trivial_sat():
    w = WCNF()
    w.append([1, 2])
    w.append([1], weight=1)
    assert CoreGuidedMSU3(w, POLICIES["first"]()).solve().cost == 0


def test_hard_unsat_raises():
    w = WCNF()
    w.append([1])
    w.append([-1])
    w.append([2], weight=1)
    with pytest.raises(Exception):
        CoreGuidedMSU3(w, POLICIES["first"]()).solve()
