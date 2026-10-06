"""Camera sources: one interface over UVC webcams and STREAM tablets.

A take drives every source through the same four calls, in order:

    prepare()          before the take: open the device, check it can deliver
                       the configured format (STREAM also syncs clocks)
    start(take_dir)    start writing under `raw/` of the take folder
    stop()             stop writing (STREAM syncs clocks again)
    collect(take_dir)  finish the files and return the paths written
                       (the video and its `timestamps.csv`, per `layout`)

Implementations register under the `CameraSource` enum value of mocap-contracts
they handle, and `create_source` picks one from a `CameraConfig`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from mocap_contracts import CameraConfig
from mocap_contracts import CameraSource as SourceKind


@runtime_checkable
class CameraSource(Protocol):
    config: CameraConfig

    def prepare(self) -> None: ...

    def start(self, take_dir: Path) -> None: ...

    def stop(self) -> None: ...

    def collect(self, take_dir: Path) -> list[Path]: ...


SourceFactory = Callable[[CameraConfig], CameraSource]

_REGISTRY: dict[int, SourceFactory] = {}


def register(kind: int) -> Callable[[SourceFactory], SourceFactory]:
    """Class decorator: `@register(SourceKind.Value("CAMERA_SOURCE_UVC"))`."""
    name = SourceKind.Name(kind)
    if kind == 0:
        raise ValueError(f"can't register a source for {name}")

    def add(factory: SourceFactory) -> SourceFactory:
        if kind in _REGISTRY:
            raise ValueError(f"a source for {name} is already registered")
        _REGISTRY[kind] = factory
        return factory

    return add


def create_source(config: CameraConfig) -> CameraSource:
    try:
        factory = _REGISTRY[config.source]
    except KeyError:
        name = SourceKind.Name(config.source)
        raise LookupError(f"role {config.role}: no source registered for {name}") from None
    return factory(config)
