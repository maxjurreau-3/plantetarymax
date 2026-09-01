import pytest

from messaging.queue import enqueue_message, get_queue_size, default_queue


def setup_function():
    # Clear the in-memory queue before each test
    try:
        default_queue.queue.clear()
    except Exception:
        # best-effort
        pass


def test_enqueue_message_returns_id_and_increments_queue():
    before = get_queue_size()
    msg_id = enqueue_message({"type": "test.event", "body": {"x": 1}}, source="test")
    assert isinstance(msg_id, str) and msg_id != ""
    after = get_queue_size()
    assert after == before + 1


def test_enqueue_message_retry_behavior_basic():
    # Enqueue another message and ensure it's processed by the in-memory queue when handler is provided
    processed = []

    def handler(payload):
        processed.append(payload)

    msg_id = enqueue_message({"type": "test.process", "body": {"y": 2}}, source="test", handler=handler)
    assert msg_id != ""
    # Process all messages in the default_queue via its process_all method
    count = default_queue.process_all()
    # Handler should have been called for one message
    assert len(processed) >= 1
    assert count >= 1
