"""Run every supported sample through the live API and save reviewable results."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

try:
    from scripts.score_accuracy import score
except ImportError:
    from score_accuracy import score


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()
    return value[:100] or "document"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def request_json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    relative_path = path.lstrip("/")
    response = client.request(method, relative_path, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw_response": response.text}
    if response.is_error:
        error = payload.get("error", payload)
        raise RuntimeError(
            f"{method} {response.request.url} failed with HTTP {response.status_code}: "
            f"{error.get('code', 'unknown_error')} - {error.get('message', error)}"
        )
    return payload


def render_fields(extraction: dict[str, Any] | None) -> str:
    if not extraction:
        return "No extraction result was returned.\n"
    lines = [
        f"Document type: {extraction.get('document_type')}",
        f"Confidence summary: {extraction.get('confidence_summary')}",
        f"Review required: {extraction.get('review_required')}",
        f"Warnings: {', '.join(extraction.get('warnings', [])) or 'none'}",
        "",
        "| Field | Value | Confidence | Engine | Page | Review |",
        "|---|---|---:|---|---:|---|",
    ]
    for name, field in extraction.get("fields", {}).items():
        value = str(field.get("normalized_value") if field.get("normalized_value") is not None else "")
        value = value.replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {name} | {value} | {field.get('confidence', 0):.2f} | "
            f"{field.get('source_engine') or ''} | {field.get('page') or ''} | "
            f"{'yes' if field.get('review_required') else 'no'} |"
        )
    return "\n".join(lines) + "\n"


def ground_truth_for(file: Path, ground_truth_dir: Path) -> Path | None:
    candidates = [
        ground_truth_dir / f"{slugify(file.stem)}.json",
        ground_truth_dir / f"{file.stem}.json",
    ]
    if "gci_claim form" in file.name.lower():
        candidates.insert(0, ground_truth_dir / "health_claim_form.json")
    return next((path for path in candidates if path.exists()), None)


def process_file(
    client: httpx.Client,
    source: Path,
    output_dir: Path,
    ground_truth_dir: Path,
    poll_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    folder = output_dir / slugify(source.stem)
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    print(f"\n[{source.name}] uploading")
    with source.open("rb") as handle:
        upload = request_json(client, "POST", "upload", files={"file": (source.name, handle)})
    write_json(folder / "01-upload.json", upload)
    document_id = upload["document_id"]

    print(f"[{source.name}] queueing document_id={document_id}")
    trigger = request_json(client, "POST", f"extract/{document_id}")
    write_json(folder / "02-trigger.json", trigger)
    job_id = trigger["job_id"]

    deadline = time.monotonic() + timeout_seconds
    last_marker = None
    while True:
        job = request_json(client, "GET", f"jobs/{job_id}")
        marker = (job["status"], job.get("stage"), job.get("progress"), job.get("attempts"))
        if marker != last_marker:
            print(
                f"[{source.name}] status={job['status']} stage={job.get('stage')} "
                f"progress={job.get('progress')}% attempt={job.get('attempts')}/{job.get('max_attempts')}"
            )
            last_marker = marker
        if job["status"] in TERMINAL_STATUSES:
            break
        if time.monotonic() > deadline:
            raise TimeoutError(f"Timed out waiting for job {job_id} after {timeout_seconds} seconds.")
        time.sleep(poll_seconds)

    write_json(folder / "03-job-final.json", job)
    document = request_json(client, "GET", f"document/{document_id}")
    write_json(folder / "04-document-final.json", document)
    write_json(folder / "05-processing-events.json", document.get("logs", []))
    extraction = document.get("extracted_data")
    if extraction:
        write_json(folder / "06-extraction.json", extraction)
    (folder / "07-fields-review.md").write_text(render_fields(extraction))

    accuracy = None
    expected = ground_truth_for(source, ground_truth_dir)
    if expected and extraction:
        accuracy = score(expected, folder / "06-extraction.json")
        accuracy["ground_truth"] = str(expected)
        write_json(folder / "08-accuracy.json", accuracy)

    return {
        "source": str(source),
        "output_dir": str(folder),
        "document_id": document_id,
        "job_id": job_id,
        "status": job["status"],
        "stage": job.get("stage"),
        "attempts": job.get("attempts"),
        "failure_code": job.get("failure_code"),
        "failure_message": job.get("failure_message"),
        "document_type": extraction.get("document_type") if extraction else None,
        "confidence_summary": extraction.get("confidence_summary") if extraction else None,
        "review_required": extraction.get("review_required") if extraction else None,
        "extracted_field_count": sum(
            1 for field in (extraction or {}).get("fields", {}).values() if field.get("value") is not None
        ),
        "accuracy": accuracy,
        "duration_seconds": round(time.monotonic() - started, 2),
    }


def render_summary(results: list[dict[str, Any]], base_url: str) -> str:
    lines = [
        "# Corpus Extraction Test",
        "",
        f"- API: `{base_url}`",
        f"- Documents: {len(results)}",
        f"- Completed: {sum(1 for result in results if result['status'] == 'COMPLETED')}",
        f"- Failed: {sum(1 for result in results if result['status'] != 'COMPLETED')}",
        "",
        "| Source | Status | Type | Fields | Confidence | Review | Typed Accuracy | Duration |",
        "|---|---|---|---:|---:|---|---:|---:|",
    ]
    for result in results:
        accuracy = result.get("accuracy") or {}
        typed_accuracy = accuracy.get("typed_accuracy")
        source_name = Path(result["source"]).name.replace("|", "\\|")
        lines.append(
            f"| {source_name} | {result['status']} | "
            f"{result.get('document_type') or ''} | {result['extracted_field_count']} | "
            f"{result.get('confidence_summary') if result.get('confidence_summary') is not None else ''} | "
            f"{result.get('review_required') if result.get('review_required') is not None else ''} | "
            f"{f'{typed_accuracy:.1%}' if typed_accuracy is not None else ''} | "
            f"{result['duration_seconds']}s |"
        )
        if result.get("failure_message"):
            lines.append(f"\nFailure for `{Path(result['source']).name}`: `{result['failure_code']}` - {result['failure_message']}\n")
    return "\n".join(lines) + "\n"


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    project_dir = backend_dir.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, default=project_dir / "generali_samples")
    parser.add_argument("--output", type=Path, default=project_dir / "test-results")
    parser.add_argument("--ground-truth", type=Path, default=backend_dir / "tests" / "ground_truth")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=1200)
    args = parser.parse_args()

    samples = sorted(
        path for path in args.samples.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not samples:
        print(f"No supported files found under {args.samples}", file=sys.stderr)
        return 2

    run_dir = args.output / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    results = []
    api_url = args.api_url.rstrip("/") + "/"
    with httpx.Client(base_url=api_url, timeout=60) as client:
        try:
            readiness = request_json(client, "GET", "health/ready")
            write_json(run_dir / "00-readiness.json", readiness)
            print(f"API readiness: {readiness['status']}")
            if readiness["status"] != "ready":
                print(
                    f"API is not ready. See {run_dir / '00-readiness.json'} for dependency details.",
                    file=sys.stderr,
                )
                return 2
        except Exception as exc:
            print(f"API is unavailable or unhealthy: {exc}", file=sys.stderr)
            return 2

        for sample in samples:
            try:
                result = process_file(
                    client, sample, run_dir, args.ground_truth, args.poll_seconds, args.timeout_seconds
                )
            except Exception as exc:
                result = {
                    "source": str(sample),
                    "output_dir": str(run_dir / slugify(sample.stem)),
                    "status": "RUNNER_ERROR",
                    "failure_code": type(exc).__name__,
                    "failure_message": str(exc),
                    "extracted_field_count": 0,
                    "duration_seconds": 0,
                }
                error_dir = Path(result["output_dir"])
                error_dir.mkdir(parents=True, exist_ok=True)
                write_json(error_dir / "00-runner-error.json", result)
                print(f"[{sample.name}] runner error: {exc}", file=sys.stderr)
            results.append(result)
            write_json(run_dir / "summary.json", results)

    summary = render_summary(results, api_url)
    (run_dir / "summary.md").write_text(summary)
    print(f"\nResults saved to: {run_dir}")
    print(summary)
    return 1 if any(result["status"] != "COMPLETED" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
