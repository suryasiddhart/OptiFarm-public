"""Shared pytest configuration for the FarmApp backend.

`config.settings` builds Settings() at import time and requires DATABASE_URL
and SECRET_KEY. Test modules import `main`, so these must exist before pytest
collects anything. Dummy defaults let unit tests run without a database or
real secrets; values already set in the environment (e.g. the CI integration
job's DATABASE_URL) take precedence.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-not-used-outside-tests")
# Never load a developer's ../.env during tests
os.environ.setdefault("IN_CONTAINER", "true")
