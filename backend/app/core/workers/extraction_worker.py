import time
from datetime import datetime
from loguru import logger
from app.api.dependencies import (
    get_storage_service,
    get_preprocessing_service,
    get_ocr_service,
    get_extraction_service
)

async def run_extraction_pipeline(document_id: str, file_path: str):
    """
    Executes the entire document extraction pipeline asynchronously:
    1. File Ingestion & PDF Conversion
    2. OpenCV Image Preprocessing
    3. OCR execution
    4. Template layout/field extraction
    5. JSON Normalization & SQLite Storage update
    """
    logger.info(f"Worker starting pipeline for document ID: {document_id}")
    
    storage = get_storage_service()
    preprocessing = get_preprocessing_service()
    ocr = get_ocr_service()
    extraction = get_extraction_service()
    
    logs = []
    
    def log_stage(stage: str, status: str, details: str = ""):
        log_entry = {
            "stage": stage,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }
        logs.append(log_entry)
        storage.update_document_record(document_id, status=status, logs=logs)
        logger.info(f"[{status}] {stage}: {details}")

    start_time = time.time()
    
    try:
        # Stage 1: Ingestion & Preprocessing
        log_stage("File Ingestion & Conversion", "PROCESSING", f"Reading document from temporary path: {file_path}")
        
        # In case we have a large PDF or image, this converts/deskews/thresholds it.
        preprocessed_images = await preprocessing.preprocess_document(file_path)
        log_stage(
            "Image Preprocessing (CV)", 
            "PROCESSING", 
            f"Preprocessed {len(preprocessed_images)} page(s) (deskewed, denoised, thresholded)."
        )
        
        # Stage 2: OCR Execution
        all_ocr_results = []
        log_stage("OCR Execution", "PROCESSING", "Running localized text recognition...")
        
        for idx, img_path in enumerate(preprocessed_images):
            page_num = idx + 1
            page_results = await ocr.perform_ocr(img_path, page_num)
            all_ocr_results.extend(page_results)
            
        log_stage("OCR Execution", "PROCESSING", f"OCR completed. Found {len(all_ocr_results)} text boxes across pages.")
        
        # Stage 3: Field Extraction
        log_stage("Template Layout Extraction", "PROCESSING", "Mapping elements to form labels...")
        extracted_data = await extraction.extract_data(all_ocr_results, file_path)
        
        # Complete Pipeline
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        log_stage(
            "JSON Generation & Cleanup", 
            "COMPLETED", 
            f"Successfully processed document in {processing_time_ms}ms with classification '{extracted_data['document_type']}'"
        )
        
        # Save results to DB
        storage.update_document_record(
            document_id,
            status="COMPLETED",
            extracted_data=extracted_data,
            logs=logs,
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Worker extraction pipeline failed for {document_id}: {str(e)}")
        log_stage("Pipeline Failure", "FAILED", f"Error details: {str(e)}")
        
        storage.update_document_record(
            document_id,
            status="FAILED",
            logs=logs,
            processing_time_ms=processing_time_ms
        )
