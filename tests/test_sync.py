import time

import pytest
from mocap_contracts import SyncEvent, from_json, to_json

from mocap_capture.sync import END, MANUAL, START, ManualTrigger, SyncError


def ticking(*values):
    it = iter(values)
    return lambda: next(it)


def test_start_then_end():
    trigger = ManualTrigger(clock=ticking(100, 250))
    start, end = trigger.mark(START), trigger.mark(END)
    assert (start.kind, start.host_ts_ns, start.source) == (START, 100, MANUAL)
    assert (end.kind, end.host_ts_ns, end.source) == (END, 250, MANUAL)
    assert (trigger.start, trigger.end) == (start, end)


def test_events_are_valid_contract_messages():
    trigger = ManualTrigger()
    for event in (trigger.mark(START), trigger.mark(END)):
        assert from_json(SyncEvent, to_json(event)) == event


def test_real_clock_is_unix_ns_and_monotonic():
    before = time.time_ns()
    trigger = ManualTrigger()
    start, end = trigger.mark(START), trigger.mark(END)
    assert before <= start.host_ts_ns <= end.host_ts_ns <= time.time_ns()


def test_simulated_key_press():
    prompts = []
    trigger = ManualTrigger(clock=ticking(5, 9))
    start = trigger.mark_on_key(START, "Enter to start", read=prompts.append)
    end = trigger.mark_on_key(END, "Enter to stop", read=prompts.append)
    assert prompts == ["Enter to start", "Enter to stop"]
    assert (start.host_ts_ns, end.host_ts_ns) == (5, 9)


def test_clock_going_backwards_is_an_error():
    trigger = ManualTrigger(clock=ticking(200, 150))
    trigger.mark(START)
    with pytest.raises(SyncError, match="went backwards"):
        trigger.mark(END)
    assert trigger.end is None


@pytest.mark.parametrize(
    "marks, message",
    [
        ([END], "END before START"),
        ([START, START], "START is already marked"),
        ([START, END, END], "END is already marked"),
        ([0], "can't mark SYNC_KIND_UNSET"),
    ],
)
def test_out_of_order(marks, message):
    trigger = ManualTrigger(clock=ticking(*range(len(marks))))
    *ok, bad = marks
    for kind in ok:
        trigger.mark(kind)
    with pytest.raises(SyncError, match=message):
        trigger.mark(bad)
