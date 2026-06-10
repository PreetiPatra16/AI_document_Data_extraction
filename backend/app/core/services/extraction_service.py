import re
from difflib import SequenceMatcher
from functools import lru_cache
from statistics import mean
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from app.core.config import Settings, settings
from app.middleware.error_handler import ExtractionException


SCHEMAS: Dict[str, Dict[str, Any]] = {
    "health_claim_form": {
        "anchors": [
            "health insurance claim form",
            "claimant / patient details",
            "personal details of employee",
            "claim details",
        ],
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
        "decoys": [
            "aadhar card no", "claimed amount in words", "relationship with the employee / proposer",
            "details of other existing health policies", "ongoing medication", "enclosure check list",
            "policy no", "health card no. of patient", "policy start date", "policy end date",
            "corporate name", "employee id",
        ],
        # All extracted fields sit on page 1 of the claim form.
        "default_page": 1,
    },
    "health_proposal_form": {
        "anchors": [
            "proposal form for health total",
            "details of persons to be insured",
            "permanent address and other details",
            "proposer details",
        ],
        "fields": {
            "proposer_name": {"labels": ["proposer details", "name"], "type": "name", "required": True},
            "permanent_address": {"labels": ["permanent address and other details", "permanent address"], "type": "address"},
            "state": {"labels": ["state"], "type": "string"},
            "pin_code": {"labels": ["pin code"], "type": "pin"},
            "mobile": {"labels": ["mobile no", "mobile no*"], "type": "phone"},
            "email": {"labels": ["email id", "email"], "type": "email"},
            "pan": {"labels": ["pan"], "type": "pan"},
            "date_of_birth": {"labels": ["date of birth"], "type": "date"},
            "occupation": {"labels": ["occupation"], "type": "string"},
        },
        "decoys": [
            "received date", "branch code", "branch name", "tel no", "fax no",
            "annual gross income", "family doctor details", "e-ia number",
            "e-insurance account number", "io no", "app no", "client code",
            "receipt no", "payer id", "sb/ca acc no", "journal no", "present address",
        ],
        # Proposer fields live on page 1 of the multi-page template.
        "default_page": 1,
    },
    "motor_claim_form": {
        "anchors": [
            "motor claim form",
            "loss details",
            "driver details at the time of accident",
            "insured details",
        ],
        "fields": {
            "insured_name": {"labels": ["name"], "type": "name", "required": True, "section": "insured details"},
            "policy_number": {"labels": ["policy number", "policy no"], "type": "identifier"},
            "claim_number": {"labels": ["claim number", "claim no"], "type": "identifier"},
            "vehicle_registration": {"labels": ["vehicle number", "vehicle registration", "registration no"], "type": "identifier"},
            "address": {"labels": ["address"], "type": "address", "section": "insured details"},
            "state": {"labels": ["state"], "type": "string", "section": "insured details"},
            "mobile": {"labels": ["mobile", "mobile no", "mobile number"], "type": "phone", "section": "insured details"},
            "email": {"labels": ["email", "email id", "e-mail"], "type": "email", "section": "insured details"},
            "place_of_accident": {"labels": ["place of accident"], "type": "string"},
            "accident_date": {"labels": ["date & time of accident", "date of accident"], "type": "date"},
        },
        "decoys": [
            "ifsc code", "micr", "a/c no", "aadhar no", "pan no", "bank details - bank name",
            "branch", "landline", "pin-code", "type of a/c", "name (as per bank account)",
            "police report details", "name of rto", "learners license", "driver license no",
            "permit no", "permit valid up to", "contact no", "city",
        ],
    },
    "office_proposal_form": {
        "anchors": [
            "office suraksha proposal form",
            "occupation / business activity",
            "name of proposer / insured",
        ],
        "fields": {
            "proposer_name": {
                "labels": [
                    "name of proposer / insured along with correspondence address",
                    "name of proposer / insured",
                    "name of proposer",
                ],
                "type": "name",
                "required": True,
            },
            "address": {"labels": ["address of proposer / insured premises", "address of proposer"], "type": "address"},
            "city": {"labels": ["city"], "type": "string"},
            "state": {"labels": ["state"], "type": "string"},
            "pin_code": {"labels": ["pin code"], "type": "pin"},
            "email": {"labels": ["e-mail", "email"], "type": "email"},
            "occupation": {"labels": ["occupation / business activity", "occupation"], "type": "string"},
        },
        "decoys": [
            "telephone (o)", "fax no", "policy period", "coverage proposed",
            "hypothecation", "building construction", "year of production",
            "name of manufacturer", "date of manufacture", "reinstatement value",
        ],
    },
}

