"""Shared pytest setup.

- Tests never touch the real runs database or the network: RUNS_DB points at a temp file and LLM_MODE=mock.
- Windows only: the provided test_generated_data.py::test_deterministic leaves a SQLite connection open inside a
  TemporaryDirectory, and Windows refuses to delete an open file. The comparison itself is fine, so we let temp-dir
  cleanup ignore that one error instead of editing the provided test.
"""
import functools
import os
import sys
import tempfile

os.environ["RUNS_DB"] = os.path.join(tempfile.mkdtemp(prefix="emami-tests-"), "runs.sqlite")
os.environ["LLM_MODE"] = "mock"

if sys.platform == "win32":
    tempfile.TemporaryDirectory = functools.partial(tempfile.TemporaryDirectory, ignore_cleanup_errors=True)
