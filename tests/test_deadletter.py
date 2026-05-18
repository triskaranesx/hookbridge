"""Tests for hookbridge.deadletter."""
import time
import pytest
from hookbridge.deadletter import DeadLetterEntry, DeadLetterQueue


@pytest.fixture()
def queue() -> DeadLetterQueue:
    return DeadLetterQueue(capacity=10)


def test_record_returns_entry(queue):
    entry = queue.record("my-route", {"x": 1}, "timeout", 3)
    assert isinstance(entry, DeadLetterEntry)
    assert entry.route == "my-route"
    assert entry.payload == {"x": 1}
    assert entry.reason == "timeout"
    assert entry.attempts == 3


def test_record_assigns_unique_ids(queue):
    e1 = queue.record("r", {}, "err", 1)
    e2 = queue.record("r", {}, "err", 1)
    assert e1.id != e2.id


def test_record_sets_failed_at_timestamp(queue):
    before = time.time()
    entry = queue.record("r", {}, "err", 1)
    after = time.time()
    assert before <= entry.failed_at <= after


def test_record_stores_tags(queue):
    entry = queue.record("r", {}, "err", 1, tags={"env": "prod"})
    assert entry.tags == {"env": "prod"}


def test_all_returns_all_entries(queue):
    queue.record("a", {}, "e", 1)
    queue.record("b", {}, "e", 2)
    assert len(queue.all()) == 2


def test_all_returns_copy(queue):
    queue.record("a", {}, "e", 1)
    result = queue.all()
    result.clear()
    assert len(queue) == 1


def test_get_by_route_filters(queue):
    queue.record("alpha", {}, "e", 1)
    queue.record("beta", {}, "e", 1)
    queue.record("alpha", {}, "e", 2)
    found = queue.get_by_route("alpha")
    assert len(found) == 2
    assert all(e.route == "alpha" for e in found)


def test_get_by_id_found(queue):
    entry = queue.record("r", {}, "e", 1)
    result = queue.get_by_id(entry.id)
    assert result is entry


def test_get_by_id_missing_returns_none(queue):
    assert queue.get_by_id("nonexistent") is None


def test_remove_existing_entry(queue):
    entry = queue.record("r", {}, "e", 1)
    removed = queue.remove(entry.id)
    assert removed is True
    assert queue.get_by_id(entry.id) is None


def test_remove_nonexistent_returns_false(queue):
    assert queue.remove("ghost-id") is False


def test_capacity_evicts_oldest():
    q = DeadLetterQueue(capacity=3)
    e1 = q.record("r", {}, "e", 1)
    q.record("r", {}, "e", 1)
    q.record("r", {}, "e", 1)
    q.record("r", {}, "e", 1)  # should evict e1
    assert q.get_by_id(e1.id) is None
    assert len(q) == 3


def test_clear_empties_queue(queue):
    queue.record("r", {}, "e", 1)
    queue.clear()
    assert len(queue) == 0


def test_invalid_capacity_raises():
    with pytest.raises(ValueError):
        DeadLetterQueue(capacity=0)
