# Release Verification Checklist

- [ ] `PYTHONPATH=. pytest` passes.
- [ ] API and worker start independently.
- [ ] `/api/v1/health/ready` reports required dependencies.
- [ ] Runtime networking is disabled.
- [ ] TrOCR and PaddleOCR assets are provisioned when marked required.
- [ ] Supplied sample corpus has approved ground truth.
- [ ] Typed accuracy is at least 90%.
- [ ] Handwritten accuracy is at least 75%.
- [ ] Success, OCR failure, timeout, and delete flows leave no document files.
- [ ] A 100-page PDF is processed incrementally.
- [ ] API remains responsive while worker processes documents.
- [ ] Logs contain no extracted values.
