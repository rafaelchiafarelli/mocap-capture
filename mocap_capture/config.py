"""`config.yaml`: the recorder's declaration of its storage and cameras.

`storage.root` is the data root the session folders live under
(`mocap_contracts.layout`): an absolute path, required, never guessed.
`report.max_gap_ms` is the longest frame gap a take may have and still be
ok (shorter gaps are listed in the report, not failed). `take.post_roll_ms`
is how long every source keeps recording after END, so the last frames
captured before END have arrived when it stops.
Every camera declares `preprocess:`, either a `PreprocessSpec` (crop inside
the source frame, output size) or the word `none`; a missing one is an error,
never a default. In the resulting `CameraConfig` an absent `preprocess`
means none, as the contract says.
`handoff` declares the processing PC: its `host`, the ports its
`mocap-extract watch` binds for `TakeClosed` and `CameraFileReady`, and the
`ssh_user` and `data_root` (absolute, on that PC) files are rsynced into.
Each `cameras` entry is a `CameraConfig` from
mocap-contracts and is checked exactly like a contract file: declared
fields only, `required` enforced, plus the per-message rules. Every other
section (`handoff`, `board`, ...) is added by the task that needs it, so
an unknown top-level key is an error rather than something to ignore.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from os import PathLike
from pathlib import Path, PurePosixPath

import yaml
from mocap_contracts import CameraConfig, ContractError, PreprocessSpec, from_json

SECTIONS = ("storage", "take", "report", "handoff", "cameras")
HANDOFF_KEYS = ("host", "take_closed_port", "file_ready_port", "ssh_user", "data_root")
STORAGE_KEYS = ("root",)


class ConfigError(ValueError):
    """A `config.yaml` that can't be used."""


@dataclass(frozen=True)
class Handoff:
    host: str
    take_closed_port: int
    file_ready_port: int
    ssh_user: str
    data_root: PurePosixPath

    @property
    def take_closed_endpoint(self) -> str:
        return f"tcp://{self.host}:{self.take_closed_port}"

    @property
    def file_ready_endpoint(self) -> str:
        return f"tcp://{self.host}:{self.file_ready_port}"


@dataclass(frozen=True)
class Config:
    storage_root: Path
    post_roll_ms: float
    max_gap_ms: float
    handoff: Handoff
    cameras: tuple[CameraConfig, ...]

    def preprocess(self, role: str) -> PreprocessSpec | None:
        """The role's declared preprocessing, None for `none`."""
        camera = next((c for c in self.cameras if c.role == role), None)
        if camera is None:
            raise KeyError(f"no camera with role {role!r}")
        return camera.preprocess if camera.HasField("preprocess") else None


def load_config(path: str | PathLike[str]) -> Config:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError as e:
        raise ConfigError(f"{path}: {e.strerror}") from None
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: invalid YAML: {e}") from None

    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a mapping at the top level")
    unknown = sorted(set(data) - set(SECTIONS))
    if unknown:
        raise ConfigError(f"{path}: unknown section(s) {unknown}")
    storage_root = _storage(path, data.get("storage"))
    post_roll_ms = _number(path, data.get("take"), "take", "post_roll_ms", allow_zero=True)
    max_gap_ms = _number(path, data.get("report"), "report", "max_gap_ms")
    handoff = _handoff(path, data.get("handoff"))
    entries = data.get("cameras")
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path}: cameras must be a non-empty list")

    cameras = tuple(_camera(path, i, entry) for i, entry in enumerate(entries))
    roles = [c.role for c in cameras]
    duplicates = sorted({r for r in roles if roles.count(r) > 1})
    if duplicates:
        raise ConfigError(f"{path}: duplicate role(s) {duplicates}")
    return Config(
        storage_root=storage_root, post_roll_ms=post_roll_ms, max_gap_ms=max_gap_ms,
        handoff=handoff, cameras=cameras,
    )


