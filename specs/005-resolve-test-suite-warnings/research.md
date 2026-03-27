# Research — Spec 005: Resolve Test Suite Warnings

No project-specific external research was required beyond standard Python/pytest docs. All context was derived from:

- The existing test suite warning output (`agdt-test-pattern tests/ -W error`)
- Python documentation for `tarfile` filter parameter (PEP 706 / Python 3.12 changelog)
- pytest documentation for `filterwarnings` configuration and `pytest.warns()`
