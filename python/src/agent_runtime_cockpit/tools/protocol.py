"""Tool execution protocol per ADR-019."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import BaseModel

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken


@dataclass(frozen=True)
class ToolResult:
    """Result from tool execution.
    
    For mixed-level tools, content must be a dict and trust_overrides maps
    field names to their trust levels.
    """
    content: str | dict
    trust_overrides: dict[str, Literal["trusted", "untrusted"]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trust_overrides and not isinstance(self.content, dict):
            raise ValueError(
                "trust_overrides requires content to be a dict (mixed-level tool); "
                f"got {type(self.content).__name__}"
            )


class ToolHandler(Protocol):
    """Protocol for tool handlers per ADR-019.
    
    Every tool must declare output_trust_level:
    - "untrusted" (default): output is wrapped and scanned
    - "trusted": output bypasses scanner (high bar: no user-controlled component)
    - "mixed": structured output with per-field trust (deferred to Phase 7+)
    """
    name: str
    description: str
    output_trust_level: Literal["untrusted", "trusted", "mixed"]
    args_schema: type[BaseModel]
    output_byte_limit: int = 65536

    def execute(
        self,
        args: BaseModel,
        cancellation_token: CancellationToken,
    ) -> ToolResult:
        """Execute the tool with validated args.
        
        Raises:
            ValueError: invalid args
            Cancelled: cancellation requested
        """
        ...
