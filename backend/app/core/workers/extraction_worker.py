import asyncio
import os
import socket
import time
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from app.api.dependencies import (
    get_extraction_service,
    get_ingestion_service,
    get_ocr_service,
    get_preprocessing_service,
    get_storage_service,
)
from app.core.config import settings
from app.core.domain import FailureCode, PipelineStage
from app.middleware.error_handler import ExtractionException, OCRException, PreprocessingException
from app.utils.logger import setup_logger


class ExtractionWorker:
    def __init__(self):
        self.storage = get_storage_service()
        self.ingestion = get_ingestion_service()
        self.preprocessing = get_preprocessing_service()
        self.ocr = get_ocr_service()
        self.extraction = get_extraction_service()
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"

    async def run_once(self) -> bool:
        job = self.storage.claim_next_job(self.worker_id)
        if not job:
            return False
        logger.info(
            "Worker claimed job_id={} document_id={} attempt={}/{}",
            job["id"], job["document_id"], job["attempts"], job["max_attempts"],
        )
        await self._run_with_timeout(job)
        return True

    async def _run_with_timeout(self, job: Dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(self._process(job), timeout=settings.job_timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(
                "Job timed out job_id={} document_id={} timeout_seconds={}",
                job["id"], job["document_id"], settings.job_timeout_seconds,
            )
            self._cleanup(job["document_id"])
            self.storage.fail_job(job["id"], FailureCode.JOB_TIMEOUT, "Extraction exceeded the configured timeout.")

    async def _process(self, job: Dict[str, Any]) -> None:
        start = time.monotonic()
        document_id = job["document_id"]
        source_path = self.storage.get_document_source(document_id)
        try:
            logger.info("Job started job_id={} document_id={}", job["id"], document_id)
            if not source_path or not Path(source_path).exists():
                raise FileNotFoundError("Source file is unavailable.")
            self.storage.update_job_progress(job["id"], PipelineStage.VALIDATION.value, 5, "Source validated.")
            self.storage.update_job_progress(job["id"], PipelineStage.RENDERING.value, 12, "Rendering pages incrementally.")
            pages = await self.preprocessing.preprocess_document(source_path, document_id)
            self.storage.update_job_progress(
                job["id"], PipelineStage.PREPROCESSING.value, 30, f"Prepared {len(pages)} page(s)."
            )
            blocks = []
            for index, page in enumerate(pages):
                page_blocks = await self.ocr.perform_ocr_multi_variant(page["variants"], page["page"])
                if self.ocr.trocr:
                    page_blocks = self._upgrade_low_confidence(page_blocks, page["variants"].get("original", ""))
                blocks.extend(page_blocks)
                progress = 30 + int(((index + 1) / len(pages)) * 40)
                self.storage.update_job_progress(
                    job["id"], PipelineStage.OCR.value, progress, f"OCR completed for {index + 1}/{len(pages)} page(s)."
                )
            self.storage.update_job_progress(job["id"], PipelineStage.CLASSIFICATION.value, 75, "Classifying document.")
            self.storage.update_job_progress(job["id"], PipelineStage.EXTRACTION.value, 82, "Extracting structured fields.")
            result = await self.extraction.extract_data(blocks)
            result["warnings"] = sorted(set(result["warnings"] + [warning for page in pages for warning in page["warnings"]]))
            self.storage.update_job_progress(job["id"], PipelineStage.NORMALIZATION.value, 92, "Normalizing extracted fields.")
            self.storage.update_job_progress(job["id"], PipelineStage.CLEANUP.value, 98, "Removing temporary document files.")
            self._cleanup(document_id)
            elapsed = int((time.monotonic() - start) * 1000)
            self.storage.complete_job(job["id"], result, elapsed)
            logger.info("Job completed job_id={} document_id={} duration_ms={}", job["id"], document_id, elapsed)
        except FileNotFoundError:
            self._fail(job, FailureCode.SOURCE_FILE_MISSING, "Source file is unavailable.", start)
        except PreprocessingException:
            self._fail(job, FailureCode.RENDERING_FAILED, "Document rendering or preprocessing failed.", start)
        except OCRException as exc:
            self._fail(job, FailureCode.OCR_FAILED, exc.message, start, exc, retryable=True)
        except ExtractionException as exc:
            self._fail(job, FailureCode.EXTRACTION_FAILED, exc.message, start, exc)
        except Exception as exc:
            self._fail(
                job,
                FailureCode.INTERNAL_ERROR,
                f"Unexpected {type(exc).__name__} during document processing.",
                start,
                exc,
                retryable=True,
            )

    def _fail(
        self,
        job: Dict[str, Any],
        code: FailureCode,
        message: str,
        start: float,
        exc: Exception = None,
        retryable: bool = False,
    ) -> None:
        current = self.storage.get_job(job["id"]) or {}
        if exc:
            logger.opt(exception=exc).error(
                "Job failed job_id={} document_id={} stage={} code={} message={}",
                job["id"], job["document_id"], current.get("stage"), code.value, message,
            )
        else:
            logger.error(
                "Job failed job_id={} document_id={} stage={} code={} message={}",
                job["id"], job["document_id"], current.get("stage"), code.value, message,
            )
        if retryable and self.storage.retry_job(job["id"], code, message):
            source_path = self.storage.get_document_source(job["document_id"])
            self.ingestion.cleanup_document_files(job["document_id"], preserve_path=source_path)
            logger.warning(
                "Job requeued job_id={} document_id={} code={} next_attempt={}",
                job["id"], job["document_id"], code.value, job["attempts"] + 1,
            )
            return
        self._cleanup(job["document_id"])
        self.storage.fail_job(job["id"], code, message, int((time.monotonic() - start) * 1000))

    def _upgrade_low_confidence(self, blocks, original_image_path: str):
        """Re-run TrOCR on blocks with low OCR confidence and replace text when the result is non-empty."""
        if not original_image_path:
            return blocks
        upgraded = []
        for block in blocks:
            if block["confidence"] < 0.5 and block.get("text", "").strip():
                try:
                    result = self.ocr.recognize_handwriting_region(original_image_path, block["bounding_box"])
                    if result["text"]:
                        block = {**block, "text": result["text"], "source_engine": "trocr", "confidence": result["confidence"]}
                        logger.info(
                            "TrOCR upgrade page={} original_engine={} new_text={}",
                            block["page"], block.get("source_engine"), result["text"][:40],
                        )
                except Exception:
                    pass
            upgraded.append(block)
        return upgraded

    def _cleanup(self, document_id: str) -> None:
        self.ingestion.cleanup_document_files(document_id)

    async def serve(self) -> None:
        logger.info(
            "Worker starting worker_id={} concurrency={} capabilities={}",
            self.worker_id, settings.worker_concurrency, self.ocr.capabilities(),
        )
        self.storage.recover_abandoned_jobs()
        self.ingestion.cleanup_orphans(self.storage.referenced_source_paths())
        await asyncio.gather(*(self._poll_loop() for _ in range(settings.worker_concurrency)))

    async def _poll_loop(self) -> None:
        while True:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(settings.worker_poll_seconds)


async def run_extraction_pipeline(document_id: str, file_path: str):
    """Compatibility helper for older callers. Queue processing should use the worker service."""
    storage = get_storage_service()
    job = storage.create_job(document_id)
    await ExtractionWorker()._run_with_timeout(job)


if __name__ == "__main__":
    setup_logger()
    asyncio.run(ExtractionWorker().serve())
