# AI Document Extraction Backend

Local-only FastAPI document extraction with a persistent SQLite job queue,
separate worker process, OpenCV preprocessing, local OCR, structured extraction,
and automatic document-file cleanup.

## Runtime Contract

- API service accepts and validates one PDF/JPG/JPEG/PNG upload at a time.
- `POST /api/v1/extract/{document_id}` queues work and returns `202`.
- A separate worker claims jobs from SQLite using WAL transactions.
- PaddleOCR is preferred when installed; Tesseract is the printed-text fallback.
- TrOCR is loaded only from `TROCR_MODEL_PATH`; runtime never downloads a model.
- Original and generated document files are deleted after success or failure.
- Metadata, safe events, and extracted JSON remain in SQLite.

## Local Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Run the worker separately:

```bash
cd backend
source .venv/bin/activate
python -m app.core.workers.extraction_worker
```

Swagger is available at `http://localhost:8000/docs`.

Frontend integration details, response examples, polling behavior, and error
handling are documented in [docs/frontend-integration.md](docs/frontend-integration.md).

## Optional Local Models

Install `requirements-models.txt`, provision TrOCR once, and let PaddleOCR cache
its official models under `models/paddlex` on first initialization. Models must
be provisioned ahead of production runtime; production networking can then be
disabled.

```bash
pip install -r requirements-models.txt
PYTHONPATH=. python scripts/provision_trocr.py
PYTHONPATH=. python scripts/verify_models.py
```

Set `PADDLE_REQUIRED=true` and `TROCR_REQUIRED=true` after provisioning. TrOCR
uses Apple Metal (`mps`) when available and otherwise falls back to CPU. TrOCR
must receive cropped handwritten text lines; running it against an entire form
does not produce useful results.

## API Flow

```bash
curl -F file=@sample.pdf http://localhost:8000/api/v1/upload
curl -X POST http://localhost:8000/api/v1/extract/DOCUMENT_ID
curl http://localhost:8000/api/v1/jobs/JOB_ID
curl http://localhost:8000/api/v1/document/DOCUMENT_ID
curl -X DELETE http://localhost:8000/api/v1/document/DOCUMENT_ID
```

The frontend should poll `GET /api/v1/jobs/{job_id}` while a job is `QUEUED` or
`PROCESSING`, then fetch `GET /api/v1/document/{document_id}` after the job
reaches `COMPLETED` or `FAILED`. Do not poll the extraction trigger endpoint.

## Tests And Accuracy

```bash
PYTHONPATH=. pytest
PYTHONPATH=. python scripts/score_accuracy.py \
  tests/ground_truth/health_claim_form.json actual-result.json
```

Run every supported sample through a running API and worker, saving timestamped
raw responses, extraction JSON, processing events, human-readable field tables,
and accuracy reports:

```bash
PYTHONPATH=. python scripts/test_corpus.py
```

Results are saved under `../test-results/<timestamp>/summary.md`, with one folder
per source document.

Release gates are at least 90% normalized typed-field accuracy and 75%
handwritten-field accuracy over approved annotations. The photographed sample
forms still require human-approved handwritten ground truth before that gate can
be measured honestly.

## Docker

The recommended full-stack command runs from the repository root and includes
automatic first-run OCR model provisioning:

```bash
docker compose up --build --wait
```

The `model-init` service downloads required PaddleOCR and TrOCR assets into a
persistent named volume, then exits. API and worker services start only after
model provisioning succeeds. Later starts reuse the volume and can run offline.

The backend-only Compose file remains available for development with manually
provisioned assets:

```bash
cp .env.example .env
docker compose up --build
```

The Compose stack runs API and worker separately while sharing SQLite, temporary
storage, logs, and read-only local models. The image installs both
`requirements.txt` and `requirements-models.txt`; the build fails immediately
if PaddleOCR, PaddlePaddle, Torch, or Transformers cannot be imported.

Provision `models/paddlex` and `models/trocr-handwritten` before starting the
stack. Docker build context excludes the large local model directory because
Compose mounts it at runtime.

```bash
docker compose build
docker compose up -d
docker compose ps
curl http://localhost:8000/api/v1/health/ready
docker compose logs --tail=100 api worker
```

## Operational Notes

- Default upload limit: 50 MB.
- Default PDF limit: 100 pages.
- Default job timeout: 15 minutes.
- Default attempts: 2.
- Readiness: `/api/v1/health/ready`.
- Liveness: `/api/v1/health/live`.
- Metrics: `/api/v1/metrics`.
- Processing events intentionally exclude extracted values and other document PII.
