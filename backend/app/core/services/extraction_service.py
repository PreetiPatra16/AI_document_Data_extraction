import re
from difflib import SequenceMatcher
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.core.config import Settings, settings
from app.middleware.error_handler import ExtractionException


SCHEMAS: Dict[str, Dict[str, Any]] = {
    "health_claim_form": {
        "anchors": ["claimant / patient details", "personal details of employee", "claim details"],
        "fields": {
            "employee_name": {"labels": ["name of the employee / individual", "name of employee / proposer"], "type": "name", "required": True},
            "employee_email": {"labels": ["e-mail address of the employee/individual", "email address"], "type": "email"},
            "employee_mobile": {"labels": ["mobile number"], "type": "phone"},
            "pan": {"labels": ["permanent account number (pan)", "pan"], "type": "pan"},
            "patient_name": {"labels": ["name of the patient", "claimant name"], "type": "name", "required": True},
            "patient_date_of_birth": {"labels": ["date of birth of claimant"], "type": "date"},
            "residential_address": {"labels": ["residential address"], "type": "address"},
            "claimed_amount": {"labels": ["total claimed amount"], "type": "currency"},
            "diagnosis": {"labels": ["diagnosis"], "type": "string"},
            "admission_date": {"labels": ["admission date"], "type": "date"},
            "discharge_date": {"labels": ["discharge date"], "type": "date"},
            "treating_doctor": {"labels": ["name of treating doctor"], "type": "name"},
            "treating_doctor_mobile": {"labels": ["mobile no. of treating doctor"], "type": "phone"},
            "family_physician": {"labels": ["name of family physician"], "type": "name"},
            "family_physician_mobile": {"labels": ["mobile no. of family physician"], "type": "phone"},
        },
    },
    "health_proposal_form": {
        "anchors": ["proposal form for health total", "proposer details", "details of persons to be insured"],
        "fields": {
            "proposer_name": {"labels": ["proposer details", "name"], "type": "name", "required": True},
            "permanent_address": {"labels": ["permanent address and other details"], "type": "address"},
            "state": {"labels": ["state"], "type": "string"},
            "pin_code": {"labels": ["pin code"], "type": "pin"},
            "mobile": {"labels": ["mobile no", "mobile no*"], "type": "phone"},
            "email": {"labels": ["email id", "email"], "type": "email"},
            "occupation": {"labels": ["occupation"], "type": "string"},
        },
    },
    "motor_claim_form": {
        "anchors": ["motor claim form", "claim form", "vehicle"],

        "fields": {

            "insured_name": {"labels": ["insured details name","insured name"],"type": "name","required": True},
            "policy_number": {"labels": ["policy number","policy no"],"type": "identifier"},
            "claim_number": {"labels": ["claim number","claim no"],"type": "identifier"},
            "mobile": {"labels": ["mobile","mobile no","mobile number"],"type": "phone"},
            "email": {"labels": ["email","email id","e-mail"],"type": "email"},
            "vehicle_registration": {"labels": ["vehicle number","vehicle registration","registration no"],"type": "identifier"}
        },
    },
}


