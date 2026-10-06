import subprocess
import sys

import mocap_capture


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-c", "from mocap_capture.cli import main; main(['--version'])"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"mocap-capture {mocap_capture.__version__}"
