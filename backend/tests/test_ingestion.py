import io

import pytest
from fastapi import UploadFile
from PIL import Image

from app.middleware.error_handler import ValidationException


def png_bytes():
    stream = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(stream, format="PNG")
    return stream.getvalue()


@pytest.mark.asyncio
async def test_valid_image_is_streamed_and_validated(configured_services):
    _, _, ingestion = configured_services
    upload = UploadFile(filename="safe.png", file=io.BytesIO(png_bytes()))
    filename, path, size, pages, mime = await ingestion.save_and_validate(upload, "doc")
    assert filename == "safe.png"
    assert size > 0 and pages == 1 and mime == "image/png"


@pytest.mark.asyncio
async def test_empty_and_fake_files_are_rejected(configured_services):
    _, _, ingestion = configured_services
    with pytest.raises(ValidationException):
        await ingestion.save_and_validate(UploadFile(filename="fake.png", file=io.BytesIO(b"not png")), "fake")
