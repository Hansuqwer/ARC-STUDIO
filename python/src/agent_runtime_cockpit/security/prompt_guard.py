"""prompt_guard.py — deterministic regex-based prompt injection detection (R-SEC2).

Research-grade guard: no LLM judgment; purely deterministic regex patterns.
Scans a prompt for known injection-pattern families and returns a severity score.

Severity:
  blocked   — high-confidence injection attempt (ignore-instructions, role-switch)
  degraded  — suspicious but ambiguous (instruction-like imperative, jailbreak preamble)
  clean     — no patterns detected

This module is intentionally conservative: false negatives are acceptable;
false positives should be minimized for developer productivity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Pattern families ──────────────────────────────────────────────────────────

_BLOCKED_PATTERNS: list[re.Pattern] = [
    # Direct instruction-override attempts
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you|i)\s+(know|said|told)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+\w+", re.IGNORECASE),
    re.compile(r"(act|pretend|roleplay)\s+as\s+(if\s+)?(you\s+are|a|an|the)\s+\w+", re.IGNORECASE),
    re.compile(
        r"your\s+(new|real|true)\s+(instructions?|purpose|goal|role|system)\s+(is|are)",
        re.IGNORECASE,
    ),
    re.compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re.compile(r"</?(system|human|assistant|prompt)>", re.IGNORECASE),
    re.compile(r"\[\s*INST\s*\]|\[/?SYS\]", re.IGNORECASE),
]

_DEGRADED_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"do\s+not\s+follow\s+(your|the)\s+(guidelines?|rules?|instructions?)", re.IGNORECASE
    ),
    re.compile(
        r"(bypass|override|circumvent|disable)\s+(the\s+)?(safety|filter|restrict|guard)",
        re.IGNORECASE,
    ),
    re.compile(r"DAN\b|do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(
        r"(answer|respond|reply)\s+without\s+(any\s+)?(restrict|filter|censor|limit)", re.IGNORECASE
    ),
]


@dataclass(frozen=True)
class GuardResult:
    severity: str  # "blocked" | "degraded" | "clean"
    matched_patterns: list[str] = field(default_factory=list)
    is_safe: bool = True


def scan(prompt: str) -> GuardResult:
    """Scan a prompt for injection patterns. Returns a GuardResult."""
    matches: list[str] = []

    for pattern in _BLOCKED_PATTERNS:
        m = pattern.search(prompt)
        if m:
            matches.append(f"blocked:{pattern.pattern[:40]}")

    if matches:
        return GuardResult(severity="blocked", matched_patterns=matches, is_safe=False)

    for pattern in _DEGRADED_PATTERNS:
        m = pattern.search(prompt)
        if m:
            matches.append(f"degraded:{pattern.pattern[:40]}")

    if matches:
        return GuardResult(severity="degraded", matched_patterns=matches, is_safe=False)

    return GuardResult(severity="clean", is_safe=True)


def highest_severity(results: list[GuardResult]) -> str:
    """Return the highest severity across multiple scan results."""
    if any(r.severity == "blocked" for r in results):
        return "blocked"
    if any(r.severity == "degraded" for r in results):
        return "degraded"
    return "clean"
