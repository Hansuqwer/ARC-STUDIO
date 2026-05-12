"""ARC runtime capability model."""
from pydantic import BaseModel


class RuntimeCapabilities(BaseModel):
    can_inspect: bool = False
    can_run: bool = False
    can_trace: bool = False
    can_replay: bool = False
    can_export_schema: bool = False
    can_export_workflow: bool = False
    can_stream_events: bool = False
    can_audit: bool = False
