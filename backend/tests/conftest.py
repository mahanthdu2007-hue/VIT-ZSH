"""Test-wide setup: unit tests use the fast, offline KeywordBackend (slow tests build the real model),
a throwaway SQLite database, DEMO_MODE off and no LLM."""

import os
import tempfile
from pathlib import Path

os.environ["SYSTEM1_BACKEND"] = "keyword"
os.environ["DATABASE_URL"] = f"sqlite:///{(Path(tempfile.mkdtemp()) / 'test.db').as_posix()}"
os.environ["DEMO_MODE"] = "0"
os.environ["LLM_PROVIDER"] = "none"  # tests never call a real LLM; providers are tested with mocked clients
