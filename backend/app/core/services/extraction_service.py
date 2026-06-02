import re
from typing import List, Dict, Any, Tuple
from loguru import logger
import math

class ExtractionService:
    def __init__(self):
        # Definitions of v1 Form Templates
        # Each template contains a dictionary of target fields, their matching labels, regex rules, and coordinates.
        self.templates = {
            "invoice": {
                "name": "Standard Invoice Template",
                "fields": {
                    "invoice_number": {
                        "labels": ["invoice number", "invoice #", "inv no", "inv #"],
                        "regex": r"(?:inv|invoice)?[-#:\s]*([a-zA-Z0-9-]+)",
                        "type": "string"
                    },
                    "date": {
                        "labels": ["date", "invoice date", "dated"],
                        "regex": r"(\b\d{1,2}[/\-\s]\d{1,2}[/\-\s]\d{2,4}\b|\b[a-zA-Z]{3,9}\s\d{1,2},\s\d{4}\b)",
                        "type": "date"
                    },
                    "total_amount": {
                        "labels": ["total amount", "grand total", "total due", "amount due", "total"],
                        "regex": r"\$?\s*([\d,]+\.\d{2})",
                        "type": "currency"
                    },
                    "tax_rate": {
                        "labels": ["tax rate", "tax", "vat"],
                        "regex": r"([\d\.]+)\s*%",
                        "type": "percentage"
                    }
                }
            },
            "application_form": {
                "name": "General Application Form",
                "fields": {
                    "first_name": {
                        "labels": ["first name", "given name", "fname"],
                        "regex": r"([a-zA-Z]+)",
                        "type": "string"
                    },
                    "last_name": {
                        "labels": ["last name", "surname", "lname"],
                        "regex": r"([a-zA-Z]+)",
                        "type": "string"
                    },
                    "email": {
                        "labels": ["email address", "email", "e-mail"],
                        "regex": r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
                        "type": "email"
                    },
                    "phone": {
                        "labels": ["phone number", "phone", "tel", "mobile"],
                        "regex": r"((?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
                        "type": "phone"
                    },
                    "signature": {
                        "labels": ["signature", "signed by", "sign here"],
                        "regex": r"\[?handwritten:\s*([^\]]+)\]?|([a-zA-Z\s]+)",
                        "type": "signature"
                    }
                }
            }
        }

    async def extract_data(self, ocr_results: List[Dict[str, Any]], filename: str) -> Dict[str, Any]:
        """
        Runs template-driven extraction matching labels, regex rules, and computing
        custom confidence scores based on OCR score, regex match, and label-value distances.
        """
        logger.info(f"Starting field extraction for {filename} with {len(ocr_results)} OCR items.")
        
        # 1. Identify which template to use
        template_key = self._classify_document(ocr_results, filename)
        logger.info(f"Selected template: {template_key}")
        
        # Get selected template fields
        template_def = self.templates.get(template_key)
        if not template_def:
            # Fallback to default raw output
            return {
                "document_type": "generic",
                "fields": self._extract_generic_fields(ocr_results),
                "confidence_summary": 0.85
            }
            
        fields_config = template_def["fields"]
        extracted_fields = {}
        total_confidence = 0.0
        field_count = 0
        
        # 2. Extract each field based on template specifications
        for field_name, config in fields_config.items():
            field_result = self._extract_field(ocr_results, config)
            if field_result:
                extracted_fields[field_name] = field_result
                total_confidence += field_result["confidence"]
                field_count += 1
            else:
                extracted_fields[field_name] = {
                    "value": None,
                    "confidence": 0.0,
                    "bounding_box": None,
                    "page": 1,
                    "raw_text": None
                }
                
        avg_confidence = total_confidence / field_count if field_count > 0 else 0.0
        
        return {
            "document_type": template_key,
            "fields": extracted_fields,
            "confidence_summary": round(avg_confidence, 2)
        }

    def _classify_document(self, ocr_results: List[Dict[str, Any]], filename: str) -> str:
        """Classifies document to a template using filename keywords and OCR keyword hits."""
        name_lower = filename.lower()
        if "invoice" in name_lower:
            return "invoice"
        if "form" in name_lower or "app" in name_lower:
            return "application_form"
            
        # Analyze OCR text for keywords
        ocr_text_pool = " ".join([item["text"].lower() for item in ocr_results])
        
        invoice_hits = sum(1 for kw in ["invoice", "tax invoice", "amount due", "bill to"] if kw in ocr_text_pool)
        form_hits = sum(1 for kw in ["application", "first name", "email address", "signature"] if kw in ocr_text_pool)
        
        if invoice_hits > form_hits and invoice_hits > 0:
            return "invoice"
        elif form_hits > invoice_hits and form_hits > 0:
            return "application_form"
            
        return "generic"

    def _extract_field(self, ocr_results: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts to extract a single field by locating its label in OCR space,
        finding the nearest-neighbor / right-neighbor / bottom-neighbor value block,
        applying validation regex, and computing robust confidence scores.
        """
        target_labels = config["labels"]
        regex_pattern = config["regex"]
        
        best_candidate = None
        
        # Traverse OCR results to find labels
        for idx, ocr_item in enumerate(ocr_results):
            text = ocr_item["text"].lower().strip()
            
            # Check if this OCR block contains one of our target labels
            matching_label = next((lbl for lbl in target_labels if lbl in text), None)
            if not matching_label:
                continue
                
            label_box = ocr_item["bounding_box"]
            label_page = ocr_item["page"]
            
            # Now find a value candidate. Values are usually next to the label (same line/right) 
            # or directly below it. We'll search OCR items on the same page.
            candidates = []
            for other_idx, other_item in enumerate(ocr_results):
                if other_idx == idx or other_item["page"] != label_page:
                    continue
                    
                other_box = other_item["bounding_box"]
                
                # Compute spatial relationship
                dx = other_box["x"] - (label_box["x"] + label_box["width"])
                dy = other_box["y"] - label_box["y"]
                
                # Candidate 1: Right neighbor (same horizontal band, distance not too far)
                is_right = -15 < dy < 15 and 0 <= dx < 300
                
                # Candidate 2: Bottom neighbor (vertically aligned, down not too far)
                is_bottom = -20 < (other_box["x"] - label_box["x"]) < 50 and 0 < (other_box["y"] - (label_box["y"] + label_box["height"])) < 60
                
                if is_right or is_bottom:
                    candidates.append((other_item, dx, dy, "right" if is_right else "bottom"))
                    
            # Let's inspect the label block itself as sometimes the label and value are combined 
            # (e.g. "Invoice Number: INV-001")
            matches = re.search(regex_pattern, ocr_item["text"], re.IGNORECASE)
            if matches:
                matched_val = next((m for m in matches.groups() if m), ocr_item["text"])
                ocr_conf = ocr_item["confidence"]
                # Combined block gets high proximity score (distance = 0)
                score = self._compute_confidence(ocr_conf, regex_match=1.0, distance_factor=1.0)
                
                candidate = {
                    "value": matched_val.strip(": ").strip(),
                    "confidence": score,
                    "bounding_box": label_box,
                    "page": label_page,
                    "raw_text": ocr_item["text"]
                }
                if not best_candidate or score > best_candidate["confidence"]:
                    best_candidate = candidate
                    
            # Check separate candidates
            for cand_item, dx, dy, alignment in candidates:
                cand_text = cand_item["text"]
                matches = re.search(regex_pattern, cand_text, re.IGNORECASE)
                if matches:
                    matched_val = next((m for m in matches.groups() if m), cand_text)
                    ocr_conf = cand_item["confidence"]
                    
                    # Compute spatial distance penalty
                    distance = math.sqrt(dx**2 + dy**2) if alignment == "right" else dy
                    distance_factor = max(0.1, 1.0 - (distance / 400.0))  # Closer is better
                    
                    score = self._compute_confidence(ocr_conf, regex_match=1.0, distance_factor=distance_factor)
                    
                    candidate = {
                        "value": matched_val.strip(),
                        "confidence": score,
                        "bounding_box": cand_item["bounding_box"],
                        "page": label_page,
                        "raw_text": cand_text
                    }
                    if not best_candidate or score > best_candidate["confidence"]:
                        best_candidate = candidate
                        
        return best_candidate

    def _compute_confidence(self, ocr_confidence: float, regex_match: float, distance_factor: float) -> float:
        """
        Combines three dimensions:
        - OCR Confidence (from model output)
        - Regex match score (1.0 for matches, lower or None if invalid pattern)
        - Distance Factor (relative location to label, 1.0 is perfect)
        """
        # Weighted average
        score = (ocr_confidence * 0.4) + (regex_match * 0.3) + (distance_factor * 0.3)
        return round(min(1.0, max(0.0, score)), 2)

    def _extract_generic_fields(self, ocr_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generic fallback when no template matches."""
        # Return first 10 text blocks parsed directly as generic metadata key-values
        generic_data = {}
        for idx, item in enumerate(ocr_results[:10]):
            generic_data[f"block_{idx+1}"] = {
                "value": item["text"],
                "confidence": item["confidence"],
                "bounding_box": item["bounding_box"],
                "page": item["page"]
            }
        return generic_data
