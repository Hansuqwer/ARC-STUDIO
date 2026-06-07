"""Advisory compliance artifact generators for ARC Mobile Runtime.

All generated artifacts are ADVISORY ONLY and require human review
before any app-store submission. These generators do not provide legal
advice and do not guarantee app-store approval.
"""

from .ios import generate_privacy_manifest, generate_usage_strings
from .android import generate_manifest_permissions, generate_data_safety_notes
from .review_notes import generate_review_notes
from .report import generate_compliance_report

__all__ = [
    "generate_privacy_manifest",
    "generate_usage_strings",
    "generate_manifest_permissions",
    "generate_data_safety_notes",
    "generate_review_notes",
    "generate_compliance_report",
]
