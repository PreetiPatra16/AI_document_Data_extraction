import os
import re
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings, settings
from app.middleware.error_handler import ValidationException

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from pdf2image import pdfinfo_from_path
except ImportError:
    pdfinfo_from_path = None


ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}


class IngestionService:
    def __init__(self, config: Settings = settings):
        self.settings = config
        config.temp_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        name = Path(filename or "upload").name
        return re.sub(r"[^A-Za-z0-9._ -]", "_", name)[:255]

    async def save_and_validate(self, file: UploadFile, document_id: str) -> Tuple[str, str, int, int, str]:
        filename = self.sanitize_filename(file.filename or "")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_TYPES:
            raise ValidationException("Unsupported file type.", details={"allowed_extensions": sorted(ALLOWED_TYPES)})
        path = self.settings.temp_dir / f"{document_id}{ext}"
        size = 0
        try:
            with path.open("wb") as output:
                while chunk := await file.read(self.settings.upload_chunk_bytes):
                    size += len(chunk)
                    if size > self.settings.max_upload_bytes:
                        raise ValidationException("File exceeds maximum upload size.", status_code=413)
                    output.write(chunk)
            if size == 0:
                raise ValidationException("Empty files are not allowed.")
            page_count, detected_type = self._validate_content(path, ext)
            return filename, str(path), size, page_count, detected_type
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

    def _validate_content(self, path: Path, ext: str) -> Tuple[int, str]:
        header = path.read_bytes()[:16]
        if not any(header.startswith(signature) for signature in SIGNATURES[ext]):
            raise ValidationException("File content does not match its extension.")
        if ext == ".pdf":
            try:
                if PdfReader is not None:
                    reader = PdfReader(str(path))
                    if reader.is_encrypted:
                        raise ValidationException("Encrypted PDFs are not supported.")
                    count = len(reader.pages)
                elif pdfinfo_from_path is not None:
                    count = int(pdfinfo_from_path(str(path))["Pages"])
                else:
                    raise ValidationException("PDF validation dependency is unavailable.", status_code=503)
            except ValidationException:
                raise
            except Exception as exc:
                raise ValidationException("PDF is corrupt or unreadable.") from exc
            if count == 0:
                raise ValidationException("PDF contains no pages.")
            if count > self.settings.max_pdf_pages:
                raise ValidationException("PDF exceeds maximum page count.", status_code=413)
            return count, ALLOWED_TYPES[ext]
        try:
            with Image.open(path) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValidationException("Image is corrupt or unreadable.") from exc
        return 1, ALLOWED_TYPES[ext]

    def cleanup_document_files(self, document_id: str, preserve_path: str | None = None) -> None:
        for path in self.settings.temp_dir.glob(f"{document_id}*"):
            if path.is_file() and str(path) != preserve_path:
                path.unlink(missing_ok=True)

    def cleanup_orphans(self, referenced_paths: set[str]) -> int:
        cutoff = __import__("time").time() - self.settings.orphan_max_age_hours * 3600
        removed = 0
        for path in self.settings.temp_dir.iterdir():
            if path.is_file() and str(path) not in referenced_paths and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        return removed
