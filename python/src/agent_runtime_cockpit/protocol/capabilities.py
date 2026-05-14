"""ARC runtime capability model."""
from pydantic import BaseModel, Field


class RuntimeCapabilities(BaseModel):
    """Honest self-report of what this adapter supports."""
    # Inspection / export
    can_inspect: bool = False
    can_run: bool = False
    can_export_schema: bool = False
    can_export_workflow: bool = False

    # Observability
    can_trace: bool = False
    can_replay: bool = False
    can_stream_events: bool = False
    can_audit: bool = False

    # Advanced execution (Runtime Contract v2)
    can_checkpoint: bool = False
    can_resume: bool = False
    can_fork: bool = False
    can_diff: bool = False
    can_eval: bool = False

    # Permission requirements (reported by adapter, enforced by gating)
    requires_paid_calls: bool = False
    requires_network: bool = Field(default=False, description="Runtime needs external network access")
    requires_shell: bool = Field(default=False, description="Runtime spawns subprocesses")
    requires_secrets: bool = Field(default=False, description="Runtime needs API keys or tokens")
