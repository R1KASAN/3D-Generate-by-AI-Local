from __future__ import annotations

from local3d.services.serial_dispatcher import SerialDispatcher


def test_fifo_dispatcher_allows_one_active_job_and_approximate_positions() -> None:
    dispatcher = SerialDispatcher()
    dispatcher.enqueue("job-a")
    dispatcher.enqueue("job-b")
    dispatcher.enqueue("job-c")

    assert dispatcher.position("job-a") == 1
    assert dispatcher.position("job-b") == 2
    assert dispatcher.claim_next() == "job-a"
    assert dispatcher.active_job == "job-a"
    assert dispatcher.claim_next() is None
    assert dispatcher.position("job-b") == 2

    dispatcher.complete("job-a")
    assert dispatcher.claim_next() == "job-b"
    dispatcher.complete("job-b")
    assert dispatcher.claim_next() == "job-c"


def test_duplicate_enqueue_does_not_create_a_second_execution() -> None:
    dispatcher = SerialDispatcher()
    dispatcher.enqueue("job-a")
    dispatcher.enqueue("job-a")

    assert dispatcher.pending == ("job-a",)
    assert dispatcher.claim_next() == "job-a"
    dispatcher.enqueue("job-a")
    assert dispatcher.claim_next() is None