# Field types whose values must match their validation pattern to be accepted.
STRICT_TYPES = {"email", "phone", "pan", "pin", "date", "currency", "identifier", "address"}

# Form vocabulary that never appears inside a person's name. Used to reject
# label fragments and headings that get picked up as name candidates.
NAME_STOPWORDS = {
    "name", "address", "mobile", "state", "email", "city", "details", "signature",
    "declaration", "bank", "branch", "number", "code", "permanent", "present",
    "account", "form", "proposal", "insurance", "health", "total", "office",
    "claim", "policy", "vehicle", "period", "gender", "nationality", "marital",
    "occupation", "telephone", "district", "landmark", "manufacturer", "mr",
    "ms", "mrs", "m/s", "tick", "please", "above", "same", "premises",
    "correspondence",
}

KNOWN_EMAIL_PROVIDERS = ("gmail", "yahoo", "hotmail", "outlook", "rediffmail")
EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", re.I)
TLD_RE = re.compile(r"\b(com|in|net|org|co\.in|edu|gov)\b", re.I)

# A same-block remainder starting with a connective means the label match was a
# prefix of a longer label ("Name of manufacturer"), not a label/value pair.
LABEL_CONTINUATION_RE = re.compile(r"^(of|the|and|in|for|as|per|to|with|details?)\b", re.I)

# Section headings, boilerplate, and label-like fragments ("Tel No") that must
# never be picked as field values.
VALUE_NOISE_RE = re.compile(
    r"\b(details?|declaration|signature|checklist|check list|no\.?|number|id)\s*[:.]?\s*$", re.I
)


