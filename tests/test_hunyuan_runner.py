import subprocess
import sys
from pathlib import Path


def test_hunyuan_runner_help():
    result = subprocess.run(
        [sys.executable, "scripts/hunyuan3d_runner.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--repo-path" in result.stdout
    assert "--images" in result.stdout


def test_triposr_runner_help():
    result = subprocess.run(
        [sys.executable, "scripts/triposr_runner.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--repo-path" in result.stdout
    assert "--mc-resolution" in result.stdout
