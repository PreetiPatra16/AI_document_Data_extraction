# Frontend Integration Contract

This document is the frontend-facing contract for backend v1. Generated OpenAPI
documentation is available at `http://localhost:8000/docs`.

## Base URL And CORS

- Local API base URL: `http://localhost:8000/api/v1`
- JSON requests and responses use `application/json`.
- Uploads use `multipart/form-data`.
- The upload form field must be named `file`.
- Allowed browser origins are configured with `CORS_ORIGINS`.
- The API returns an `X-Request-ID` response header. Include it in bug reports.

## Document Lifecycle

```text
UPLOADED -> QUEUED -> PROCESSING -> COMPLETED
                                  -> FAILED
```

- `UPLOADED`: source file was validated and is ready to queue.
- `QUEUED`: an extraction job exists and is waiting for a worker.
- `PROCESSING`: the worker is actively processing the document.
- `COMPLETED`: structured extraction data is available.
- `FAILED`: extraction stopped; inspect `failure_code` and `failure_message`.

Job statuses are `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, or `CANCELLED`.
Treat `COMPLETED`, `FAILED`, and `CANCELLED` as terminal.

Progress is an integer from `0` through `100`. The current processing stage may
be `validation`, `rendering`, `preprocessing`, `ocr`, `classification`,
`extraction`, `normalization`, or `cleanup`.

## Recommended Frontend Flow

1. Upload one document with `POST /upload`.
2. Queue extraction with `POST /extract/{document_id}`.
3. Poll `GET /jobs/{job_id}` every 1-2 seconds while the job is active.
4. When terminal, fetch `GET /document/{document_id}`.
5. Display extracted fields, warnings, confidence, and review flags.
6. Delete retained metadata/results with `DELETE /document/{document_id}` when
   the user requests deletion.

The worker automatically deletes the original document and generated files
after success or failure. The frontend must not expect a document preview or
download URL after processing.

If the page reloads and the frontend no longer has the `job_id`, poll
`GET /document/{document_id}` instead. That response also contains status,
stage, progress, processing events, and the terminal result.

## Endpoints

### Upload Document

`POST /upload`

Accepts one PDF, JPG, JPEG, or PNG, up to 50 MB by default. PDFs may contain up
to 100 pages by default.

```bash
curl -F file=@sample.pdf http://localhost:8000/api/v1/upload
```

Success: `201 Created`

```json
{
  "document_id": "a456f3b3-6367-42a6-99ef-faa929d3d5c3",
  "filename": "sample.pdf",
  "status": "UPLOADED",
  "message": "File uploaded and validated. Extraction can be queued."
}
```

### Queue Extraction

`POST /extract/{document_id}`

Success: `202 Accepted`

```json
{
  "job_id": "fbb50cc4-f928-4e93-9283-469cf33d176f",
  "document_id": "a456f3b3-6367-42a6-99ef-faa929d3d5c3",
  "status": "QUEUED",
  "message": "Extraction job queued."
}
```

Possible errors:

- `404`: document does not exist.
- `409`: document already has an active job.
- `410`: source file is no longer available for extraction.

### Poll Job

`GET /jobs/{job_id}`

```json
{
  "id": "fbb50cc4-f928-4e93-9283-469cf33d176f",
  "document_id": "a456f3b3-6367-42a6-99ef-faa929d3d5c3",
  "status": "PROCESSING",
  "stage": "ocr",
  "progress": 55,
  "attempts": 1,
  "max_attempts": 2,
  "created_at": "2026-06-06T07:30:00+00:00",
  "started_at": "2026-06-06T07:30:01+00:00",
  "finished_at": null,
  "failure_code": null,
  "failure_message": null
}
```

Stop polling when the status is terminal. Network failures while polling do not
mean the extraction job failed; retry polling with bounded backoff.

### Fetch Document And Result

`GET /document/{document_id}`

The response always includes metadata, status, progress, and safe processing
events. `extracted_data` is populated only after successful completion.

```json
{
  "id": "a456f3b3-6367-42a6-99ef-faa929d3d5c3",
  "filename": "sample.pdf",
  "file_type": "pdf",
  "file_size": 245760,
  "page_count": 3,
  "status": "COMPLETED",
  "current_stage": "cleanup",
  "progress": 100,
  "uploaded_at": "2026-06-06T07:30:00+00:00",
  "updated_at": "2026-06-06T07:30:35+00:00",
  "processing_time_ms": 34000,
  "failure_code": null,
  "failure_message": null,
  "source_available": false,
  "logs": [],
  "extracted_data": {
    "schema_version": "1.0",
    "document_type": "health_claim_form",
    "confidence_summary": 0.91,
    "review_required": false,
    "fields": {
      "employee_name": {
        "value": "Pranita Vilas Ghule",
        "normalized_value": "Pranita Vilas Ghule",
        "confidence": 0.96,
        "bounding_box": {
          "x": 100,
          "y": 200,
          "width": 300,
          "height": 30
        },
        "page": 1,
        "raw_text": "Pranita Vilas Ghule",
        "source_engine": "paddleocr",
        "review_required": false
      }
    },
    "tables": [],
    "warnings": []
  }
}
```

Frontend display rules:

- Prefer `normalized_value`; fall back to `value`.
- Highlight a field when `review_required` is `true`.
- Highlight the whole result when `extracted_data.review_required` is `true`.
- Show warnings as non-fatal extraction notices.
- Treat missing fields as absent keys or fields with null values.
- Do not expose `raw_text` unless the product explicitly needs OCR evidence.

### List Documents

`GET /document`

Returns an array of document responses. This is suitable for a local processing
history screen.

### Delete Document

`DELETE /document/{document_id}`

Success: `204 No Content`. Do not attempt to parse a JSON body.

## Error Envelope

Every handled API error uses:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The uploaded file is invalid.",
    "details": {},
    "request_id": "a4e25ea4-5f04-4f81-b948-c289b033388b"
  }
}
```

