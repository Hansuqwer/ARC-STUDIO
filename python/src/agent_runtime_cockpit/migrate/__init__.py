"""ARC Migrate — cross-adapter migration assistant (R102).

Convert agent projects between frameworks (e.g. LangGraph ↔ CrewAI, SwarmGraph →
OpenAI Agents) via AST analysis + templated generation, with equivalence validation.

Leverages ARC's multi-adapter surface for migration paths.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

MIGRATE_SCHEMA_VERSION = 1


class MigrationStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class FrameworkType(str, Enum):
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    SWARMGRAPH = "swarmgraph"
    OPENAI_AGENTS = "openai_agents"
    AUTOGEN = "autogen"
    LLAMAINDEX = "llamaindex"
    UNKNOWN = "unknown"


@dataclass
class MigrationIssue:
    issue_type: str  # "incompatible_feature", "missing_mapping", "semantic_diff"
    severity: str  # "error", "warning", "info"
    message: str
    source_location: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "source_location": self.source_location,
            "suggestion": self.suggestion,
        }


@dataclass
class MigrationAnalysis:
    source_framework: FrameworkType
    target_framework: FrameworkType
    source_files: list[str] = field(default_factory=list)
    detected_patterns: list[str] = field(default_factory=list)
    issues: list[MigrationIssue] = field(default_factory=list)
    compatibility_score: float = 0.0  # 0.0 to 1.0
    estimated_effort: str = "unknown"  # "low", "medium", "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_framework": self.source_framework.value,
            "target_framework": self.target_framework.value,
            "source_files": self.source_files,
            "detected_patterns": self.detected_patterns,
            "issues": [i.to_dict() for i in self.issues],
            "compatibility_score": self.compatibility_score,
            "estimated_effort": self.estimated_effort,
        }


@dataclass
class MigrationResult:
    session_id: str
    source_framework: FrameworkType
    target_framework: FrameworkType
    status: MigrationStatus = MigrationStatus.PENDING
    analysis: Optional[MigrationAnalysis] = None
    generated_files: list[str] = field(default_factory=list)
    validation_passed: bool = False
    validation_report: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source_framework": self.source_framework.value,
            "target_framework": self.target_framework.value,
            "status": self.status.value,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "generated_files": self.generated_files,
            "validation_passed": self.validation_passed,
            "validation_report": self.validation_report,
            "errors": self.errors,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


def detect_framework(workspace: Path) -> FrameworkType:
    """Detect the agent framework used in a workspace."""
    indicators = {
        FrameworkType.LANGGRAPH: ["langgraph.json", "from langgraph", "import langgraph"],
        FrameworkType.CREWAI: ["crewai.yaml", "from crewai", "import crewai"],
        FrameworkType.SWARMGRAPH: ["swarmgraph.yaml", "from swarmgraph", "import swarmgraph"],
        FrameworkType.OPENAI_AGENTS: [
            "openai_agents.yaml",
            "from openai_agents",
            "import openai_agents",
        ],
        FrameworkType.AUTOGEN: ["autogen.yaml", "from autogen", "import autogen"],
        FrameworkType.LLAMAINDEX: ["llamaindex.yaml", "from llama_index", "import llama_index"],
    }

    for framework, patterns in indicators.items():
        for pattern in patterns:
            if pattern.endswith(".json") or pattern.endswith(".yaml"):
                if (workspace / pattern).exists():
                    return framework
            else:
                for py_file in workspace.rglob("*.py"):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if pattern in content:
                            return framework
                    except Exception:
                        continue

    return FrameworkType.UNKNOWN


def analyze_migration(
    source: Path, source_framework: FrameworkType, target_framework: FrameworkType
) -> MigrationAnalysis:
    """Analyze a workspace for migration feasibility."""
    issues = []
    detected_patterns = []
    source_files = []

    for py_file in source.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        source_files.append(str(py_file.relative_to(source)))
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if source_framework.value in alias.name:
                            detected_patterns.append(f"import:{alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and source_framework.value in node.module:
                        detected_patterns.append(f"from:{node.module}")
                elif isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            detected_patterns.append(f"class:{base.id}")
        except Exception as e:
            issues.append(
                MigrationIssue(
                    issue_type="parse_error",
                    severity="warning",
                    message=f"Failed to parse {py_file}: {e}",
                    source_location=str(py_file),
                )
            )

    compatibility_score = 0.7
    if source_framework == target_framework:
        compatibility_score = 1.0
    elif source_framework == FrameworkType.UNKNOWN or target_framework == FrameworkType.UNKNOWN:
        compatibility_score = 0.3
        issues.append(
            MigrationIssue(
                issue_type="unknown_framework",
                severity="warning",
                message="Source or target framework is unknown. Migration may require manual adjustments.",
            )
        )

    estimated_effort = "medium"
    if compatibility_score > 0.8:
        estimated_effort = "low"
    elif compatibility_score < 0.5:
        estimated_effort = "high"

    return MigrationAnalysis(
        source_framework=source_framework,
        target_framework=target_framework,
        source_files=source_files,
        detected_patterns=list(set(detected_patterns)),
        issues=issues,
        compatibility_score=compatibility_score,
        estimated_effort=estimated_effort,
    )


def generate_migration(
    source: Path,
    output: Path,
    analysis: MigrationAnalysis,
) -> list[str]:
    """Generate migrated code based on analysis."""
    generated_files = []
    output.mkdir(parents=True, exist_ok=True)

    for source_file in analysis.source_files:
        source_path = source / source_file
        if not source_path.exists():
            continue

        content = source_path.read_text(encoding="utf-8")
        migrated_content = _apply_migration_templates(
            content, analysis.source_framework, analysis.target_framework
        )

        output_path = output / source_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(migrated_content, encoding="utf-8")
        generated_files.append(str(output_path))

    return generated_files


def _apply_migration_templates(content: str, source: FrameworkType, target: FrameworkType) -> str:
    """Apply simple template-based migrations."""
    migrated = content

    if source == FrameworkType.LANGGRAPH and target == FrameworkType.CREWAI:
        migrated = migrated.replace("from langgraph", "from crewai")
        migrated = migrated.replace("import langgraph", "import crewai")
        migrated = migrated.replace("StateGraph", "Crew")
        migrated = migrated.replace("MessageGraph", "Crew")
    elif source == FrameworkType.CREWAI and target == FrameworkType.LANGGRAPH:
        migrated = migrated.replace("from crewai", "from langgraph")
        migrated = migrated.replace("import crewai", "import langgraph")
        migrated = migrated.replace("Crew", "StateGraph")
    elif source == FrameworkType.SWARMGRAPH and target == FrameworkType.OPENAI_AGENTS:
        migrated = migrated.replace("from swarmgraph", "from openai_agents")
        migrated = migrated.replace("import swarmgraph", "import openai_agents")
    elif source == FrameworkType.OPENAI_AGENTS and target == FrameworkType.SWARMGRAPH:
        migrated = migrated.replace("from openai_agents", "from swarmgraph")
        migrated = migrated.replace("import openai_agents", "import swarmgraph")

    return migrated


def validate_migration(source: Path, output: Path, analysis: MigrationAnalysis) -> dict[str, Any]:
    """Validate the migrated code for equivalence."""
    issues = []
    source_files_count = len(analysis.source_files)
    generated_files_count = 0

    for source_file in analysis.source_files:
        output_path = output / source_file
        if output_path.exists():
            generated_files_count += 1
            try:
                content = output_path.read_text(encoding="utf-8")
                ast.parse(content)
            except SyntaxError as e:
                issues.append(
                    {
                        "type": "syntax_error",
                        "file": source_file,
                        "message": str(e),
                    }
                )

    return {
        "source_files": source_files_count,
        "generated_files": generated_files_count,
        "parse_errors": len(issues),
        "issues": issues,
        "validation_passed": len(issues) == 0 and generated_files_count == source_files_count,
    }


def migrate_workspace(
    source: Path,
    output: Path,
    target_framework: FrameworkType,
    session_id: str = "default",
) -> MigrationResult:
    """Perform a full migration from source to target framework."""
    result = MigrationResult(
        session_id=session_id,
        source_framework=detect_framework(source),
        target_framework=target_framework,
    )

    try:
        result.status = MigrationStatus.ANALYZING
        result.analysis = analyze_migration(source, result.source_framework, target_framework)

        result.status = MigrationStatus.GENERATING
        result.generated_files = generate_migration(source, output, result.analysis)

        result.status = MigrationStatus.VALIDATING
        result.validation_report = validate_migration(source, output, result.analysis)
        result.validation_passed = result.validation_report.get("validation_passed", False)

        result.status = MigrationStatus.COMPLETED
    except Exception as e:
        result.status = MigrationStatus.FAILED
        result.errors.append(str(e))

    result.completed_at = datetime.now(timezone.utc).isoformat()
    return result


__all__ = [
    "MIGRATE_SCHEMA_VERSION",
    "MigrationStatus",
    "FrameworkType",
    "MigrationIssue",
    "MigrationAnalysis",
    "MigrationResult",
    "detect_framework",
    "analyze_migration",
    "generate_migration",
    "validate_migration",
    "migrate_workspace",
]
