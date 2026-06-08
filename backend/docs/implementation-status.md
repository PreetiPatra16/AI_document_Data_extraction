# Backend V1 Implementation Status

## Verified On The Supplied Corpus

- Persistent async jobs, separate worker execution, progress events, retries, and SQLite WAL are implemented.
- Uploads are streamed, content-validated, page-limited, and stored under generated names.
- PDFs are rendered page-by-page.
- OCR failures never produce mock or fabricated text.
- PaddleOCR and local TrOCR adapters are implemented and provisioned for the
  current local and Docker environments.
- Tesseract printed OCR, known-form classification, generic extraction, normalization, confidence, and review flags are implemented.
- Every supplied document reached a terminal state and all source/derived files were deleted.
- Populated health claim typed-field accuracy: **91.7%** over approved ground truth.
- Automated tests: **15 passing**.

## Corpus Smoke Results

| Sample | Classification | Reliable values | Result |
|---|---|---:|---|
| Populated health claim PDF | `health_claim_form` | 13 | Completed, review required for weak fields |
| Blank health proposal PDF | `health_proposal_form` | 5 printed/layout values | Completed |
| WhatsApp proposal photo | `health_proposal_form` | 5 | Completed |
| Motor claim photo | `motor_claim_form` | 0 | Completed with `no_fields_extracted`, review required |
| Unknown WhatsApp photo | `generic_form` | 0 | Completed with unsupported/no-fields warnings |

## Remaining Release Blockers

These cannot be truthfully marked complete without additional assets or approved data:

1. Human-review and approve handwritten ground-truth annotations for the photographed samples.
2. Tune handwritten-region routing against those annotations until accuracy reaches 75%.
3. Add template alignment, checkbox selection, and table row extraction for fields selected during annotation review.
4. Run the documented 100-page memory/concurrency benchmark on the target 8-core/16-GB machine.

The backend is now a reliable implementation foundation and meets the typed-field
accuracy gate. It must not be declared fully release-ready until the blockers
above are verified.
