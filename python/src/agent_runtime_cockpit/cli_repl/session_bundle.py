from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent_runtime_cockpit.security.redaction import Redactor
from agent_runtime_cockpit.storage.atomic import write_text_atomic

from .session import SESSION_SCHEMA_VERSION, ChatSession, _get_sessions_dir, is_safe_session_id

SESSION_BUNDLE_SCHEMA = "arc.session.bundle"
SESSION_BUNDLE_VERSION = 1
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY)",
    re.IGNORECASE,
)


class SessionBundleRedaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applied: bool = True
    placeholder: str = "[REDACTED]"
    policy: str = "agent_runtime_cockpit.security.redaction.Redactor"


class SessionBundleIntegrity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_sha256: str


class SessionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    schema_: Literal["arc.session.bundle"] = Field(default=SESSION_BUNDLE_SCHEMA, alias="schema")
    schema_version: Literal[1] = SESSION_BUNDLE_VERSION
    session_schema_version: int = SESSION_SCHEMA_VERSION
    exported_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    redaction: SessionBundleRedaction = Field(default_factory=SessionBundleRedaction)
    session: dict[str, Any]
    integrity: SessionBundleIntegrity


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(data: Any) -> str:
    return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()


def _redacted_session_dict(session: ChatSession) -> dict[str, Any]:
    data = session.model_dump(mode="json")
    return Redactor().redact_dict(data)


def export_session_bundle(session: ChatSession) -> SessionBundle:
    redacted = _redacted_session_dict(session)
    return SessionBundle(
        session_schema_version=SESSION_SCHEMA_VERSION,
        session=redacted,
        integrity=SessionBundleIntegrity(content_sha256=_sha256(redacted)),
    )


def validate_session_bundle(data: Any) -> SessionBundle:
    bundle = SessionBundle.model_validate(data)
    if bundle.session_schema_version > SESSION_SCHEMA_VERSION:
        raise ValueError("unsupported future session schema version")
    if bundle.integrity.content_sha256 != _sha256(bundle.session):
        raise ValueError("session bundle integrity mismatch")
    if _contains_secret(bundle.model_dump(mode="json")):
        raise ValueError("session bundle contains secret-looking data")
    session = ChatSession.model_validate(bundle.session)
    if not is_safe_session_id(session.id):
        raise ValueError("unsafe session id")
    return bundle


def load_session_bundle(path: Path) -> SessionBundle:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return validate_session_bundle(data)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise ValueError(f"invalid session bundle: {exc}") from exc


def write_session_bundle(path: Path, bundle: SessionBundle) -> None:
    write_text_atomic(path, bundle.model_dump_json(indent=2) + "\n")


def import_session_bundle(
    path: Path, *, new_id: bool = False, overwrite: bool = False
) -> ChatSession:
    bundle = load_session_bundle(path)
    session = ChatSession.model_validate(bundle.session)
    if new_id:
        session.id = f"s-{uuid.uuid4().hex[:12]}"
    target = _get_sessions_dir() / session.id / "session.json"
    if target.exists() and not overwrite:
        raise ValueError(f"session already exists: {session.id}")
    session.save()
    return session


def _contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_secret(k) or _contains_secret(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    if isinstance(value, str):
        return bool(SECRET_RE.search(value))
    return False
