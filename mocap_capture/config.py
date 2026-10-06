"""`config.yaml`: the recorder's declaration of its cameras.

Only `cameras` exists so far. Each entry is a `CameraConfig` from
mocap-contracts and is checked exactly like a contract file: declared
fields only, `required` enforced, plus the per-message rules. Every other
section (`handoff`, `board`, ...) is added by the task that needs it, so
an unknown top-level key is an error rather than something to ignore.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from os import PathLike

import yaml
from mocap_contracts import CameraConfig, ContractError, from_json

SECTIONS = ("cameras",)


class ConfigError(ValueError):
    """A `config.yaml` that can't be used."""


@dataclass(frozen=True)
class Config:
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
    entries = data.get("cameras")
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path}: cameras must be a non-empty list")

    cameras = tuple(_camera(path, i, entry) for i, entry in enumerate(entries))
    roles = [c.role for c in cameras]
    duplicates = sorted({r for r in roles if roles.count(r) > 1})
    if duplicates:
        raise ConfigError(f"{path}: duplicate role(s) {duplicates}")
    return Config(cameras=cameras)


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
