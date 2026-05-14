# Intentionally empty.
#
# A prior autouse fixture (close_pytest_asyncio_fallback_loop) was removed
# because pytest-asyncio >=0.23 in asyncio_mode = "auto" owns the event loop
# lifecycle and cleans it up itself. The fixture's call to
# asyncio.get_event_loop() emitted DeprecationWarning on Python 3.12 for
# synchronous tests (no loop on current thread), which became an error under
# -W error. See R-3 in the 2026-05-14 audit follow-up.

