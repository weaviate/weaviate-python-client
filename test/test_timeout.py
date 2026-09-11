"""Tests for the custom per-test timeout mechanism in conftest.py.

Uses subprocess because the timeout mechanism calls os._exit(1).
"""

import subprocess
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _run_pytest(tmp_path: Path, test_code: str, *extra_args: str) -> subprocess.CompletedProcess:
    """Run pytest in a subprocess with a copy of our timeout conftest."""
    (tmp_path / "conftest.py").write_text((PROJECT_ROOT / "conftest.py").read_text())
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\naddopts = --capture=sys --max-worker-restart=0\nmarkers =\n    timeout: custom timeout\n"
    )
    (tmp_path / "test_it.py").write_text(textwrap.dedent(test_code))
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-n",
            "auto",
            "--dist",
            "loadgroup",
            "test_it.py",
            *extra_args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
    )


def test_timeout_prints_test_name_and_stacktrace(tmp_path: Path) -> None:
    result = _run_pytest(
        tmp_path,
        """\
        import time
        import pytest

        @pytest.mark.timeout(2)
        def test_hangs():
            time.sleep(999)
        """,
    )
    assert result.returncode != 0
    assert "TIMEOUT: test_it.py::test_hangs exceeded 2.0s" in result.stderr
    assert "test_hangs" in result.stderr


def test_fast_test_not_killed(tmp_path: Path) -> None:
    result = _run_pytest(
        tmp_path,
        """\
        import pytest

        @pytest.mark.timeout(10)
        def test_fast():
            assert True
        """,
    )
    assert result.returncode == 0
    assert "TIMEOUT" not in result.stderr


def test_timeout_with_passing_and_hanging_test(tmp_path: Path) -> None:
    result = _run_pytest(
        tmp_path,
        """\
        import time
        import pytest

        @pytest.mark.timeout(2)
        def test_hangs_in_worker():
            time.sleep(999)

        def test_passes():
            assert True
        """,
    )
    assert result.returncode != 0
    assert "TIMEOUT: test_it.py::test_hangs_in_worker exceeded 2.0s" in result.stderr
    assert "test_hangs_in_worker" in result.stderr
