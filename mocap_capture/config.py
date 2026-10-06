"""`config.yaml`: the recorder's declaration of its storage and cameras.

`storage.root` is the data root the session folders live under
(`mocap_contracts.layout`): an absolute path, required, never guessed.
`report.max_gap_ms` is the longest frame gap a take may have and still be
ok (shorter gaps are listed in the report, not failed).
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
from pathlib import Path

import yaml
from mocap_contracts import CameraConfig, ContractError, from_json

SECTIONS = ("storage", "report", "cameras")
STORAGE_KEYS = ("root",)
REPORT_KEYS = ("max_gap_ms",)


class ConfigError(ValueError):
    """A `config.yaml` that can't be used."""


@dataclass(frozen=True)
class Config:
    storage_root: Path
    max_gap_ms: float
    cameras: tuple[CameraConfig, ...]


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
    max_gap_ms = _report(path, data.get("report"))
    entries = data.get("cameras")
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path}: cameras must be a non-empty list")

    cameras = tuple(_camera(path, i, entry) for i, entry in enumerate(entries))
    roles = [c.role for c in cameras]
    duplicates = sorted({r for r in roles if roles.count(r) > 1})
    if duplicates:
        raise ConfigError(f"{path}: duplicate role(s) {duplicates}")
    return Config(storage_root=storage_root, max_gap_ms=max_gap_ms, cameras=cameras)


def _report(path: str | PathLike[str], report: object) -> float:
    if not isinstance(report, dict):
        raise ConfigError(f"{path}: report must be a mapping with max_gap_ms")
    unknown = sorted(set(report) - set(REPORT_KEYS))
    if unknown:
        raise ConfigError(f"{path}: report: unknown key(s) {unknown}")
    limit = report.get("max_gap_ms")
    if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit <= 0:
        raise ConfigError(f"{path}: report.max_gap_ms must be a positive number, got {limit!r}")
    return float(limit)


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
    try:
        text = json.dumps(entry)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"{where}: {e}") from None
    try:
        return from_json(CameraConfig, text)
    except ContractError as e:
        raise ConfigError(f"{where}: {e}") from None
