# DocuExtract Frontend

React operator workspace for the local document extraction backend. The frontend
stages document batches in the browser, queues extraction through the existing
single-document API, monitors processing, and presents retained structured
results.

## Product Flow

1. Select one or more PDF, JPG, JPEG, or PNG files.
2. Inspect session-only previews before processing.
3. Start the batch explicitly.
4. Upload and process up to three documents concurrently.
5. Inspect normalized fields, confidence, warnings, tables, and processing
   events.
6. Download individual or combined JSON results.
7. Delete retained result metadata from history when it is no longer needed.

The backend deletes original and generated document files after terminal
processing. Local previews therefore exist only while the browser retains the
selected `File` objects. Refresh recovery restores document and job references,
but not source previews or document contents.

## Run Locally

Start the backend API and worker first, then run:

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000/api/v1 npm run dev
```

Open `http://localhost:3000`.

The API URL defaults to `http://localhost:8000/api/v1` when `VITE_API_URL` is
not set.

## Run With Docker

The recommended full-stack command is run from the repository root:

```bash
docker compose up --build --wait
```

The frontend Nginx container proxies `/api/` to the Compose API service, so it
works through the same browser host on Windows, Linux, macOS, and remote Docker
hosts.

Stop the full stack with:

```bash
docker compose down
```

When running Vite directly, set `VITE_API_URL` because the development server
does not use the production Nginx proxy.

## Commands

```bash
npm run dev      # Start the Vite development server
npm test         # Run focused Vitest tests
npm run build    # Type-check and create a production build
npm run preview  # Preview the production build
```

## Routes

| Route | Purpose |
|---|---|
| `/` | Batch staging, preview, queue progress, and batch export |
| `/history` | Search, inspect, download, and delete retained records |
| `/documents/:documentId` | Read-only extraction result and processing events |
| `/diagnostics` | Backend health, readiness, and local dependency status |

## Architecture

- **React Router** owns page navigation.
- **React Query** owns backend records, health requests, and detail polling.
- **Zustand** owns browser-session batch files, preview URLs, recovery
  references, and theme preference.
- **Axios** implements the backend integration contract and structured error
  parsing.
- **React PDF** renders session-only PDF previews.

Important modules:

```text
src/
├── components/       Reusable shell, preview, status, result, and event UI
├── pages/            Workspace, history, detail, and diagnostics routes
├── services/api.ts   Backend client and error-envelope parsing
├── store/            Session batch state and refresh recovery references
├── types/            Backend and frontend workflow contracts
└── utils/            Batch concurrency, validation, formatting, and export
```

## Backend Integration Rules

- Accepted files: PDF, JPG, JPEG, and PNG, up to 50 MB each.
- Extraction flow: upload, queue extraction, poll job, then fetch document.
- Active states: `QUEUED` and `PROCESSING`.
- Terminal states: `COMPLETED`, `FAILED`, and job-level `CANCELLED`.
- If a job ID is unavailable, the frontend polls the document record.
- Failed or completed documents cannot be retried without uploading the source
  again.
- API errors use `error.code`, `error.message`, `error.details`, and
  `error.request_id`.
- Extracted values are read-only. Prefer `normalized_value`, then fall back to
  `value`.
- Do not expose `raw_text` in the operator UI.

See [`../backend/docs/frontend-integration.md`](../backend/docs/frontend-integration.md)
for the full API contract.

## Testing Notes

Focused tests currently cover:

- Supported format and size validation
- Combined batch export shape
- Three-at-a-time concurrency limiting
- API error-envelope parsing
- Preview URL cleanup

Before merging frontend changes, run:

```bash
cd frontend
npm test
npm run build
```

For an integration smoke test, run the backend API and worker, process a small
image and a PDF, then verify successful and failed records in history.
