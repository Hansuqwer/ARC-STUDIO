"""Heuristic prompt-injection pattern scanner."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class InjectionPattern(StrEnum):
    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_CONFUSION = "role_confusion"
    TOOL_HIJACKING = "tool_hijacking"
    EXFILTRATION = "exfiltration"
    JAILBREAK_ROLEPLAY = "jailbreak_roleplay"


class Severity(StrEnum):
    DEGRADED = "degraded"
    BLOCKED = "blocked"


SEVERITY: dict[InjectionPattern, Severity] = {
    InjectionPattern.INSTRUCTION_OVERRIDE: Severity.BLOCKED,
    InjectionPattern.ROLE_CONFUSION: Severity.BLOCKED,
    InjectionPattern.TOOL_HIJACKING: Severity.BLOCKED,
    InjectionPattern.EXFILTRATION: Severity.BLOCKED,
    InjectionPattern.JAILBREAK_ROLEPLAY: Severity.DEGRADED,
}


@dataclass(frozen=True)
class Detection:
    pattern: InjectionPattern
    severity: Severity
    matched_text: str
    confidence: float


def _compile(phrases: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(phrase, re.IGNORECASE) for phrase in phrases]


_PATTERNS: dict[InjectionPattern, list[re.Pattern[str]]] = {
    InjectionPattern.INSTRUCTION_OVERRIDE: _compile([
        r"ignore (?:all |any |the |your )?(?:previous |prior |above )?(?:instructions?|rules?|prompts?)",
        r"disregard (?:all|any|the|your|previous|prior|above) (?:instructions?|rules?)",
        r"forget (?:everything|all|your) (?:above|prior|previous|instructions?)",
        r"new instructions?:\s",
        r"the (?:real|actual|true|new) (?:instructions?|task) (?:are|is)",
        r"<\s*system\s*>",
        r"</\s*untrusted_input\s*>",
    ]),
    InjectionPattern.ROLE_CONFUSION: _compile([
        r"you are (?:now|actually) (?:a|an) ",
        r"you(?:'re| are) no longer (?:a|an|the) ",
        r"pretend (?:to be|you(?:'re| are)) ",
        r"act as (?:if you(?:'re| are)|a|an) ",
        r"from now on,? you ",
        r"switch to (?:the )?(?:role|persona|mode) of ",
    ]),
    InjectionPattern.TOOL_HIJACKING: _compile([
        r"call (?:the )?(?:function|tool) ",
        r"execute (?:the )?(?:following|this) (?:command|code|script)",
        r"run (?:the )?(?:following|this) (?:shell|bash|python|javascript)",
        r"<tool_use>",
        r"```(?:tool|function)_call",
        r"invoke[_\s](?:tool|function|api)\(",
    ]),
    InjectionPattern.EXFILTRATION: _compile([
        r"send (?:the |your )?(?:secrets?|api[_\s]?keys?|passwords?|credentials?) to",
        r"post (?:the |your )?(?:contents?|history|data) to",
        r"upload (?:everything|the (?:history|conversation|context))",
        r"include (?:the |your )?(?:system prompt|hidden instructions?) in (?:your|the) (?:reply|response)",
        r"print (?:your |the )?(?:system prompt|hidden instructions?|api[_\s]?keys?)",
        r"what (?:are |is )?(?:your |the )?(?:original |initial |hidden )?(?:system prompt|instructions?)",
    ]),
    InjectionPattern.JAILBREAK_ROLEPLAY: _compile([
        r"\bDAN\b",
        r"developer mode",
        r"unrestricted (?:mode|version|model)",
        r"no (?:ethical |moral |safety )?(?:guidelines?|constraints?|restrictions?)",
        r"hypothetically,? (?:if you|imagine|suppose)",
        r"in a (?:fictional|hypothetical|alternate) (?:world|universe|scenario)",
    ]),
}


def scan(text: str) -> list[Detection]:
    if not text:
        return []
    detections: list[Detection] = []
    for pattern, regexes in _PATTERNS.items():
        for regex in regexes:
            match = regex.search(text)
            if match:
                detections.append(Detection(pattern, SEVERITY[pattern], match.group(0), 1.0))
    return detections


def highest_severity(detections: list[Detection]) -> Severity | None:
    if not detections:
        return None
    if any(detection.severity is Severity.BLOCKED for detection in detections):
        return Severity.BLOCKED
    return Severity.DEGRADED
