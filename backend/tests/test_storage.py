import pytest

from app.middleware.error_handler import ConflictException
from app.core.domain import FailureCode


def test_job_is_persistent_and_duplicate_active_job_is_rejected(configured_services):
    _, storage, _ = configured_services
    storage.create_document_record("doc", "sample.png", "image/png", 10, 1, "/tmp/source.png")
    job = storage.create_job("doc")
    assert job["status"] == "QUEUED"
    with pytest.raises(ConflictException):
        storage.create_job("doc")
    claimed = storage.claim_next_job("worker")
    assert claimed["id"] == job["id"]
    assert claimed["status"] == "PROCESSING"


def test_delete_removes_source(configured_services, tmp_path):
    _, storage, _ = configured_services
    source = tmp_path / "source.png"
    source.write_bytes(b"x")
    storage.create_document_record("doc", "sample.png", "image/png", 1, 1, str(source))
    storage.delete_document_record("doc")
    assert not source.exists()
    assert storage.get_document_record("doc") is None


def test_retry_requeues_until_attempt_limit(configured_services):
    _, storage, _ = configured_services
    storage.create_document_record("doc", "sample.png", "image/png", 10, 1, "/tmp/source.png")
    job = storage.create_job("doc")
    claimed = storage.claim_next_job("worker")
    assert storage.retry_job(claimed["id"], FailureCode.OCR_FAILED, "OCR temporarily failed") is True
    retried = storage.claim_next_job("worker")
    assert retried["attempts"] == 2
    assert storage.retry_job(retried["id"], FailureCode.OCR_FAILED, "OCR failed again") is False
