"""Tests for hookbridge.audit."""
import time

import pytest

from hookbridge.audit import AuditEntry, AuditLog, make_entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(route="r1", status="dispatched", event_id="e1", size=100):
    return AuditEntry(route=route, event_id=event_id, status=status, payload_size=size)


# ---------------------------------------------------------------------------
# AuditLog basics
# ---------------------------------------------------------------------------

def test_empty_log_returns_empty_list():
    log = AuditLog()
    assert log.all() == []
    assert len(log) == 0


def test_record_and_all():
    log = AuditLog()
    e = _entry()
    log.record(e)
    assert log.all() == [e]
    assert len(log) == 1


def test_all_returns_copy():
    log = AuditLog()
    log.record(_entry())
    copy = log.all()
    copy.clear()
    assert len(log) == 1


def test_capacity_evicts_oldest():
    log = AuditLog(max_entries=3)
    for i in range(4):
        log.record(_entry(event_id=str(i)))
    ids = [e.event_id for e in log.all()]
    assert ids == ["1", "2", "3"]
    assert len(log) == 3


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

def test_by_route_filters_correctly():
    log = AuditLog()
    log.record(_entry(route="alpha"))
    log.record(_entry(route="beta"))
    log.record(_entry(route="alpha"))
    result = log.by_route("alpha")
    assert len(result) == 2
    assert all(e.route == "alpha" for e in result)


def test_by_status_filters_correctly():
    log = AuditLog()
    log.record(_entry(status="dispatched"))
    log.record(_entry(status="filtered"))
    log.record(_entry(status="dispatched"))
    result = log.by_status("filtered")
    assert len(result) == 1
    assert result[0].status == "filtered"


def test_since_returns_entries_at_or_after_timestamp():
    log = AuditLog()
    past = _entry(event_id="old")
    past.timestamp = time.time() - 100
    recent = _entry(event_id="new")
    recent.timestamp = time.time()
    log.record(past)
    log.record(recent)
    result = log.since(time.time() - 10)
    assert len(result) == 1
    assert result[0].event_id == "new"


def test_clear_removes_all():
    log = AuditLog()
    log.record(_entry())
    log.clear()
    assert len(log) == 0


# ---------------------------------------------------------------------------
# make_entry factory
# ---------------------------------------------------------------------------

def test_make_entry_computes_bytes_size():
    e = make_entry("r1", "e1", "dispatched", b"hello world")
    assert e.payload_size == 11


def test_make_entry_computes_str_size():
    e = make_entry("r1", "e1", "dispatched", "hello")
    assert e.payload_size == 5


def test_make_entry_non_string_payload_size_is_zero():
    """Non-bytes/str payloads (e.g. None) should record a payload_size of 0."""
    e = make_entry("r1", "e1", "dispatched", None)
    assert e.payload_size == 0


def test_make_entry_sets_route_and_status():
    """make_entry should propagate route and status onto the returned entry."""
    e = make_entry("my-route", "e42", "filtered", b"data")
    assert e.route == "my-route"
    assert e.event_id == "e42"
    assert e.status == "filtered"
