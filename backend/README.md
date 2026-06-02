# AI Document Data Extraction System (Backend)

An enterprise-grade document ingestion and extraction pipeline using FastAPI, OpenCV, and local OCR engines.

## Architecture Decisions

- **FastAPI / Async**: Leveraging non-blocking asyncio endpoints for handling multi-page document uploads and status polling.
- **Service-Oriented Design**: Business logic is separated into independent services:
  - `StorageService`: Handles file storage and SQLite (extendable to PostgreSQL).
  - `PreprocessingService`: Uses OpenCV for deskewing, denoising, and thresholding.
  - `OCRService`: PaddleOCR (primary for printed/mixed) with Tesseract (optional fallback).
  - `ExtractionService`: Template-driven key-value mapping and regex-based normalization.
- **Production Roadmap**:
  - SQLite is used for simplicity. In production, swap SQLite with **PostgreSQL**.
  - Background tasks run inside FastAPI. For production, scale with **Celery + Redis/RabbitMQ**.

## Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) binary installed (if running outside Docker).
- [Poppler](https://poppler.freedesktop.org/) installed for PDF-to-image conversion.

## Quick Start (Local Development)

1. Create a virtual environment and install requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Setup Environment Variables:
   ```bash
   cp .env.example .env
   ```

3. Run the development server:
   ```bash
   python app/main.py
   ```
   The API will start on `http://localhost:8000`. You can access the Swagger documentation at `http://localhost:8000/docs`.

## Docker Setup

Ensure you are in the project's backend directory:
```bash
docker-compose up --build
```
This boots both the FastAPI backend (port 8000) and the React frontend (port 3000).
