# AI-Based Document Data Extraction System

An enterprise-grade document data extraction suite designed to process scanned documents, printed forms, mixed printed/handwritten content, and PDFs, running entirely locally on a single machine with zero external cloud dependencies

## One-Command Docker Startup

Install Docker Desktop on Windows or macOS, or Docker Engine with the Compose
plugin on Linux. From the repository root, run:

```bash
docker compose up --build --wait
```

Allocate at least 8 GB of memory and enough disk space for the backend image,
OCR dependencies, and model cache.

Then open:

- Frontend: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`

The first startup downloads the required PaddleOCR and TrOCR model assets into
the persistent `docuextract_ocr_models` Docker volume. This download is roughly
1.4 GB and requires internet access. Later starts reuse the cached models and
can run offline.

Convenience launchers are also available:

```bash
# macOS / Linux
./start.sh

# Windows PowerShell
.\start.ps1
```

Stop the stack without deleting retained results or models:

```bash
docker compose down
```

If ports `3000` or `8000` are already in use, choose different host ports:

```bash
# macOS / Linux
FRONTEND_PORT=3100 API_PORT=8100 docker compose up --build --wait

# Windows PowerShell
$env:FRONTEND_PORT="3100"; $env:API_PORT="8100"; docker compose up --build --wait
```

To deliberately remove retained result metadata, logs, and downloaded models:

```bash
docker compose down --volumes
```

## Key Design Principles & Architecture

The codebase follows **Clean Architecture** patterns, decoupling storage, computer vision, text recognition, and field parsing layers into individual modules:

- **CV Preprocessing Service (`preprocessing_service.py`)**: Uses OpenCV to deskew (minAreaRect box rotation), denoise (fastNlMeansDenoising), and threshold (adaptiveThreshold) inputs to maximize local OCR recognition accuracy.
- **Local OCR Engine Core (`ocr_service.py`)**: Automatically selects **PaddleOCR** as primary (highly effective for mixed and handwritten lines) with a secondary fallback to **Tesseract** if OCR confidence ratings drop.
- **Audit Field Extractor Service (`extraction_service.py`)**: To mitigate risks associated with dynamic layouts in V1, a template-matching label router maps coordinates, applies regular expressions, and returns strict confidence ratings computed as:
  $$\text{Confidence} = (\text{OCR\_Confidence} \times 0.4) + (\text{Regex\_Match} \times 0.3) + (\text{Proximity\_Distance\_Factor} \times 0.3)$$
- **Operator Workspace (React / TypeScript)**: Stages document batches, provides session-only previews, limits concurrent processing, monitors jobs, and presents retained extraction results without implying that source documents remain stored.

Frontend setup, routes, architecture, and integration rules are documented in
[`frontend/README.md`](frontend/README.md).

---

## Folder Structure

```
AI_doc_extraction_sys/
├─ backend/
│  ├─ app/
│  │   ├─ api/
│  │   │   ├─ v1/
│  │   │   │   ├─ endpoints/
│  │   │   │   │   ├─ upload.py         # POST /api/v1/upload
│  │   │   │   │   ├─ extraction.py     # POST /api/v1/extract/{doc_id}
│  │   │   │   │   └─ document.py       # GET /api/v1/document/{doc_id}
│  │   │   │   └─ health.py             # GET /api/v1/health
│  │   │   └─ dependencies.py           # Dependency Injection setup
│  │   ├─ core/
│  │   │   ├─ services/
│  │   │   │   ├─ storage_service.py
│  │   │   │   ├─ preprocessing_service.py
│  │   │   │   ├─ ocr_service.py
│  │   │   │   └─ extraction_service.py
│  │   │   └─ workers/
│  │   │       └─ extraction_worker.py  # Background task pipeline runner
│  │   ├─ middleware/
│  │   │   ├─ error_handler.py          # Central HTTP exceptions mapping
│  │   │   └─ logging_middleware.py      # HTTP request loguru outputs
│  │   ├─ schemas/
│  │   │   ├─ upload.py
│  │   │   └─ document.py
│  │   ├─ utils/
│  │   │   └─ logger.py
│  │   └─ main.py
│  ├─ Dockerfile
│  ├─ docker-compose.yml
│  ├─ requirements.txt
│  ├─ .env.example
│  └─ README.md
├─ frontend/
│  ├─ src/
│  │   ├─ components/
│  │   │   ├─ AppShell.tsx
│  │   │   ├─ LocalPreview.tsx
│  │   │   ├─ ExtractionPanel.tsx
│  │   │   └─ ProcessingTimeline.tsx
│  │   ├─ pages/
│  │   │   ├─ Workspace.tsx
│  │   │   ├─ History.tsx
│  │   │   ├─ DocumentDetail.tsx
│  │   │   └─ Diagnostics.tsx
│  │   ├─ store/
│  │   │   └─ documentStore.ts
│  │   ├─ services/
│  │   │   └─ api.ts
│  │   ├─ types/
│  │   │   └─ index.ts
│  │   ├─ utils/
│  │   │   ├─ batch.ts
│  │   │   └─ files.ts
│  │   ├─ App.tsx
│  │   ├─ main.tsx
│  │   └─ index.css
│  ├─ Dockerfile
│  ├─ package.json
│  ├─ tailwind.config.js
│  ├─ vite.config.ts
│  └─ tsconfig.json
├─ compose.yaml
├─ start.sh
├─ start.ps1
├─ stop.sh
├─ stop.ps1
└─ README.md
```

---

## Production Readiness Upgrade Path

While this system functions out-of-the-box as a self-contained local workspace, enterprise deployment demands the following adaptations:

1. **Database Tier**: Replace the portable local SQLite instance inside `storage_service.py` with an external **PostgreSQL** instance to handle concurrent read-writes and support transaction lock patterns.
2. **Worker Scaling**: FastAPI's in-process `BackgroundTasks` executes on the event loop. Swap this in `extraction_worker.py` for a dedicated **Celery** or **Arq** setup powered by a **Redis** or **RabbitMQ** broker to scale task workers independently.
3. **Blob Storage**: Transition document assets from the local filesystem to an object store like **AWS S3** or local **MinIO** buckets.
4. **Handwriting Optimization**: To extract complex cursive handwriting beyond basic detection, run custom deep-learning layout models (such as TroCR or LayoutLMv3) on discrete GPU nodes.
