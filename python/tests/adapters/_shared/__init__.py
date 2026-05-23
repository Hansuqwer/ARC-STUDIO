"""Shared adapter test harness (Phase 25.5).

This module is the contract surface every adapter phase consumes. New
helpers require an ADR; signature changes to existing helpers require
an ADR.
"""

from ._typed_run_event_conformance import (
    TypedRunEventConformance,
    assert_event_stream_conforms,
)
from ._fake_provider_fixture import FakeProviderFixture
from ._fixture_project_loader import FixtureProjectLoader
from ._golden_file_compare import GoldenFileCompare
from ._denial_event_assertions import (
    DenialEventAssertions,
    assert_denial_event,
)

__all__ = [
    "TypedRunEventConformance",
    "assert_event_stream_conforms",
    "FakeProviderFixture",
    "FixtureProjectLoader",
    "GoldenFileCompare",
    "DenialEventAssertions",
    "assert_denial_event",
]
