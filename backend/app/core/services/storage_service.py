import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
from app.middleware.error_handler import StorageException

class StorageService:
    def __init__(self):
        self.storage_dir = os.getenv("STORAGE_DIR", "storage")
        self.temp_dir = os.getenv("TEMP_DIR", "temp_uploads")
        self.db_path = os.path.join(self.storage_dir, "documents.db")
        
        # Ensure directories exist
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize database
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        file_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        uploaded_at TEXT NOT NULL,
                        extracted_data TEXT,
                        logs TEXT,
                        processing_time_ms INTEGER
                    )
                """)
                conn.commit()
            logger.info("SQLite storage database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise StorageException(f"Database initialization failed: {str(e)}")

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    async def save_uploaded_file(self, file_id: str, filename: str, content: bytes) -> str:
        """Saves file content to temporary storage and returns target filepath."""
        try:
            ext = os.path.splitext(filename)[1]
            target_filename = f"{file_id}{ext}"
            file_path = os.path.join(self.temp_dir, target_filename)
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            logger.info(f"File saved to temp storage: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {str(e)}")
            raise StorageException(f"Failed to save file: {str(e)}")

    def create_document_record(self, doc_id: str, filename: str, file_type: str) -> Dict[str, Any]:
        uploaded_at = datetime.utcnow().isoformat()
        status = "PENDING"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO documents (id, filename, file_type, status, uploaded_at) VALUES (?, ?, ?, ?, ?)",
                    (doc_id, filename, file_type, status, uploaded_at)
                )
                conn.commit()
            
            return {
                "id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "status": status,
                "uploaded_at": uploaded_at,
                "extracted_data": None,
                "logs": [],
                "processing_time_ms": 0
            }
        except Exception as e:
            logger.error(f"Failed to create document record: {str(e)}")
            raise StorageException(f"Database insertion failed: {str(e)}")

    def get_document_record(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                record = dict(row)
                record["extracted_data"] = json.loads(record["extracted_data"]) if record["extracted_data"] else None
                record["logs"] = json.loads(record["logs"]) if record["logs"] else []
                # Parse datetime back
                record["uploaded_at"] = datetime.fromisoformat(record["uploaded_at"])
                return record
        except Exception as e:
            logger.error(f"Failed to get document record: {str(e)}")
            raise StorageException(f"Database query failed: {str(e)}")

    def get_all_document_records(self) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = dict(row)
                    record["extracted_data"] = json.loads(record["extracted_data"]) if record["extracted_data"] else None
                    record["logs"] = json.loads(record["logs"]) if record["logs"] else []
                    record["uploaded_at"] = datetime.fromisoformat(record["uploaded_at"])
                    records.append(record)
                return records
        except Exception as e:
            logger.error(f"Failed to get all document records: {str(e)}")
            raise StorageException(f"Database query failed: {str(e)}")

    def update_document_record(self, doc_id: str, status: str, extracted_data: Optional[Dict[str, Any]] = None, logs: Optional[List[Dict[str, Any]]] = None, processing_time_ms: Optional[int] = None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                updates = ["status = ?"]
                params = [status]
                
                if extracted_data is not None:
                    updates.append("extracted_data = ?")
                    params.append(json.dumps(extracted_data))
                if logs is not None:
                    updates.append("logs = ?")
                    params.append(json.dumps(logs))
                if processing_time_ms is not None:
                    updates.append("processing_time_ms = ?")
                    params.append(processing_time_ms)
                
                params.append(doc_id)
                query = f"UPDATE documents SET {', '.join(updates)} WHERE id = ?"
                
                cursor.execute(query, tuple(params))
                conn.commit()
            logger.info(f"Document record {doc_id} updated: status={status}")
        except Exception as e:
            logger.error(f"Failed to update document record: {str(e)}")
            raise StorageException(f"Database update failed: {str(e)}")
            
    def delete_document_record(self, doc_id: str):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.commit()
            logger.info(f"Document record {doc_id} deleted.")
        except Exception as e:
            logger.error(f"Failed to delete document record: {str(e)}")
            raise StorageException(f"Database delete failed: {str(e)}")
