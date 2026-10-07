"""Per-file transfer to the processing PC: rsync over SSH, into the same layout path.

    <recorder storage.root>/<session>/takes/<take>/<rel_path>
      → <handoff.data_root>/<session>/takes/<take>/<rel_path> on handoff.host

rsync writes into a hidden temporary name and renames when the file is
complete, so nothing half-copied is ever visible under its real name. An
interrupted copy keeps what arrived in `.rsync-partial/` and the next run
resumes from it. Sizes and modification times are preserved, so a rerun after
a success copies nothing.

`send_file` returns the size and sha256 measured on the receiving side, which
is what the file's `CameraFileReady` announces.
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from mocap_contracts import layout

from mocap_capture.config import Handoff

PARTIAL_DIR = ".rsync-partial"
ERROR_LINES = 5
SSH = ["ssh", "-o", "BatchMode=yes"]  # never prompt: a missing key is an error


class TransferError(RuntimeError):
    """A file that didn't arrive intact."""


@dataclass(frozen=True)
class Arrived:
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class SshTarget:
    """The processing PC, as `config.yaml` `handoff:` declares it."""

    user: str
    host: str
    root: PurePosixPath

    @classmethod
    def from_config(cls, handoff: Handoff) -> SshTarget:
        return cls(user=handoff.ssh_user, host=handoff.host, root=handoff.data_root)

    def rsync_dest(self, rel: PurePosixPath) -> str:
        return f"{self.user}@{self.host}:{self.root / rel}"

    def rsync_shell(self) -> list[str]:
        return ["-e", shlex.join(SSH)]

    def measure(self, rel: PurePosixPath) -> Arrived:
        path = shlex.quote(str(self.root / rel))
        result = _run([*SSH, f"{self.user}@{self.host}", f"stat -c %s -- {path} && sha256sum -- {path}"])
        lines = result.splitlines()  # "<size>" then "<sha256>  <path>"
        return Arrived(int(lines[0]), lines[1].split()[0])


@dataclass(frozen=True)
class LocalTarget:
    """A data root on this machine (tests, or a recorder that is also the processing PC)."""

    root: Path

    def rsync_dest(self, rel: PurePosixPath) -> str:
        return str(self.root / rel)

    def rsync_shell(self) -> list[str]:
        return []

    def measure(self, rel: PurePosixPath) -> Arrived:
        path = self.root / rel
        return Arrived(path.stat().st_size, _sha256(path))


def send_file(
    take_dir: Path, rel_path: str, target: SshTarget | LocalTarget, *, with_sidecar: bool = True
) -> Arrived:
    """Copy one file of a take (then its `.ready.json` sidecar, if it has one)."""
    rel = _remote_rel(take_dir, rel_path)
    source = take_dir / rel_path
    if not source.is_file():
        raise TransferError(f"{source} is not a file")
    _rsync(source, rel, target)
    arrived = target.measure(rel)
    local = Arrived(source.stat().st_size, _sha256(source))
    if arrived != local:
        raise TransferError(f"{rel_path} arrived as {arrived}, sent {local}")
    sidecar = layout.ready_sidecar(source)
    if with_sidecar and sidecar.is_file():
        _rsync(sidecar, _remote_rel(take_dir, f"{rel_path}.ready.json"), target)
    return arrived


def send_session_file(
    storage_root: Path, session: str, name: str, target: SshTarget | LocalTarget
) -> Arrived:
    """Copy a session-level file (`session.json`) to <data_root>/<session>/<name>."""
    source = layout.session_dir(storage_root, session) / name
    if not source.is_file():
        raise TransferError(f"{source} is not a file")
    rel = PurePosixPath(session, name)
    _rsync(source, rel, target)
    arrived, local = target.measure(rel), Arrived(source.stat().st_size, _sha256(source))
    if arrived != local:
        raise TransferError(f"{name} arrived as {arrived}, sent {local}")
    return arrived


def rsync_cmd(source: Path, rel: PurePosixPath, target: SshTarget | LocalTarget) -> list[str]:
    return ["rsync", "--times", "--mkpath", f"--partial-dir={PARTIAL_DIR}",
            *target.rsync_shell(), str(source), target.rsync_dest(rel)]


def _rsync(source: Path, rel: PurePosixPath, target: SshTarget | LocalTarget) -> None:
    _run(rsync_cmd(source, rel, target))


def _remote_rel(take_dir: Path, rel_path: str) -> PurePosixPath:
    """<session>/takes/<take>/<rel_path>, checked so nothing escapes the take."""
    rel = PurePosixPath(rel_path)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise TransferError(f"{rel_path!r} must be a path inside the take folder")
    if take_dir.parent.name != "takes":
        raise TransferError(f"{take_dir} is not a take folder (<root>/<session>/takes/<take>)")
    session, take = take_dir.parent.parent.name, take_dir.name
    layout.check_id("session", session)
    layout.check_id("take", take)
    return PurePosixPath(session, "takes", take) / rel


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-ERROR_LINES:])
        raise TransferError(f"{cmd[0]} exited {result.returncode}:\n{tail}")
    return result.stdout


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
