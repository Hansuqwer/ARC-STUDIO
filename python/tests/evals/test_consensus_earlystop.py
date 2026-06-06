"""Tests for token-aware consensus early-stop (moonshot #2 first slice)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.evals.consensus_earlystop import (
    EARLY_STOP_SAFE_PROTOCOLS,
    EarlyStopDecision,
    can_stop_early,
    protocol_allows_early_stop,
    required_for_majority,
)


# ── required_for_majority ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "total,expected",
    [
        (1, 1),
        (2, 2),
        (3, 2),
        (4, 3),
        (5, 3),
        (6, 4),
        (7, 4),
    ],
)
def test_required_for_majority(total, expected):
    assert required_for_majority(total) == expected


# ── Settled PASS ──────────────────────────────────────────────────────────────


def test_settled_pass_majority():
    # 5 workers, required 3, 3 approved already → stop, 2 saved
    d = can_stop_early(approved=3, rejected=0, total=5)
    assert d.can_stop is True
    assert d.outcome == "settled_pass"
    assert d.workers_saved == 2


def test_settled_pass_exact_required():
    # required computed as 3; exactly 3 approvals
    d = can_stop_early(approved=3, rejected=1, total=5)
    assert d.can_stop is True
    assert d.outcome == "settled_pass"
    assert d.workers_saved == 1


def test_settled_pass_all_approve_early():
    d = can_stop_early(approved=2, rejected=0, total=3)  # required 2
    assert d.can_stop is True
    assert d.outcome == "settled_pass"


# ── Settled FAIL ──────────────────────────────────────────────────────────────


def test_settled_fail_majority():
    # 5 workers, required 3; 3 rejected → max reachable approvals = 2 < 3 → stop
    d = can_stop_early(approved=0, rejected=3, total=5)
    assert d.can_stop is True
    assert d.outcome == "settled_fail"
    assert d.workers_saved == 2


def test_settled_fail_mixed():
    # 5 workers, required 3; 1 approved + 3 rejected, 1 remaining
    # max reachable = 1 + 1 = 2 < 3 → fail
    d = can_stop_early(approved=1, rejected=3, total=5)
    assert d.can_stop is True
    assert d.outcome == "settled_fail"
    assert d.workers_saved == 1


# ── Undecided ─────────────────────────────────────────────────────────────────


def test_undecided_split():
    # 5 workers, required 3; 2 approved 1 rejected, 2 remaining → could still pass
    d = can_stop_early(approved=2, rejected=1, total=5)
    assert d.can_stop is False
    assert d.outcome == "undecided"
    assert d.workers_saved == 0


def test_undecided_first_vote():
    # 1 approval of 5, plenty remaining
    d = can_stop_early(approved=1, rejected=0, total=5)
    assert d.can_stop is False


# ── Custom required (quorum) ──────────────────────────────────────────────────


def test_custom_required_quorum_pass():
    # quorum of 2 out of 5
    d = can_stop_early(approved=2, rejected=0, total=5, required=2)
    assert d.can_stop is True
    assert d.outcome == "settled_pass"
    assert d.workers_saved == 3


def test_custom_required_unanimous():
    # required == total (unanimous); one rejection settles fail
    d = can_stop_early(approved=2, rejected=1, total=5, required=5)
    assert d.can_stop is True
    assert d.outcome == "settled_fail"


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_n_equals_1_pass():
    d = can_stop_early(approved=1, rejected=0, total=1)  # required 1
    assert d.can_stop is True
    assert d.outcome == "settled_pass"
    assert d.workers_saved == 0


def test_n_equals_1_fail():
    d = can_stop_early(approved=0, rejected=1, total=1)  # required 1, max reachable 0
    assert d.can_stop is True
    assert d.outcome == "settled_fail"


def test_zero_total_is_undecided():
    d = can_stop_early(approved=0, rejected=0, total=0)
    assert d.can_stop is False
    assert d.outcome == "undecided"


def test_voted_exceeds_total_fails_safe():
    d = can_stop_early(approved=5, rejected=5, total=5)  # 10 > 5 inconsistent
    assert d.can_stop is False
    assert d.outcome == "undecided"


def test_required_exceeds_total_fails_safe():
    d = can_stop_early(approved=1, rejected=0, total=3, required=4)
    assert d.can_stop is False


def test_negative_inputs_fail_safe():
    d = can_stop_early(approved=-1, rejected=0, total=5)
    assert d.can_stop is False
    assert d.outcome == "undecided"


def test_returns_early_stop_decision_type():
    assert isinstance(can_stop_early(approved=3, rejected=0, total=5), EarlyStopDecision)


# ── Protocol gating ───────────────────────────────────────────────────────────


def test_majority_and_quorum_allow_early_stop():
    assert protocol_allows_early_stop("majority") is True
    assert protocol_allows_early_stop("quorum") is True
    assert protocol_allows_early_stop("MAJORITY") is True  # case-insensitive


def test_bft_protocols_disallow_early_stop():
    for proto in ("bft", "bft_escrow", "raft"):
        assert protocol_allows_early_stop(proto) is False, f"{proto} must not early-stop"


def test_safe_protocols_set():
    assert EARLY_STOP_SAFE_PROTOCOLS == {"majority", "quorum"}


# ── Workers-saved fraction (token-saving evidence) ────────────────────────────


def test_workers_saved_fraction():
    """A 7-worker majority decided at vote 4 saves 3/7 of the worker cost."""
    d = can_stop_early(approved=4, rejected=0, total=7)  # required 4
    assert d.can_stop is True
    assert d.workers_saved == 3  # 7 - 4 voted
