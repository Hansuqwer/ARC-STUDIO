from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChainOperator(str, Enum):
    ALWAYS = "always"
    AND = "&&"
    OR = "||"
    PIPE = "|"


@dataclass(frozen=True)
class ChainSegment:
    command: str
    operator_before: ChainOperator = ChainOperator.ALWAYS


def parse_command_chain(text: str) -> list[ChainSegment]:
    """Parse unquoted REPL command chains without invoking a shell."""
    source = text.strip()
    if not source:
        raise ValueError("empty command")
    segments: list[ChainSegment] = []
    current: list[str] = []
    quote: str | None = None
    escape = False
    pending = ChainOperator.ALWAYS
    index = 0
    while index < len(source):
        char = source[index]
        if escape:
            current.append(char)
            escape = False
            index += 1
            continue
        if char == "\\":
            current.append(char)
            escape = True
            index += 1
            continue
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            current.append(char)
            index += 1
            continue
        operator: ChainOperator | None = None
        if source.startswith("&&", index):
            operator = ChainOperator.AND
            step = 2
        elif source.startswith("||", index):
            operator = ChainOperator.OR
            step = 2
        elif char == "|":
            operator = ChainOperator.PIPE
            step = 1
        else:
            current.append(char)
            index += 1
            continue
        command = "".join(current).strip()
        if not command:
            raise ValueError("empty pipeline segment")
        segments.append(ChainSegment(command=command, operator_before=pending))
        current = []
        pending = operator
        index += step
    if quote:
        raise ValueError("unterminated quote")
    command = "".join(current).strip()
    if not command:
        raise ValueError("empty pipeline segment")
    segments.append(ChainSegment(command=command, operator_before=pending))
    return segments


def has_chain_operator(text: str) -> bool:
    try:
        return len(parse_command_chain(text)) > 1
    except ValueError:
        return any(token in text for token in ("&&", "||", "|"))
