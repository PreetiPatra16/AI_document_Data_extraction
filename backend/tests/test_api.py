import io

from fastapi.testclient import TestClient
from PIL import Image

from app.api.dependencies import get_ingestion_service, get_storage_service
from app.main import app


def image_bytes():
    stream = io.BytesIO()
    Image.new("RGB", (25, 25), "white").save(stream, "PNG")
    return stream.getvalue()


def test_upload_queue_poll_and_duplicate_contract(configured_services):
    _, storage, ingestion = configured_services
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    try:
        client = TestClient(app)
        upload = client.post("/api/v1/upload", files={"file": ("sample.png", image_bytes(), "image/png")})
        assert upload.status_code == 201
        document_id = upload.json()["document_id"]
        queued = client.post(f"/api/v1/extract/{document_id}")
        assert queued.status_code == 202
        assert queued.json()["status"] == "QUEUED"
        duplicate = client.post(f"/api/v1/extract/{document_id}")
        assert duplicate.status_code == 409
        job = client.get(f"/api/v1/jobs/{queued.json()['job_id']}")
        assert job.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_validation_error_has_stable_code_and_request_id(configured_services):
    _, storage, ingestion = configured_services
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/upload",
            files={"file": ("not-allowed.zip", b"fake", "application/zip")},
            headers={"X-Request-ID": "test-request-id"},
        )
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["request_id"] == "test-request-id"
        assert response.headers["X-Request-ID"] == "test-request-id"
    finally:
        app.dependency_overrides.clear()
