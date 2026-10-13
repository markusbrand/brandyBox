## 1. Storage Path Sanitization Updates

- [x] 1.1 Update `_SAFE_SEGMENT_ASCII` regex and `_is_safe_path_char` in `backend/app/files/storage.py` to allow `$` and Unicode category `S` symbols
- [x] 1.2 Add unit tests in `backend/tests/test_storage.py` covering currency symbols (`$`, `€`, `£`), lockfiles (`~$Doc.docx`), and Unicode symbols, and verify with pytest
- [x] 1.3 Run full QA test suite via `./scripts/run-qa.sh` to ensure all tests pass