class ExtractionService:
    def __init__(self, config: Settings = settings):
        self.settings = config

    async def extract_data(self, ocr_results: List[Dict[str, Any]], filename: str = "") -> Dict[str, Any]:
        try:
            clean_blocks = self._filter_noise_blocks(ocr_results)
            document_type = self.classify(clean_blocks)
            warnings: List[str] = []
            paragraphs = self._assemble_free_text(clean_blocks)
            raw_text = "\n\n".join(paragraphs)

            if document_type == "free_text_document":
                logger.info("Document classified as free_text_document paragraphs={}", len(paragraphs))
                warnings.append("free_text_no_schema")
                block_confidences = [b["confidence"] for b in clean_blocks if b["confidence"] > 0]
                summary = round(mean(block_confidences), 4) if block_confidences else 0.0
                return {
                    "schema_version": "1.0",
                    "document_type": document_type,
                    "confidence_summary": summary,
                    "review_required": True,
                    "fields": {},
                    "tables": [],
                    "warnings": warnings,
                    "raw_text": raw_text,
                    "paragraphs": paragraphs,
                }

            schema = SCHEMAS.get(document_type)
            if schema:
                fields = {name: self._extract_field(clean_blocks, spec) for name, spec in schema["fields"].items()}
            else:
                fields = self._generic_fields(clean_blocks)
                warnings.append("unsupported_template")
            confidences = [field["confidence"] for field in fields.values() if field["value"] is not None]
            summary = round(mean(confidences), 4) if confidences else 0.0
            review = any(field["review_required"] for field in fields.values()) or not fields
            if not confidences:
                warnings.append("no_fields_extracted")
                review = True
            return {
                "schema_version": "1.0",
                "document_type": document_type,
                "confidence_summary": summary,
                "review_required": review,
                "fields": fields,
                "tables": [],
                "warnings": warnings,
                "raw_text": raw_text,
                "paragraphs": paragraphs,
            }
        except ExtractionException:
            raise
        except Exception as exc:
            raise ExtractionException(f"Structured field extraction failed: {exc}") from exc

    def classify(self, blocks: List[Dict[str, Any]]) -> str:
        text = " ".join(block["text"].lower() for block in blocks)
        tokens = set(text.split())
        scores: Dict[str, float] = {}
        for name, schema in SCHEMAS.items():
            score = 0.0
            for anchor in schema["anchors"]:
                if anchor.lower() in text:
                    score += 2.0
                else:
                    anchor_tokens = set(anchor.lower().split())
                    if anchor_tokens:
                        overlap = len(anchor_tokens & tokens) / len(anchor_tokens)
                        if overlap >= 0.6:
                            score += overlap
                        else:
                            ratio = SequenceMatcher(None, anchor.lower(), text).ratio()
                            if ratio >= 0.7:
                                score += ratio
            scores[name] = score
        winner = max(scores, key=scores.get)
        if scores[winner] >= 0.6:
            return winner
        if self._is_free_text(blocks):
            return "free_text_document"
        return "generic_form"

    def _is_free_text(self, blocks: List[Dict[str, Any]]) -> bool:
        """Heuristic: if blocks look like running prose rather than label:value pairs."""
        valid = [b for b in blocks if b["text"].strip()]
        if len(valid) < 3:
            return False
        avg_len = sum(len(b["text"]) for b in valid) / len(valid)
        colon_pct = sum(1 for b in valid if ":" in b["text"]) / len(valid)
        long_block_pct = sum(1 for b in valid if len(b["text"].split()) >= 5) / len(valid)
        return avg_len > 20 and colon_pct < 0.25 and long_block_pct > 0.4

    def _extract_field(self, blocks: List[Dict[str, Any]], spec: Dict[str, Any]) -> Dict[str, Any]:
        full_text = " ".join(
            b["text"]
            for b in blocks
        )
        candidates: List[Tuple[str, Dict[str, Any], float, bool]] = []
        
        for label_block in blocks:
            label_text = label_block["text"].strip()
            label_lower = label_text.lower()
            for label in spec["labels"]:

                field_type = spec.get("type")

                if field_type == "name":

                    match = re.search(
                        r"insured details\s+name\s+([A-Z\s]{5,80})",
                        full_text,
                        re.I,
                    )

                    if match:

                        extracted_name = match.group(1)
                        extracted_name = re.split(
                            r"\b(Address|Mobile|State|Email)\b",
                            extracted_name,
                            flags=re.I,
                        )[0].strip()
                        candidates.append(
                            (
                                extracted_name,
                                label_block,
                                1.0,
                                True,
                            )
                        )  

                elif field_type == "identifier":

                    match = re.search(
                        rf"{re.escape(label)}\s+([A-Z0-9-]{{4,25}})",
                    label_text,
                    re.I,
                    )

                    if match:
                        candidates.append(
                            (
                                match.group(1).strip(),
                                label_block,
                                1.0,
                                True,
                            )
                        )
        
                position = label_lower.find(label.lower())
                if position < 0:
                    continue
                remainder = re.sub(r"^[\s:.\-–]+", "", label_text[position + len(label):]).strip()
                if remainder:
                    candidates.append((remainder, label_block, 1.0, True))
                label_box = label_block["bounding_box"]
                for value_block in blocks:
                    if value_block is label_block or value_block["page"] != label_block["page"]:
                        continue
                    value_text = value_block["text"].strip()
                    if any(alias.lower() in value_text.lower() for alias in spec["labels"]):
                        continue
                    value_box = value_block["bounding_box"]
                    vertical_delta = abs(value_box["y"] - label_box["y"])
                    right_gap = value_box["x"] - (label_box["x"] + label_box["width"])
                    below_gap = value_box["y"] - (label_box["y"] + label_box["height"])
                    same_row = vertical_delta <= max(label_box["height"], value_box["height"]) * 1.2 and -10 <= right_gap <= 500
                    below = -40 <= value_box["x"] - label_box["x"] <= 200 and 0 <= below_gap <= 120
                    if same_row or below:
                        distance_score = max(0.2, 1 - max(right_gap, below_gap, 0) / 600)
                        candidates.append((value_text, value_block, distance_score, False))
        best = None
        for raw, block, spatial, same_block in candidates:

            if "vehicle" in " ".join(spec["labels"]).lower():
                match = re.search(
                    r"MH\d{2}[A-Z]{1,3}\d{4}",
                    full_text,
                    re.I
                )
                
                if match:
                    normalized = match.group(0)
                    return self._field(
                        normalized,
                        raw,
                        block,
                        0.99,
                        False
                    )

            normalized, valid = self._normalize(raw, spec["type"])

            if normalized == "Name":
                continue
            if normalized in ["Address", "Mobile", "State", "Email"]:
                continue
            if not normalized:
                continue
            confidence = (
                block["confidence"] * 0.5
                + spatial * 0.25
                + (1.0 if valid else 0.25) * 0.25
            )
            if same_block:
                confidence += 0.03
            confidence = round(min(confidence, 1.0), 4)
            if best is None or confidence > best["confidence"]:
                best = self._field(normalized, raw, block, confidence, not valid)
        if best:
            return best
        return self._field(None, None, None, 0.0, bool(spec.get("required")), missing=True)

    def _filter_noise_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove empty, near-zero-confidence, and known pen-label blocks."""
        _product_re = re.compile(
            r"uni\b.*\bpin\b"                   # "uni pin FINE LINE" etc.
            r"|\bfine\s+line\b"
            r"|\brecap\b|\bmicron\b",
            re.I,
        )
        cleaned = []
        for b in blocks:
            t = b["text"].strip()
            if not t or len(t) < 2:
                continue
            if b["confidence"] < 0.05:
                continue
            if _product_re.search(t):
                continue
            cleaned.append(b)
        return cleaned

    def _assemble_free_text(self, blocks: List[Dict[str, Any]]) -> List[str]:
        """Sort OCR blocks spatially, group into lines then paragraphs, trim trailing noise."""
        valid = [b for b in blocks if b["text"].strip()]
        if not valid:
            return []

        # Sort by page → Y → X
        valid = sorted(valid, key=lambda b: (b["page"], b["bounding_box"]["y"], b["bounding_box"]["x"]))

        # Group blocks into text lines by Y-center proximity
        lines: List[List[Dict[str, Any]]] = []
        current_line: List[Dict[str, Any]] = []
        for block in valid:
            if not current_line:
                current_line = [block]
                continue
            last = current_line[-1]
            last_cy = last["bounding_box"]["y"] + last["bounding_box"]["height"] / 2
            curr_cy = block["bounding_box"]["y"] + block["bounding_box"]["height"] / 2
            tolerance = max(last["bounding_box"]["height"], block["bounding_box"]["height"]) * 0.75
            if abs(curr_cy - last_cy) <= tolerance:
                current_line.append(block)
            else:
                lines.append(sorted(current_line, key=lambda b: b["bounding_box"]["x"]))
                current_line = [block]
        if current_line:
            lines.append(sorted(current_line, key=lambda b: b["bounding_box"]["x"]))

        # Trim lines that appear after a letter closing phrase
        _closing = re.compile(r"\b(sincere|regards|respect|truly|sincerely|yours|warm|cheers)\b", re.I)
        trim_at = len(lines)
        for i, line in enumerate(lines):
            line_text = " ".join(b["text"] for b in line)
            if _closing.search(line_text):
                trim_at = i + 1
                break
        if trim_at < len(lines):
            lines = lines[:trim_at]

        # Group lines into paragraphs by vertical gap
        paragraphs: List[List[List[Dict[str, Any]]]] = []
        current_para: List[List[Dict[str, Any]]] = []
        for line in lines:
            if not current_para:
                current_para = [line]
                continue
            last_line = current_para[-1]
            last_bottom = max(b["bounding_box"]["y"] + b["bounding_box"]["height"] for b in last_line)
            curr_top = min(b["bounding_box"]["y"] for b in line)
            gap = curr_top - last_bottom
            avg_height = sum(b["bounding_box"]["height"] for b in last_line) / len(last_line)
            if gap > avg_height * 1.6:
                paragraphs.append(current_para)
                current_para = [line]
            else:
                current_para.append(line)
        if current_para:
            paragraphs.append(current_para)

        # Render each paragraph to a string
        result: List[str] = []
        for para in paragraphs:
            line_texts = [
                " ".join(b["text"].strip() for b in line if b["text"].strip())
                for line in para
            ]
            para_text = " ".join(t for t in line_texts if t).strip()
            if para_text:
                result.append(para_text)
        return result

    def _generic_fields(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}

        def make_key(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", "_", text.lower().strip(" :.-_")).strip("_")

        def looks_like_label(text: str) -> bool:
            s = text.strip(" :.-")
            if not s or len(s) > 65 or len(s) < 2:
                return False
            return sum(c.isalpha() for c in s) / len(s) > 0.55

        # Pass 1: "Label: value" on the same OCR line (original behaviour, kept as it's fast)
        for block in blocks:
            match = re.match(r"^\s*([A-Za-z][A-Za-z0-9 /()_.-]{1,50})\s*[:=-]\s*(.+?)\s*$", block["text"])
            if not match:
                continue
            key = make_key(match.group(1))
            value = match.group(2).strip()
            if value and key and key not in fields:
                fields[key] = self._field(value, block["text"], block, round(block["confidence"] * 0.8, 4), True)

        # Pass 2: spatial proximity — label block paired with nearest right/below value block
        for label_block in blocks:
            label_text = label_block["text"].strip()
            if not looks_like_label(label_text):
                continue
            key = make_key(label_text)
            if not key or key in fields:
                continue
            label_box = label_block["bounding_box"]
            best_value: Optional[str] = None
            best_score = float("inf")
            best_block: Optional[Dict[str, Any]] = None
            for value_block in blocks:
                if value_block is label_block or value_block["page"] != label_block["page"]:
                    continue
                value_text = value_block["text"].strip()
                if not value_text or looks_like_label(value_text):
                    continue
                value_box = value_block["bounding_box"]
                vertical_delta = abs(value_box["y"] - label_box["y"])
                right_gap = value_box["x"] - (label_box["x"] + label_box["width"])
                below_gap = value_box["y"] - (label_box["y"] + label_box["height"])
                row_height = max(label_box["height"], value_box["height"])
                same_row = vertical_delta <= row_height * 1.5 and 0 <= right_gap <= 600
                below_row = -30 <= value_box["x"] - label_box["x"] <= 250 and 0 <= below_gap <= 150
                if same_row:
                    score = right_gap
                elif below_row:
                    score = below_gap + 300
                else:
                    continue
                if score < best_score:
                    best_score = score
                    best_value = value_text
                    best_block = value_block
            if best_value and best_block:
                fields[key] = self._field(
                    best_value, best_value, best_block,
                    round(best_block["confidence"] * 0.85, 4), True,
                )
        return fields

    def _normalize(self, value: str, field_type: str) -> Tuple[Optional[str], bool]:

        if field_type == "email":
            value = value.replace(" @ ", "@")
            value = value.replace(" gmail ", "@gmail.")
            value = value.replace(" com", ".com")
        value = re.sub(r"\s+", " ", value).strip(" :;,_")
        value = re.split(
            r"\b(?:Enclosure Check List|Discharge Date|First prescription|Copy of proposer|Aadhar Card No)\b",
            value,
            maxsplit=1,
            flags=re.I,
        )[0].strip(" ,:;")
        patterns = {
            "email": r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
            "phone": r"^\+?[\d ()-]{8,18}$",
            "pan": r"^[A-Z]{5,6}[0-9]{4}[A-Z]$",
            "pin": r"^\d{6}$",
            "date": r"^(?:\d{1,2}[/.-]){2}\d{2,4}$",
            "currency": r"^(?:Rs\.?|₹|\$)?\s*[\d,]+(?:\.\d{1,2})?$",
            "identifier": r"^[A-Za-z0-9/_-]{3,}$",
        }
        if field_type in patterns:
            pattern = patterns[field_type]
            search_pattern = pattern[1:-1] if pattern.startswith("^") and pattern.endswith("$") else pattern
            match = re.search(search_pattern, value, re.I)
            if match:
                value = match.group(0).strip()
        if field_type == "email":
            value = value.replace(" @ ", "@")
            value = value.replace("@ ", "@")
            value = value.replace(" @", "@")
            if "@gmail" in value and ".com" not in value:
                value += ".com"
            value = value.lower()
        if field_type == "phone":
            value = (value.replace("%", "9").replace("O", "0").replace("o", "0"))
            value = re.sub(r"\D", "", value)
        if field_type == "pin":
            value = re.sub(r"\D", "", value)[:6]
        if field_type == "name":
            value = value.strip(" .,:;")
        valid = bool(re.match(patterns[field_type], value, re.I)) if field_type in patterns else len(value) >= 2
        return value or None, valid

    def _field(self, value, raw, block, confidence: float, invalid: bool, missing: bool = False) -> Dict[str, Any]:
        review = invalid or (not missing and confidence < self.settings.review_confidence)
        return {
            "value": value,
            "normalized_value": value,
            "confidence": confidence,
            "bounding_box": block["bounding_box"] if block else None,
            "page": block["page"] if block else None,
            "raw_text": raw,
            "source_engine": block.get("source_engine") if block else None,
            "review_required": review,
        }
