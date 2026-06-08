import asyncio

from app.core.services.extraction_service import ExtractionService


def block(text, x, y, confidence=0.95):
    return {
        "text": text,
        "confidence": confidence,
        "bounding_box": {"x": x, "y": y, "width": 150, "height": 20},
        "page": 1,
        "source_engine": "test",
    }


def test_same_block_removes_label_and_never_returns_label_as_value():
    service = ExtractionService()
    result = asyncio.run(service.extract_data([
        block("CLAIMANT / PATIENT DETAILS", 0, 0),
        block("PERSONAL DETAILS OF EMPLOYEE", 0, 30),
        block("CLAIM DETAILS", 0, 60),
        block("Name of the Patient: Ram Pimple", 0, 100),
    ]))
    field = result["fields"]["patient_name"]
    assert field["value"] == "Ram Pimple"
    assert field["value"] != "Name"


def test_generic_extraction_does_not_return_arbitrary_ocr_blocks():
    result = asyncio.run(ExtractionService().extract_data([block("Plain heading", 0, 0), block("City: Manali", 0, 30)]))
    assert list(result["fields"]) == ["city"]
    assert result["fields"]["city"]["value"] == "Manali"


def test_currency_normalization_does_not_corrupt_dollar_regex():
    value, valid = ExtractionService()._normalize("$1,200.00", "currency")
    assert value == "$1,200.00"
    assert valid is True


def test_noise_filter_preserves_numeric_values_and_form_headings():
    service = ExtractionService()
    blocks = [
        block("CLAIM DETAILS", 0, 0),
        block("123456", 0, 30),
        block("Uni Pin Fine Line", 0, 60),
    ]

    assert [item["text"] for item in service._filter_noise_blocks(blocks)] == ["CLAIM DETAILS", "123456"]