class ExtractionService:
    def __init__(self, config: Settings = settings):
        self.settings = config

    async def extract_data(self, ocr_results: List[Dict[str, Any]], filename: str = "") -> Dict[str, Any]:
        try:
            clean_blocks = self._filter_noise_blocks(ocr_results)
            document_type = self.classify(clean_blocks)
            warnings: List[str] = []
            paragraphs = self._assemble_free_text(clean_blocks, trim_closing=document_type == "free_text_document")
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
                # Decoy labels are form fields we do not extract; knowing them
                # stops their values being attributed to neighbouring fields.
                schema_labels = [
                    label for spec in schema["fields"].values() for label in spec["labels"]
                ] + list(schema.get("decoys", []))
                label_block_ids = {
                    id(b) for b in clean_blocks if self._is_schema_label_block(b["text"].strip(), schema_labels)
                }
                default_page = schema.get("default_page")
                fields = {
                    name: self._extract_field(
                        clean_blocks, spec, schema_labels, label_block_ids, default_page
                    )
                    for name, spec in schema["fields"].items()
                }
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
        text = re.sub(r"\s+", " ", text)
        tokens = set(text.split())
        scores: Dict[str, float] = {}
        for name, schema in SCHEMAS.items():
            score = 0.0
            for anchor in schema["anchors"]:
                if anchor.lower() in text:
                    score += 2.0
                else:
                    anchor_tokens = set(anchor.lower().split())
                    overlap = len(anchor_tokens & tokens) / len(anchor_tokens) if anchor_tokens else 0.0
                    if overlap >= 0.75:
                        score += overlap
            scores[name] = score
        winner = max(scores, key=scores.get)
        if scores[winner] >= 2.0:
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

    @staticmethod
    @lru_cache(maxsize=512)
    def _label_pattern(label: str) -> re.Pattern:
        """Word-boundary label matcher tolerant of OCR whitespace; avoids
        matching 'state' inside 'statements'."""
        escaped = re.escape(label.lower()).replace(r"\ ", r"\s*")
        return re.compile(r"(?<![a-z0-9])" + escaped + r"(?![a-z])")

    @staticmethod
    def _fuzzy_label_end(text_lower: str, label: str) -> Optional[Tuple[int, float]]:
        """Photographed printed labels OCR imperfectly ('Chaliny Numbar' for
        'Claim Number'); match the block prefix approximately and return the
        position where the label ends plus the match ratio."""
        if len(label) < 5:
            return None
        # Ignore list numbering ("2. Address ...") when aligning the prefix.
        offset_match = re.match(r"\s*\d{1,2}\s*[.)]\s*", text_lower)
        offset = offset_match.end() if offset_match else 0
        body = text_lower[offset:]
        # Labels sharing a long tail ("address of proposer / insured" vs
        # "name of proposer / insured") must not cross-match: the first words
        # have to resemble each other too.
        label_head = label.split()[0]
        body_head = body.split()[0] if body.split() else ""
        if SequenceMatcher(None, label_head, body_head).ratio() < 0.5:
            return None
        best_end, best_ratio = None, 0.0
        for end in range(max(len(label) - 2, 1), min(len(label) + 3, len(body)) + 1):
            ratio = SequenceMatcher(None, label, body[:end]).ratio()
            if ratio > best_ratio:
                best_ratio, best_end = ratio, end
        if best_ratio >= 0.66:
            # Snap to the next whitespace so the remainder starts on a clean
            # token boundary ("Eman kadira..." must not leave a stray "n").
            end = offset + best_end
            while end < len(text_lower) and not text_lower[end].isspace():
                end += 1
            return end, best_ratio
        return None

    @staticmethod
    def _section_anchor(blocks: List[Dict[str, Any]], section: Optional[str]) -> Optional[Dict[str, Any]]:
        if not section:
            return None
        pattern = ExtractionService._label_pattern(section)
        for block in blocks:
            if pattern.search(block["text"].lower()):
                return block
        return None

    @staticmethod
    def _section_factor(label_block: Dict[str, Any], anchor: Optional[Dict[str, Any]]) -> float:
        if anchor is None:
            return 1.0
        if label_block["page"] != anchor["page"]:
            return 0.5
        delta = label_block["bounding_box"]["y"] - anchor["bounding_box"]["y"]
        return 1.0 if -20 <= delta <= 400 else 0.5

    def _cut_at_labels(self, value: str, schema_labels: List[str], current_label: str) -> str:
        """Trim a same-line value at the next field label that follows it."""
        cut = len(value)
        lowered = value.lower()
        for label in schema_labels:
            if label == current_label:
                continue
            match = self._label_pattern(label).search(lowered)
            if match and 0 < match.start() < cut:
                cut = match.start()
        return value[:cut].strip(" :;_")

    def _is_schema_label_block(self, text: str, schema_labels: List[str]) -> bool:
        """True when a block is just a field label (possibly with separators)."""
        stripped = text.strip(" :*.-_").lower()
        if not stripped:
            return True
        for label in schema_labels:
            match = self._label_pattern(label).match(stripped)
            if match and len(stripped) - match.end() <= 3:
                return True
        return False

    def _extract_field(
        self,
        blocks: List[Dict[str, Any]],
        spec: Dict[str, Any],
        schema_labels: List[str],
        label_block_ids: Set[int],
        default_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        field_type = spec.get("type", "string")
        expected_page = spec.get("page", default_page)
        anchor = self._section_anchor(blocks, spec.get("section"))
        candidates: List[Tuple[str, Dict[str, Any], float, bool]] = []

        for label_block in blocks:
            label_text = label_block["text"].strip()
            text_lower = label_text.lower()
            # Prefer the longest alias of this field that matches the block, so
            # "Occupation / Business Activity" is consumed whole rather than
            # leaving "/ Business Activity" as a remainder.
            label_end, matched_label, label_factor = None, None, 1.0
            for label in spec["labels"]:
                match = self._label_pattern(label).search(text_lower)
                if match and (label_end is None or match.end() > label_end):
                    label_end, matched_label = match.end(), label
            if label_end is None:
                if id(label_block) in label_block_ids:
                    # The block exactly matches another field's label; fuzzy
                    # matching it here would steal that field's value.
                    continue
                best_fuzzy: Optional[Tuple[int, float, str]] = None
                for label in spec["labels"]:
                    fuzzy = self._fuzzy_label_end(text_lower, label)
                    if fuzzy and (best_fuzzy is None or fuzzy[1] > best_fuzzy[1]):
                        best_fuzzy = (fuzzy[0], fuzzy[1], label)
                if best_fuzzy is None:
                    continue
                # Fuzzy matches rank below exact matches of other labels.
                label_end, matched_label = best_fuzzy[0], best_fuzzy[2]
                label_factor = best_fuzzy[1] * 0.95
            section_factor = self._section_factor(label_block, anchor) * label_factor
            if expected_page is not None and label_block["page"] != expected_page:
                section_factor *= 0.6

            remainder = re.sub(r"^[\s:.\-–*_]+", "", label_text[label_end:]).strip()
            if remainder and not LABEL_CONTINUATION_RE.match(remainder):
                remainder = self._cut_at_labels(remainder, schema_labels, matched_label)
                if remainder and sum(c.isalnum() for c in remainder) >= 2:
                    candidates.append((remainder, label_block, 1.0 * section_factor, True))

            label_box = label_block["bounding_box"]
            for value_block in blocks:
                if value_block is label_block or value_block["page"] != label_block["page"]:
                    continue
                value_text = value_block["text"].strip()
                if not value_text or id(value_block) in label_block_ids:
                    continue
                if sum(c.isalnum() for c in value_text) < 2:
                    continue
                if VALUE_NOISE_RE.search(value_text):
                    continue
                value_words = re.findall(r"[a-z]{2,}", value_text.lower())
                if value_words and all(word in NAME_STOPWORDS for word in value_words):
                    continue
                # A block beginning with another field's label ("State HIMACHAL
                # ... Pin Code ...") carries that field's value, not this one's.
                value_lower = value_text.lower()
                if any(
                    self._label_pattern(other).match(value_lower)
                    for other in schema_labels
                    if other not in spec["labels"]
                ):
                    continue
                value_text = self._cut_at_labels(value_text, schema_labels, matched_label)
                if not value_text or sum(c.isalnum() for c in value_text) < 2:
                    continue
                value_box = value_block["bounding_box"]
                label_cy = label_box["y"] + label_box["height"] / 2
                value_cy = value_box["y"] + value_box["height"] / 2
                vertical_delta = abs(value_cy - label_cy)
                right_gap = value_box["x"] - (label_box["x"] + label_box["width"])
                below_gap = value_box["y"] - (label_box["y"] + label_box["height"])
                row_height = max(label_box["height"], value_box["height"])
                same_row = vertical_delta <= row_height * 1.2 and -10 <= right_gap <= 600
                # Handwriting often overlaps the printed label row, so allow a
                # slightly negative gap for the below relation.
                below = (
                    -40 <= value_box["x"] - label_box["x"] <= 250
                    and -row_height * 0.6 <= below_gap <= 150
                )
                if same_row:
                    spatial = max(0.3, 1.0 - max(right_gap, 0) / 700)
                elif below:
                    spatial = max(0.25, 0.75 - below_gap / 400)
                else:
                    continue
                if self._another_label_owns_value(
                    blocks, label_block, value_block, label_block_ids, same_row
                ):
                    continue
                candidates.append((value_text, value_block, spatial * section_factor, False))

        best: Optional[Dict[str, Any]] = None
        for raw, block, spatial, same_block in candidates:
            normalized, valid = self._normalize(raw, field_type)
            if not normalized:
                continue
            if not valid and field_type in STRICT_TYPES:
                continue
            if not valid and field_type == "name":
                continue
            # Spatial proximity dominates: handwriting has low OCR confidence,
            # so weighting OCR confidence highly favours printed boilerplate.
            confidence = block["confidence"] * 0.15 + valid * 0.3 + spatial * 0.55
            if same_block:
                confidence += 0.05
            confidence = round(min(confidence, 1.0), 4)
            if best is None or confidence > best["confidence"]:
                best = self._field(normalized, raw, block, confidence, not valid)
                best["_block"] = block
                best["_same_block"] = same_block

        if best and not best["_same_block"] and field_type in ("name", "address"):
            self._extend_row(best, blocks, label_block_ids, field_type)
        if best and field_type == "address":
            self._extend_address(best, blocks, schema_labels, label_block_ids)
        if best:
            best.pop("_block", None)
            best.pop("_same_block", None)
            return best
        return self._field(None, None, None, 0.0, bool(spec.get("required")), missing=True)

    @staticmethod
    def _another_label_owns_value(
        blocks: List[Dict[str, Any]],
        label_block: Dict[str, Any],
        value_block: Dict[str, Any],
        label_block_ids: Set[int],
        same_row: bool,
    ) -> bool:
        """A value belongs to the closest label: skip the pair when a different
        label block sits between this label and the value."""
        label_box = label_block["bounding_box"]
        value_box = value_block["bounding_box"]
        for other in blocks:
            if other is label_block or other is value_block:
                continue
            if id(other) not in label_block_ids or other["page"] != value_block["page"]:
                continue
            other_box = other["bounding_box"]
            other_cy = other_box["y"] + other_box["height"] / 2
            if same_row:
                value_cy = value_box["y"] + value_box["height"] / 2
                row_tolerance = max(value_box["height"], other_box["height"]) * 1.2
                if abs(other_cy - value_cy) > row_tolerance:
                    continue
                if label_box["x"] + label_box["width"] <= other_box["x"] <= value_box["x"]:
                    return True
            else:
                # A different label sitting to the left on the value's own row
                # owns that row ("City | MANALI" must not feed proposer_name).
                value_cy = value_box["y"] + value_box["height"] / 2
                row_tolerance = max(value_box["height"], other_box["height"]) * 0.9
                if abs(other_cy - value_cy) <= row_tolerance and other_box["x"] < value_box["x"]:
                    return True
                x_overlap = (
                    min(value_box["x"] + value_box["width"], other_box["x"] + other_box["width"])
                    - max(value_box["x"], other_box["x"])
                )
                if x_overlap <= 0:
                    continue
                # Another label above the value (and at or below this label's
                # top) is the closer owner of that value column.
                if label_box["y"] <= other_cy <= value_box["y"]:
                    return True
        return False

    def _extend_row(
        self,
        field: Dict[str, Any],
        blocks: List[Dict[str, Any]],
        label_block_ids: Set[int],
        field_type: str,
    ) -> None:
        """Handwritten values fragment into several blocks on one line
        ("KAD" + "RA KAZIM MARUF"); join the row before normalizing."""
        base = field.get("_block")
        if not base:
            return
        box, page = base["bounding_box"], base["page"]
        base_cy = box["y"] + box["height"] / 2
        right_edge = box["x"] + box["width"]
        parts = [base["text"].strip()]
        followers = sorted(
            (b for b in blocks if b is not base and b["page"] == page),
            key=lambda b: b["bounding_box"]["x"],
        )
        for block in followers:
            b = block["bounding_box"]
            block_cy = b["y"] + b["height"] / 2
            if abs(block_cy - base_cy) > max(box["height"], b["height"]) * 0.6:
                continue
            gap = b["x"] - right_edge
            if gap < -10 or gap > max(50.0, box["height"] * 2.5):
                continue
            text = block["text"].strip()
            if not text or id(block) in label_block_ids or VALUE_NOISE_RE.search(text):
                break
            words = re.findall(r"[a-z]{2,}", text.lower())
            if words and all(word in NAME_STOPWORDS for word in words):
                break
            parts.append(text)
            right_edge = b["x"] + b["width"]
        merged = " ".join(parts)
        if merged == parts[0]:
            return
        normalized, valid = self._normalize(merged, field_type)
        if normalized and valid:
            field["value"] = normalized
            field["normalized_value"] = normalized
            field["raw_text"] = merged

    def _extend_address(
        self,
        field: Dict[str, Any],
        blocks: List[Dict[str, Any]],
        schema_labels: List[str],
        label_block_ids: Set[int],
    ) -> None:
        """Addresses span several OCR lines; append lines stacked directly below."""
        base = field.get("_block")
        if not base:
            return
        box, page = base["bounding_box"], base["page"]
        parts = [field["value"]]
        current_bottom = box["y"] + box["height"]
        followers = sorted(
            (b for b in blocks if b is not base and b["page"] == page),
            key=lambda b: b["bounding_box"]["y"],
        )
        label_blocks = [b for b in blocks if id(b) in label_block_ids and b["page"] == page]
        added = 0
        for block in followers:
            b = block["bounding_box"]
            gap = b["y"] - current_bottom
            x_overlap = min(box["x"] + box["width"], b["x"] + b["width"]) - max(box["x"], b["x"])
            if gap < -5 or gap > max(b["height"], box["height"]) * 1.2 or x_overlap <= 0:
                continue
            text = block["text"].strip()
            if not text or id(block) in label_block_ids:
                break
            if any(self._label_pattern(label).search(text.lower()) for label in schema_labels):
                break
            # A label to the left on the same row means this line is another
            # field's value, not an address continuation.
            block_cy = b["y"] + b["height"] / 2
            if any(
                lb["bounding_box"]["x"] < b["x"]
                and abs(lb["bounding_box"]["y"] + lb["bounding_box"]["height"] / 2 - block_cy)
                <= max(lb["bounding_box"]["height"], b["height"]) * 0.9
                for lb in label_blocks
            ):
                break
            parts.append(text)
            current_bottom = b["y"] + b["height"]
            added += 1
            if added >= 5:
                break
        joined = re.sub(r"\s+", " ", " ".join(parts)).strip()
        field["value"] = joined
        field["normalized_value"] = joined

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

    def _assemble_free_text(self, blocks: List[Dict[str, Any]], trim_closing: bool = False) -> List[str]:
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

        # Trim lines after a letter closing phrase, but only for letter-like
        # free text: forms legitimately contain words such as "respect".
        if trim_closing:
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

    @staticmethod
    def _collapse_boxed_letters(value: str) -> str:
        """Comb/boxed fields OCR as spaced single characters; join them."""
        tokens = value.split()
        if len(tokens) >= 3 and sum(1 for t in tokens if len(t) == 1) / len(tokens) >= 0.6:
            return "".join(tokens)
        return value

    def _normalize_email(self, value: str) -> Tuple[Optional[str], bool]:
        v = re.sub(r"\s*@\s*", "@", value.strip())
        if "@" not in v:
            v = re.sub(
                r"\s+(" + "|".join(KNOWN_EMAIL_PROVIDERS) + r")", r"@\1", v, count=1, flags=re.I
            )
        # Boxed-letter local parts OCR with spaces ("R I YASHARMA@..."): join
        # everything before the @.
        v = re.sub(r"\s+(?=[^@\s]*(?:\s+[^@\s]+)*@)", "", v)
        # Rejoin split provider domains ("@g mail.com", "@ya hoo.com").
        v = re.sub(r"@g\s*mail\b", "@gmail", v, flags=re.I)
        v = re.sub(r"@ya\s*hoo\b", "@yahoo", v, flags=re.I)
        v = re.sub(r"@hot\s*mail\b", "@hotmail", v, flags=re.I)
        v = re.sub(r"@(?:g|gmai|gamil|qmail)\s*\.\s*com\b", "@gmail.com", v, flags=re.I)
        v = re.sub(r"(@[A-Za-z0-9-]+)\s*\.\s*([A-Za-z]{2,6}\b)", r"\1.\2", v)
        match = re.search(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+)", v)
        if not match:
            return (re.sub(r"\s+", " ", value).strip() or None), False
        local, domain = match.group(1), match.group(2)
        rest = v[match.end():]
        tld_at_domain = re.match(r"\.([A-Za-z]{2,6}(?:\.[A-Za-z]{2})?)", rest)
        if tld_at_domain:
            domain = f"{domain}.{tld_at_domain.group(1)}"
        else:
            # OCR often splits ".com" away from the domain; look ahead for it.
            tld_nearby = TLD_RE.search(rest[:30])
            if tld_nearby:
                domain = f"{domain}.{tld_nearby.group(1)}"
            elif domain.lower() in KNOWN_EMAIL_PROVIDERS:
                domain = f"{domain}.com"
        email = f"{local}@{domain}".lower().strip(".")
        return email, bool(EMAIL_RE.match(email))

    def _normalize_name(self, value: str) -> Tuple[Optional[str], bool]:
        v = self._collapse_boxed_letters(value.strip(" .,:;*_-"))
        v = re.sub(r"\s+", " ", v)
        # Digit/letter confusions inside otherwise alphabetic words (R1YA).
        v = re.sub(r"(?<=[A-Za-z])[01]|[01](?=[A-Za-z])", lambda m: {"0": "O", "1": "I"}[m.group(0)], v)
        if not v:
            return None, False
        tokens = [t.strip(".,*:").lower() for t in v.split()]
        if not 1 <= len(tokens) <= 5 or len(v) > 60:
            return v, False
        if any(t in NAME_STOPWORDS for t in tokens):
            return v, False
        alpha = sum(c.isalpha() for c in v)
        if alpha < 2 or alpha / max(len(v.replace(" ", "")), 1) < 0.8:
            return v, False
        return v, True

    def _normalize(self, value: str, field_type: str) -> Tuple[Optional[str], bool]:
        if field_type == "email":
            return self._normalize_email(value)
        if field_type == "name":
            return self._normalize_name(value)

        # Addresses keep their commas: they separate the address lines.
        value = re.sub(r"\s+", " ", value).strip(" :;_" if field_type == "address" else " :;,_")
        if not value:
            return None, False

        if field_type == "phone":
            digits = re.sub(r"\D", "", value.replace("O", "0").replace("o", "0"))
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
            if digits.startswith("0") and len(digits) == 11:
                digits = digits[1:]
            return (digits or None), len(digits) == 10

        if field_type == "pin":
            digits = re.sub(r"\D", "", value)
            return (digits[:6] or None), len(digits) == 6

        if field_type == "pan":
            compact = re.sub(r"[^A-Za-z0-9]", "", self._collapse_boxed_letters(value)).upper()
            match = re.search(r"[A-Z]{5,6}[0-9]{4}[A-Z]", compact)
            if match:
                return match.group(0), True
            return (compact or None), False

        if field_type == "date":
            compact = self._collapse_boxed_letters(value)
            match = re.search(r"\b(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2,4})\b", compact)
            if match:
                return "/".join(match.groups()), True
            digits = re.sub(r"\D", "", compact)
            if len(digits) == 8:
                return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}", True
            return value, False

        if field_type == "currency":
            match = re.search(r"(?:Rs\.?|₹|\$)?\s*\d[\d,]*(?:\.\d{1,2})?", value)
            if match and sum(c.isdigit() for c in match.group(0)) >= 2:
                return match.group(0).strip(), True
            return value, False

        if field_type == "identifier":
            compact = re.sub(r"\s+", "", self._collapse_boxed_letters(value)).upper()
            valid = bool(re.fullmatch(r"[A-Z0-9/\-]{4,25}", compact)) and sum(c.isdigit() for c in compact) >= 2
            return (compact or None), valid

        if field_type == "address":
            boilerplate = re.search(
                r"(?i)\b(same as above|please|tick|if any|if available|must not exceed|percentage)\b", value
            )
            valid = 4 <= len(value) <= 120 and not boilerplate
            return value, valid

        # plain string fields: reject prose paragraphs
        value = self._collapse_boxed_letters(value)
        valid = 2 <= len(value) <= 60 and len(value.split()) <= 6
        return value, valid

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
