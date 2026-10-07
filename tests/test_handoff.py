import socket
from pathlib import PurePosixPath

import pytest
import zmq
from mocap_contracts import (
    CameraFileReady,
    FileKind,
    SyncEvent,
    SyncKind,
    SyncSource,
    TakeClosed,
    from_json,
    layout,
    to_json,
    transport,
)

from mocap_capture.config import Handoff
from mocap_capture.handoff import HandoffError, Publisher, sidecar_path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def event(kind: str, ts: int) -> SyncEvent:
    return SyncEvent(kind=SyncKind.Value(f"SYNC_KIND_{kind}"), host_ts_ns=ts,
                     source=SyncSource.Value("SYNC_SOURCE_MANUAL"))


def closed() -> TakeClosed:
    msg = TakeClosed(take_id="T1", start=event("START", 1), end=event("END", 2))
    msg.roles.extend(["body_1", "body_2"])
    return msg


def ready(path="raw/body_1.timestamps.csv") -> CameraFileReady:
    return CameraFileReady(take_id="T1", role="body_1", kind=FileKind.Value("FILE_KIND_TIMESTAMPS"),
                           path=path, size_bytes=17, sha256="ab" * 32, frames=0,
                           first_ts_ns=1, last_ts_ns=2)


@pytest.fixture
def handoff():
    return Handoff(host="127.0.0.1", take_closed_port=free_port(), file_ready_port=free_port(),
                   ssh_user="rafael", data_root=PurePosixPath("/data/mocap"))


@pytest.fixture
def ctx():
    ctx = zmq.Context()
    yield ctx
    ctx.destroy(linger=0)


@pytest.fixture
def take_dir(tmp_path):
    take_dir = tmp_path / "S1" / "takes" / "T1"
    layout.raw_dir(take_dir).mkdir(parents=True)
    return take_dir


def receiver(cls, ctx, port):
    rx = transport.new_receiver(cls, ctx, f"tcp://127.0.0.1:{port}")
    rx.socket.rcvtimeo = 3000
    return rx


def same(a, b) -> bool:
    """Equal as contract messages (the sender stamps Harpia's origin field)."""
    return to_json(a) == to_json(b)


@pytest.mark.parametrize("make, sidecar", [(closed, "closed.json"),
                                           (ready, "raw/body_1.timestamps.csv.ready.json")])
def test_sidecar_content_equals_the_sent_message(handoff, ctx, take_dir, make, sidecar):
    msg = make()
    port = handoff.take_closed_port if isinstance(msg, TakeClosed) else handoff.file_ready_port
    rx = receiver(type(msg), ctx, port)
    with Publisher(handoff, ctx) as pub:
        path = pub.publish(take_dir, msg)
    assert path == take_dir / sidecar
    got = rx.recv()
    assert got is not None
    assert same(got, from_json(type(msg), path.read_text()))
    assert same(got, msg)


def test_event_sent_while_the_receiver_is_down_arrives_once_it_binds(handoff, ctx, take_dir):
    pub = Publisher(handoff, ctx)
    pub.publish(take_dir, closed())
    rx = receiver(TakeClosed, ctx, handoff.take_closed_port)  # the processing PC comes up later
    got = rx.recv()
    pub.close()
    assert got is not None and same(got, closed())


def test_after_a_publisher_restart_the_lost_event_is_in_its_sidecar(handoff, ctx, take_dir):
    pub = Publisher(handoff, ctx)
    pub.publish(take_dir, ready())
    pub.close(flush_ms=0)  # the recorder dies before the processing PC is up: the message is gone
    rx = receiver(CameraFileReady, ctx, handoff.file_ready_port)
    rx.socket.rcvtimeo = 300
    assert rx.recv() is None
    recovered = from_json(CameraFileReady, sidecar_path(take_dir, ready()).read_text())
    assert same(recovered, ready())


@pytest.mark.parametrize("path", ["../escape", "/etc/passwd"])
def test_invalid_event_writes_nothing_and_sends_nothing(handoff, ctx, take_dir, path):
    rx = receiver(CameraFileReady, ctx, handoff.file_ready_port)
    rx.socket.rcvtimeo = 300
    with Publisher(handoff, ctx) as pub, pytest.raises(ValueError, match="relative"):
        pub.publish(take_dir, ready(path=path))
    assert rx.recv() is None
    assert list(take_dir.rglob("*.json*")) == []


def test_not_an_event():
    with pytest.raises(HandoffError, match="not a hand-off event"):
        sidecar_path(None, SyncEvent())
