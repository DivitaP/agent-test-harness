"""Test-only compatibility fixtures for the local Anaconda environment."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from types import SimpleNamespace

import pytest


@pytest.fixture
def capsys():
    """Capture stdout/stderr without importing pytest's crashing readline hook."""
    stdout = StringIO()
    stderr = StringIO()

    with redirect_stdout(stdout), redirect_stderr(stderr):
        yield SimpleNamespace(
            readouterr=lambda: SimpleNamespace(
                out=stdout.getvalue(), err=stderr.getvalue()
            )
        )
