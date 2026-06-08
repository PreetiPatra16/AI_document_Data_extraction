from pathlib import Path

import httpx
import pytest

from scripts.test_corpus import ground_truth_for, render_fields, request_json, slugify


def test_slugify_and_ground_truth_mapping(tmp_path):
    ground_truth = tmp_path / "ground_truth"
    ground_truth.mkdir()
    expected = ground_truth / "health_claim_form.json"
    expected.write_text("{}")
    source = tmp_path / "GCI_Claim Form -1-1.pdf"
    assert slugify(source.stem) == "gci_claim-form--1-1"
    assert ground_truth_for(source, ground_truth) == expected


def test_render_fields_creates_reviewable_markdown():
    output = render_fields({
        "document_type": "test_form",
        "confidence_summary": 0.9,
        "review_required": False,
        "warnings": [],
        "fields": {
            "name": {
                "normalized_value": "Riya Sharma",
                "confidence": 0.95,
                "source_engine": "paddleocr",
                "page": 1,
                "review_required": False,
            }
        },
    })
    assert "| name | Riya Sharma | 0.95 | paddleocr | 1 | no |" in output


def test_request_json_keeps_all_routes_under_api_prefix():
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))
        return httpx.Response(200, json={"status": "ok"})

    with httpx.Client(
        base_url="http://localhost:8000/api/v1/",
        transport=httpx.MockTransport(handler),
    ) as client:
        request_json(client, "GET", "/health/ready")
        request_json(client, "POST", "upload")

    assert requested_urls == [
        "http://localhost:8000/api/v1/health/ready",
        "http://localhost:8000/api/v1/upload",
    ]


def test_request_json_error_shows_final_requested_url():
    def handler(request):
        return httpx.Response(404, json={"detail": "Not Found"})

    with httpx.Client(
        base_url="http://localhost:8000/api/v1/",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(RuntimeError, match=r"http://localhost:8000/api/v1/upload"):
            request_json(client, "POST", "upload")
