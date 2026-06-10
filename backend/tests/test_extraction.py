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


def test_email_normalization_repairs_ocr_artifacts():
    service = ExtractionService()
    assert service._normalize("R I YASHARMA @ g mail. com", "email") == ("riyasharma@gmail.com", True)
    assert service._normalize("kadira.mulla @ gmail ful WE m410206 com", "email") == ("kadira.mulla@gmail.com", True)
    assert service._normalize("pranitag@techaim.in", "email") == ("pranitag@techaim.in", True)


def test_name_normalization_collapses_boxed_letters_and_digit_confusions():
    service = ExtractionService()
    value, valid = service._normalize("R 1 Y A S H A R M A", "name")
    assert value == "RIYASHARMA"
    assert valid is True
    value, valid = service._normalize("Mr. Ms. M/s", "name")
    assert valid is False


def test_value_owned_by_nearer_label_is_not_stolen():
    service = ExtractionService()
    result = asyncio.run(service.extract_data([
        block("MOTOR CLAIM FORM", 400, 30),
        block("Insured Details", 0, 90),
        block("Policy Number", 0, 120),
        block("AFI498ED", 10, 150, confidence=0.6),
        block("Vehicle Number", 300, 120),
        block("MH43CD7011", 310, 150, confidence=0.7),
        block("Loss Details", 0, 400),
    ]))
    assert result["fields"]["policy_number"]["value"] == "AFI498ED"
    assert result["fields"]["vehicle_registration"]["value"] == "MH43CD7011"


def test_typed_fields_reject_non_matching_candidates():
    service = ExtractionService()
    result = asyncio.run(service.extract_data([
        block("CLAIMANT / PATIENT DETAILS", 0, 0),
        block("PERSONAL DETAILS OF EMPLOYEE", 0, 30),
        block("CLAIM DETAILS", 0, 60),
        block("Date of Birth of Claimant:", 0, 100),
        block("Residential Address: nearby text", 0, 130),
    ]))
    assert result["fields"]["patient_date_of_birth"]["value"] is None


def test_noise_filter_preserves_numeric_values_and_form_headings():
    service = ExtractionService()
    blocks = [
        block("CLAIM DETAILS", 0, 0),
        block("123456", 0, 30),
        block("Uni Pin Fine Line", 0, 60),
    ]

    assert [item["text"] for item in service._filter_noise_blocks(blocks)] == ["CLAIM DETAILS", "123456"]
