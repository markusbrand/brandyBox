## Why

Users who sync or upload files containing currency symbols (such as `$`, `€`, `£`, `¥`) or Unicode symbols (such as `©`, `™`, `°`), or temporary Office lockfiles (such as `~$Document.docx`), currently experience HTTP 400 Bad Request errors (`Unsafe path segment`) and perpetual desktop client sync failures. The path segment sanitization regex and Unicode validation reject these safe characters unnecessarily.

## What Changes

- Permit `$` and Unicode Symbol categories (`S`, including `Sc`, `Sm`, `Sk`, `So`) in backend storage path segment sanitization and validation.
- Allow filenames such as `Invoice_$100.pdf`, `Budget_€50.xlsx`, and `~$Doc.docx` to be safely resolved and stored without compromising path traversal safeguards.

## Capabilities

### New Capabilities

### Modified Capabilities
- `file-storage`: Update path sanitization requirements to allow currency and Unicode symbol characters in path segments.

## Impact

- `backend/app/files/storage.py`: Update `_SAFE_SEGMENT_ASCII` regex and `_is_safe_path_char` Unicode category filter.
- `backend/tests/test_storage.py`: Add unit test coverage for filenames with currency symbols and other symbols.
- Desktop client sync will no longer reject uploads of documents containing currency symbols or Office lockfile prefixes.
