## Context

`backend/app/files/storage.py` sanitizes path segments via `_sanitize_segment` and validates paths with `resolve_user_path`.
Currently, `_SAFE_SEGMENT_ASCII` regex is:
`r"^[a-zA-Z0-9_. \-()+~#!&',;=\[\]@]+$"`
and Unicode character checking in `_is_safe_path_char` is:
```python
cat = unicodedata.category(ch)
return cat.startswith("L") or cat.startswith("N") or cat.startswith("P")
```
This excludes the ASCII character `$` and any Unicode character in the Symbol (`S`) category (which includes `Sc` Currency, `Sm` Math, `Sk` Modifier, `So` Other).
Filenames with dollar signs (e.g. `Invoice_$100.pdf` or `~$Document.docx`), euro signs (`Budget_€50.xlsx`), etc., fail sanitization and raise `ValueError("Unsafe path segment")`, returning HTTP 400 Bad Request to clients and breaking desktop sync loops.

## Goals / Non-Goals

**Goals:**
- Allow `$` in ASCII segment matching.
- Allow `$` and Unicode category `S` (symbols, including currency symbols) in `_is_safe_path_char`.
- Ensure directory traversal (`..`, `.`, `/`, `\`), null bytes, control characters, and reserved device names remain strictly disallowed.

**Non-Goals:**
- Changing path separators or directory nesting structure.
- Modifying client sync upload logic.

## Decisions

- **Decision 1: Include `$` in `_SAFE_SEGMENT_ASCII` and `_is_safe_path_char`**
  - Rationale: `$` is a common and standard filename character in modern operating systems (Linux, macOS, Windows) and commonly used in Office temporary files (`~$...`) and financial documents. It poses no filesystem traversal hazard.
  - Alternative considered: Escaping or stripping `$` - rejected because filenames must match on both client and server for hash-based sync.

- **Decision 2: Include Unicode category `S` in `_is_safe_path_char`**
  - Rationale: Unicode category `S` covers Currency (`Sc` like `€`, `£`, `¥`), Math (`Sm`), Modifier (`Sk`), and Other symbols (`So` like `©`, `®`, `°`). Allowing `cat.startswith("S")` in addition to Letters (`L`), Numbers (`N`), and Punctuation (`P`) correctly allows legitimate international symbols while continuing to reject control characters (`C`), formatting characters (`Cf`), marks (`M`), or whitespace separators (`Z`, handled explicitly as spaces).

## Risks / Trade-offs

- [Risk] Permitting additional characters could unintentionally allow shell or injection characters →
  - Mitigation: BrandyBox uses Python's standard `pathlib.Path` and direct filesystem system calls (no shell execution / `subprocess` calls on file paths), and directory separators (`/`, `\`) and traversal (`..`, `.`) remain strictly blocked by earlier checks.