Use the HTTP status for control flow and `error.code` for specific UI messages.
Display `error.message` to the user when appropriate. Do not render arbitrary
values from `details` without checking their shape.

Common statuses:

| HTTP status | Frontend behavior |
|---|---|
| `400` / `422` | Show upload or request validation feedback |
| `404` | Remove stale document/job references from the current view |
| `409` | Do not trigger again; continue polling the known job or document |
| `410` | Explain that the source file was deleted and must be uploaded again |
| `413` | Explain that the upload exceeds the configured limit |
| `500` | Show a generic failure and retain the `request_id` for investigation |

## Failure Codes

Terminal job/document failures may include:

- `validation_failed`
- `source_file_missing`
- `rendering_failed`
- `ocr_unavailable`
- `ocr_failed`
- `classification_failed`
- `extraction_failed`
- `storage_failed`
- `job_timeout`
- `internal_error`

These failure messages are safe for the frontend. Stack traces and extracted
document values are intentionally excluded.

## Health Endpoints

- `GET /health/live`: process liveness.
- `GET /health/ready`: database, storage, OCR, model, and Poppler readiness.
- `GET /health`: detailed health information.

The frontend normally does not need continuous health polling. Use readiness for
an initial backend-availability check or an administrative diagnostics view.

## Existing Frontend Migration Checklist

The current frontend predates this backend contract. Address these points before
treating it as integrated:

- Replace the old `PENDING` status with `UPLOADED`.
- Treat both `QUEUED` and `PROCESSING` as active polling states.
- Store the `job_id` returned by the extraction trigger and add
  `GET /jobs/{job_id}` to the API client.
- Remove the `/document/{document_id}/raw` preview request. That endpoint does
  not exist because source files are automatically deleted after terminal jobs.
- Replace terminal-job "retry extraction" with "upload again". A completed or
  failed document has no source file available for retry and returns `410`.
- Render `failure_code` and `failure_message` for failed documents.
- Parse API failures from `error.code`, `error.message`, `error.details`, and
  `error.request_id`.
- Use `VITE_API_URL` for all backend links instead of hard-coding localhost.
