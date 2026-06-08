# Backend Requirements Traceability

| Requirement | Implementation | Verification |
|---|---|---|
| Accept images and PDFs | Streaming `/api/v1/upload`, `IngestionService` | `test_ingestion.py` |
| Secure temporary storage | UUID filenames, content validation, terminal cleanup | `test_ingestion.py`, `test_worker.py` |
| Multi-page PDFs | Incremental page rendering | preprocessing integration test |
| Printed OCR | PaddleOCR with Tesseract fallback | OCR adapter and golden tests |
| Handwritten OCR | Offline local TrOCR adapter | model verification and handwritten corpus |
| No cloud/LLM usage | Local-only engine adapters, offline model path | deployment review |
| No fabricated output | OCR failures become failed jobs | `test_ocr.py` |
| Layout and field-value mapping | Schemas plus spatial/generic extraction | `test_extraction.py`, golden tests |
| Structured JSON | Versioned extraction response schema | API lifecycle tests |
| Temporary-file cleanup | Worker `finally`-equivalent terminal cleanup and delete endpoint | `test_worker.py` |
| Concurrent requests | Separate API and persistent worker queue, SQLite WAL | job/storage concurrency tests |
| API documentation | FastAPI OpenAPI, frontend integration contract, and operating guide | `/docs` smoke test and frontend contract review |
| Deployment guide | Docker Compose and backend README | deployment smoke test |
