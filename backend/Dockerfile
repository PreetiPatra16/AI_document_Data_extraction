FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr libtesseract-dev libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY requirements.txt requirements-models.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt -r requirements-models.txt \
    && python -c "import paddle, paddleocr, torch, transformers; print('OCR Python dependencies verified')"

COPY . .
RUN mkdir -p /app/storage /app/temp_uploads /app/logs /app/models \
    && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