def _number(
    path: str | PathLike[str], section: object, name: str, key: str, allow_zero: bool = False
) -> float:
    """A section holding exactly one required number, `key`."""
    if not isinstance(section, dict):
        raise ConfigError(f"{path}: {name} must be a mapping with {key}")
    unknown = sorted(set(section) - {key})
    if unknown:
        raise ConfigError(f"{path}: {name}: unknown key(s) {unknown}")
    value = section.get(key)
    bad = isinstance(value, bool) or not isinstance(value, (int, float))
    if bad or value < 0 or (value == 0 and not allow_zero):
        what = "a non-negative" if allow_zero else "a positive"
        raise ConfigError(f"{path}: {name}.{key} must be {what} number, got {value!r}")
    return float(value)


def _handoff(path: str | PathLike[str], handoff: object) -> Handoff:
    if not isinstance(handoff, dict):
        raise ConfigError(f"{path}: handoff must be a mapping with {list(HANDOFF_KEYS)}")
    unknown = sorted(set(handoff) - set(HANDOFF_KEYS))
    if unknown:
        raise ConfigError(f"{path}: handoff: unknown key(s) {unknown}")
    host = handoff.get("host")
    if not isinstance(host, str) or not host:
        raise ConfigError(f"{path}: handoff.host must be a host name or IP, got {host!r}")
    ports = {}
    for key in ("take_closed_port", "file_ready_port"):
        port = handoff.get(key)
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ConfigError(f"{path}: handoff.{key} must be a port 1..65535, got {port!r}")
        ports[key] = port
    if ports["take_closed_port"] == ports["file_ready_port"]:
        raise ConfigError(f"{path}: handoff ports must differ (one per event type)")
    user = handoff.get("ssh_user")
    if not isinstance(user, str) or not user:
        raise ConfigError(f"{path}: handoff.ssh_user must be a user name, got {user!r}")
    root = handoff.get("data_root")
    if not isinstance(root, str) or not PurePosixPath(root).is_absolute():
        raise ConfigError(f"{path}: handoff.data_root must be an absolute path, got {root!r}")
    return Handoff(host=host, ssh_user=user, data_root=PurePosixPath(root), **ports)


def _storage(path: str | PathLike[str], storage: object) -> Path:
    if not isinstance(storage, dict):
        raise ConfigError(f"{path}: storage must be a mapping with root")
    unknown = sorted(set(storage) - set(STORAGE_KEYS))
    if unknown:
        raise ConfigError(f"{path}: storage: unknown key(s) {unknown}")
    root = storage.get("root")
    if not isinstance(root, str) or not Path(root).is_absolute():
        raise ConfigError(f"{path}: storage.root must be an absolute path, got {root!r}")
    return Path(root)


def _camera(path: str | PathLike[str], i: int, entry: object) -> CameraConfig:
    where = f"{path}: cameras[{i}]"
    if isinstance(entry, dict):
        if "preprocess" not in entry:
            raise ConfigError(f"{where}: preprocess must be declared (a spec, or none)")
        if entry["preprocess"] == "none":
            entry = {k: v for k, v in entry.items() if k != "preprocess"}
        elif not isinstance(entry["preprocess"], dict):
            raise ConfigError(f"{where}: preprocess must be a spec or none, got {entry['preprocess']!r}")
    try:
        text = json.dumps(entry)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{where}: {e}") from None
    try:
        camera = from_json(CameraConfig, text)
    except ContractError as e:
        raise ConfigError(f"{where}: {e}") from None
    if camera.HasField("preprocess") and camera.preprocess.HasField("crop"):
        c = camera.preprocess.crop
        if c.x + c.width > camera.width or c.y + c.height > camera.height:
            raise ConfigError(
                f"{where}: crop {c.x},{c.y} {c.width}x{c.height} is outside the "
                f"{camera.width}x{camera.height} source frame"
            )
    return camera
