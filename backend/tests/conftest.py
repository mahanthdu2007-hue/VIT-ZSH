"""Test-wide setup: unit tests use the fast, offline KeywordBackend (slow tests build the real model)."""

import os

os.environ["SYSTEM1_BACKEND"] = "keyword"
