import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import Settings, settings
from app.core.domain import (
    ACTIVE_JOB_STATUSES,
    DOCUMENT_TRANSITIONS,
    DocumentStatus,
    FailureCode,
    JobStatus,
)
from app.middleware.error_handler import ConflictException, StorageException


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class StorageService:
    def __init__(self, config: Settings = settings):
        self.settings = config
        self.storage_dir = str(config.storage_dir)
        self.temp_dir = str(config.temp_dir)
        self.db_path = str(config.db_path)
        config.storage_dir.mkdir(parents=True, exist_ok=True)
        config.temp_dir.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            yield conn
        finally:
            conn.close()

    def _migrate(self) -> None:
        migrations = [
            """
            CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS documents(
                id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0, page_count INTEGER NOT NULL DEFAULT 1,
                source_path TEXT, source_available INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL, current_stage TEXT, progress INTEGER NOT NULL DEFAULT 0,
                uploaded_at TEXT NOT NULL, updated_at TEXT NOT NULL, extracted_data TEXT,
                processing_time_ms INTEGER, failure_code TEXT, failure_message TEXT
            );
            CREATE TABLE IF NOT EXISTS extraction_jobs(
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                status TEXT NOT NULL, stage TEXT, progress INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 2,
                worker_id TEXT, created_at TEXT NOT NULL, started_at TEXT, heartbeat_at TEXT,
                finished_at TEXT, failure_code TEXT, failure_message TEXT
            );
            CREATE TABLE IF NOT EXISTS processing_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                job_id TEXT REFERENCES extraction_jobs(id) ON DELETE CASCADE,
                stage TEXT NOT NULL, status TEXT NOT NULL, progress INTEGER NOT NULL,
                timestamp TEXT NOT NULL, details TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON extraction_jobs(status, created_at);
            CREATE INDEX IF NOT EXISTS idx_events_document ON processing_events(document_id, id);
            """
        ]
        try:
            with self.get_connection() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY)")
                current = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
                for version, sql in enumerate(migrations, start=1):
                    if version > current:
                        conn.executescript(sql)
                        conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
                self._upgrade_legacy_documents(conn)
                conn.commit()
        except Exception as exc:
            raise StorageException(f"Database migration failed: {exc}") from exc

    def _upgrade_legacy_documents(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
        additions = {
            "file_size": "INTEGER NOT NULL DEFAULT 0",
            "page_count": "INTEGER NOT NULL DEFAULT 1",
            "source_path": "TEXT",
            "source_available": "INTEGER NOT NULL DEFAULT 1",
            "current_stage": "TEXT",
            "progress": "INTEGER NOT NULL DEFAULT 0",
            "updated_at": "TEXT",
            "failure_code": "TEXT",
            "failure_message": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {definition}")
        conn.execute("UPDATE documents SET updated_at=uploaded_at WHERE updated_at IS NULL")

    def create_document_record(
        self, doc_id: str, filename: str, file_type: str, file_size: int = 0,
        page_count: int = 1, source_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = utcnow()
        with self.get_connection() as conn:
            conn.execute(
                """INSERT INTO documents(
                    id, filename, file_type, file_size, page_count, source_path, status, uploaded_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, filename, file_type, file_size, page_count, source_path, DocumentStatus.UPLOADED.value, now, now),
            )
            conn.commit()
        return self.get_document_record(doc_id)

    def _document_from_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        record = dict(row)
        record["source_available"] = bool(record["source_available"])
        record["extracted_data"] = json.loads(record["extracted_data"]) if record["extracted_data"] else None
        record["logs"] = self.get_events(record["id"])
        record.pop("source_path", None)
        return record

    def get_document_record(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        return self._document_from_row(row) if row else None

    def get_document_source(self, doc_id: str) -> Optional[str]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT source_path FROM documents WHERE id=?", (doc_id,)).fetchone()
        return row["source_path"] if row else None

    def get_all_document_records(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [self._document_from_row(row) for row in rows]

    def transition_document(self, doc_id: str, target: DocumentStatus, **updates: Any) -> None:
        with self.get_connection() as conn:
            row = conn.execute("SELECT status FROM documents WHERE id=?", (doc_id,)).fetchone()
            if not row:
                raise StorageException("Document does not exist.", status_code=404)
            current = DocumentStatus(row["status"])
            if target != current and target not in DOCUMENT_TRANSITIONS[current]:
                raise ConflictException(f"Illegal document transition: {current.value} -> {target.value}")
            columns = {"status": target.value, "updated_at": utcnow(), **updates}
            parts, params = [], []
            for key, value in columns.items():
                if key == "extracted_data" and value is not None:
                    value = json.dumps(value)
                parts.append(f"{key}=?")
                params.append(value)
            params.append(doc_id)
            conn.execute(f"UPDATE documents SET {', '.join(parts)} WHERE id=?", params)
            conn.commit()

    def create_job(self, document_id: str) -> Dict[str, Any]:
        job_id, now = str(uuid.uuid4()), utcnow()
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            doc = conn.execute("SELECT status, source_available FROM documents WHERE id=?", (document_id,)).fetchone()
            if not doc:
                raise StorageException("Document not found.", status_code=404)
            if not doc["source_available"]:
                raise StorageException("Source file is no longer available.", status_code=410)
            active = conn.execute(
                "SELECT id FROM extraction_jobs WHERE document_id=? AND status IN (?,?)",
                (document_id, *ACTIVE_JOB_STATUSES),
            ).fetchone()
            if active:
                raise ConflictException("An extraction job is already active for this document.")
            conn.execute(
                """INSERT INTO extraction_jobs(id, document_id, status, max_attempts, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (job_id, document_id, JobStatus.QUEUED.value, self.settings.max_job_attempts, now),
            )
            conn.execute(
                """UPDATE documents SET status=?, current_stage=?, progress=0, failure_code=NULL,
                   failure_message=NULL, updated_at=? WHERE id=?""",
                (DocumentStatus.QUEUED.value, "queued", now, document_id),
            )
            conn.commit()
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def claim_next_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        now = utcnow()
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM extraction_jobs WHERE status=? ORDER BY created_at LIMIT 1",
                (JobStatus.QUEUED.value,),
            ).fetchone()
            if not row:
                conn.commit()
                return None
            conn.execute(
                """UPDATE extraction_jobs SET status=?, worker_id=?, attempts=attempts+1,
                   started_at=COALESCE(started_at, ?), heartbeat_at=? WHERE id=?""",
                (JobStatus.PROCESSING.value, worker_id, now, now, row["id"]),
            )
            conn.execute(
                "UPDATE documents SET status=?, current_stage=?, progress=1, updated_at=? WHERE id=?",
                (DocumentStatus.PROCESSING.value, "validation", now, row["document_id"]),
            )
            conn.commit()
        return self.get_job(row["id"])

    def update_job_progress(self, job_id: str, stage: str, progress: int, details: str = "") -> None:
        progress = min(99, max(0, progress))
        now = utcnow()
        with self.get_connection() as conn:
            row = conn.execute("SELECT document_id, progress FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                raise StorageException("Job not found.", status_code=404)
            progress = max(progress, row["progress"])
            conn.execute(
                "UPDATE extraction_jobs SET stage=?, progress=?, heartbeat_at=? WHERE id=?",
                (stage, progress, now, job_id),
            )
            conn.execute(
                "UPDATE documents SET current_stage=?, progress=?, updated_at=? WHERE id=?",
                (stage, progress, now, row["document_id"]),
            )
            conn.execute(
                """INSERT INTO processing_events(document_id, job_id, stage, status, progress, timestamp, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (row["document_id"], job_id, stage, JobStatus.PROCESSING.value, progress, now, details),
            )
            conn.commit()

    def complete_job(self, job_id: str, result: Dict[str, Any], processing_time_ms: int) -> None:
        now = utcnow()
        with self.get_connection() as conn:
            row = conn.execute("SELECT document_id FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
            conn.execute(
                """UPDATE extraction_jobs SET status=?, stage=?, progress=100, finished_at=?, heartbeat_at=?,
                   failure_code=NULL, failure_message=NULL WHERE id=?""",
                (JobStatus.COMPLETED.value, "cleanup", now, now, job_id),
            )
            conn.execute(
                """UPDATE documents SET status=?, current_stage=?, progress=100, extracted_data=?,
                   processing_time_ms=?, source_available=0, source_path=NULL, failure_code=NULL,
                   failure_message=NULL, updated_at=? WHERE id=?""",
                (DocumentStatus.COMPLETED.value, "cleanup", json.dumps(result), processing_time_ms, now, row["document_id"]),
            )
            conn.execute(
                """INSERT INTO processing_events(document_id, job_id, stage, status, progress, timestamp, details)
                   VALUES (?, ?, ?, ?, 100, ?, ?)""",
                (row["document_id"], job_id, "cleanup", JobStatus.COMPLETED.value, now, "Processing completed."),
            )
            conn.commit()

    def fail_job(self, job_id: str, code: FailureCode, message: str, processing_time_ms: int = 0) -> None:
        now = utcnow()
        with self.get_connection() as conn:
            row = conn.execute("SELECT document_id FROM extraction_jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return
            conn.execute(
                """UPDATE extraction_jobs SET status=?, finished_at=?, failure_code=?, failure_message=? WHERE id=?""",
                (JobStatus.FAILED.value, now, code.value, message, job_id),
            )
            conn.execute(
                """UPDATE documents SET status=?, failure_code=?, failure_message=?, processing_time_ms=?,
                   source_available=0, source_path=NULL, updated_at=? WHERE id=?""",
                (DocumentStatus.FAILED.value, code.value, message, processing_time_ms, now, row["document_id"]),
            )
            conn.execute(
                """INSERT INTO processing_events(document_id, job_id, stage, status, progress, timestamp, details)
                   VALUES (?, ?, ?, ?, 100, ?, ?)""",
                (row["document_id"], job_id, "cleanup", JobStatus.FAILED.value, now, message),
            )
            conn.commit()

    def retry_job(self, job_id: str, code: FailureCode, message: str) -> bool:
        now = utcnow()
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT document_id, attempts, max_attempts FROM extraction_jobs WHERE id=?",
                (job_id,),
            ).fetchone()
            if not row or row["attempts"] >= row["max_attempts"]:
                conn.commit()
                return False
            conn.execute(
                """UPDATE extraction_jobs SET status=?, stage=?, progress=0, worker_id=NULL,
                   heartbeat_at=?, failure_code=?, failure_message=? WHERE id=?""",
                (JobStatus.QUEUED.value, "retrying", now, code.value, message, job_id),
            )
            conn.execute(
                """UPDATE documents SET status=?, current_stage=?, progress=0, updated_at=? WHERE id=?""",
                (DocumentStatus.QUEUED.value, "retrying", now, row["document_id"]),
            )
            conn.execute(
                """INSERT INTO processing_events(document_id, job_id, stage, status, progress, timestamp, details)
                   VALUES (?, ?, ?, ?, 0, ?, ?)""",
                (row["document_id"], job_id, "retrying", JobStatus.QUEUED.value, now, message),
            )
            conn.commit()
            return True

    def recover_abandoned_jobs(self) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=self.settings.job_timeout_seconds)).isoformat()
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, document_id, attempts, max_attempts FROM extraction_jobs WHERE status=? AND heartbeat_at<?",
                (JobStatus.PROCESSING.value, cutoff),
            ).fetchall()
            for row in rows:
                if row["attempts"] < row["max_attempts"]:
                    conn.execute(
                        "UPDATE extraction_jobs SET status=?, worker_id=NULL, stage=NULL, progress=0 WHERE id=?",
                        (JobStatus.QUEUED.value, row["id"]),
                    )
                    conn.execute(
                        "UPDATE documents SET status=?, current_stage=?, progress=0 WHERE id=?",
                        (DocumentStatus.QUEUED.value, "queued", row["document_id"]),
                    )
                else:
                    conn.execute(
                        "UPDATE extraction_jobs SET status=?, failure_code=?, failure_message=?, finished_at=? WHERE id=?",
                        (JobStatus.FAILED.value, FailureCode.JOB_TIMEOUT.value, "Job exceeded retry limit.", utcnow(), row["id"]),
                    )
            conn.commit()
        return len(rows)

    def get_events(self, document_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT stage, status, progress, timestamp, details FROM processing_events WHERE document_id=? ORDER BY id",
                (document_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_document_record(self, doc_id: str) -> None:
        source = self.get_document_source(doc_id)
        if source:
            Path(source).unlink(missing_ok=True)
        for path in Path(self.temp_dir).glob(f"{doc_id}*"):
            if path.is_file():
                path.unlink(missing_ok=True)
        with self.get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            conn.commit()

    def queue_depth(self) -> int:
        with self.get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM extraction_jobs WHERE status=?", (JobStatus.QUEUED.value,)).fetchone()[0]

    def referenced_source_paths(self) -> set[str]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT source_path FROM documents WHERE source_path IS NOT NULL").fetchall()
        return {row["source_path"] for row in rows}
