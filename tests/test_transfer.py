import hashlib
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path, PurePosixPath

import pytest

from mocap_capture import transfer
from mocap_capture.config import Handoff
from mocap_capture.transfer import (
    PARTIAL_DIR,
    LocalTarget,
    SshTarget,
    TransferError,
    rsync_cmd,
    send_file,
)

pytestmark = pytest.mark.skipif(shutil.which("rsync") is None, reason="needs rsync")


@pytest.fixture
def take_dir(tmp_path) -> Path:
    take_dir = tmp_path / "recorder" / "S1" / "takes" / "T1"
    (take_dir / "raw").mkdir(parents=True)
    (take_dir / "raw" / "body_1.timestamps.csv").write_text("frame,host_ts_ns\n0,1\n")
    return take_dir


@pytest.fixture
def target(tmp_path) -> LocalTarget:
    root = tmp_path / "processing"
    root.mkdir()
    return LocalTarget(root)


def arrived_path(target, rel):
    return target.root / "S1" / "takes" / "T1" / rel


def test_file_arrives_in_the_same_layout_path(take_dir, target):
    got = send_file(take_dir, "raw/body_1.timestamps.csv", target)
    dest = arrived_path(target, "raw/body_1.timestamps.csv")
    assert dest.read_bytes() == (take_dir / "raw" / "body_1.timestamps.csv").read_bytes()
    assert got.size_bytes == dest.stat().st_size
    assert got.sha256 == hashlib.sha256(dest.read_bytes()).hexdigest()


def test_sidecar_follows_its_file(take_dir, target):
    (take_dir / "raw" / "body_1.timestamps.csv.ready.json").write_text("{}\n")
    send_file(take_dir, "raw/body_1.timestamps.csv", target)
    assert arrived_path(target, "raw/body_1.timestamps.csv.ready.json").read_text() == "{}\n"


def test_sidecar_can_be_held_back(take_dir, target):
    (take_dir / "raw" / "body_1.timestamps.csv.ready.json").write_text("{}\n")
    send_file(take_dir, "raw/body_1.timestamps.csv", target, with_sidecar=False)
    assert not arrived_path(target, "raw/body_1.timestamps.csv.ready.json").exists()


def test_rerun_after_success_copies_nothing(take_dir, target):
    send_file(take_dir, "raw/body_1.timestamps.csv", target)
    dest = arrived_path(target, "raw/body_1.timestamps.csv")
    before = dest.stat().st_ino
    send_file(take_dir, "raw/body_1.timestamps.csv", target)
    assert dest.stat().st_ino == before  # rsync replaces a file it copies; this one was left alone


def test_interrupted_transfer_is_never_visible_and_resumes(take_dir, target):
    video = take_dir / "raw" / "body_1.mkv"
    video.write_bytes(os.urandom(4 * 1024 * 1024))
    rel = PurePosixPath("S1/takes/T1/raw/body_1.mkv")
    cmd = rsync_cmd(video, rel, target)
    cmd.insert(1, "--bwlimit=1000")  # ~1 MB/s, so it's still running when we look
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dest = target.root / rel
    deadline = time.monotonic() + 1.5
    while time.monotonic() < deadline:
        assert not dest.exists(), "a half-copied file is visible under its real name"
        time.sleep(0.05)
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=10)
    assert not dest.exists()
    partial = dest.parent / PARTIAL_DIR / dest.name
    assert 0 < partial.stat().st_size < video.stat().st_size  # what arrived is kept

    got = send_file(take_dir, "raw/body_1.mkv", target)
    assert dest.read_bytes() == video.read_bytes()
    assert got.sha256 == hashlib.sha256(video.read_bytes()).hexdigest()
    assert not partial.exists()


def test_arrival_that_differs_is_an_error(take_dir, target, monkeypatch):
    monkeypatch.setattr(LocalTarget, "measure", lambda self, rel: transfer.Arrived(1, "0" * 64))
    with pytest.raises(TransferError, match="arrived as"):
        send_file(take_dir, "raw/body_1.timestamps.csv", target)


@pytest.mark.parametrize("rel", ["../../etc/passwd", "/etc/passwd", ""])
def test_paths_outside_the_take_are_refused(take_dir, target, rel):
    with pytest.raises(TransferError):
        send_file(take_dir, rel, target)


def test_not_a_take_folder(tmp_path, target):
    (tmp_path / "x").write_text("x")
    with pytest.raises(TransferError, match="not a take folder"):
        send_file(tmp_path, "x", target)


def test_missing_file(take_dir, target):
    with pytest.raises(TransferError, match="is not a file"):
        send_file(take_dir, "raw/nope.mkv", target)


def test_ssh_target_commands(monkeypatch):
    target = SshTarget.from_config(Handoff(
        host="192.168.0.10", take_closed_port=5600, file_ready_port=5601,
        ssh_user="rafael", data_root=PurePosixPath("/data/mocap"),
    ))
    rel = PurePosixPath("S1/takes/T1/prep/body 1.mkv")
    cmd = rsync_cmd(Path("/rec/S1/takes/T1/prep/body 1.mkv"), rel, target)
    assert cmd[-1] == "rafael@192.168.0.10:/data/mocap/S1/takes/T1/prep/body 1.mkv"
    assert cmd[cmd.index("-e") + 1] == "ssh -o BatchMode=yes"
    seen = []
    monkeypatch.setattr(transfer, "_run", lambda c: seen.append(c) or "12\nabc  /x y\n")
    assert target.measure(rel) == transfer.Arrived(12, "abc")
    assert seen[0][-2] == "rafael@192.168.0.10"
    assert "'/data/mocap/S1/takes/T1/prep/body 1.mkv'" in seen[0][-1]
