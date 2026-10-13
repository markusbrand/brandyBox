## ADDED Requirements

### Requirement: Path Sanitization Allows Currency and Unicode Symbols
The storage layer SHALL allow file and directory path segments containing ASCII currency symbol `$` and Unicode symbols (such as currency symbols `€`, `£`, `¥` and common symbols `©`, `™`, `°`) as well as Office temporary lockfiles (such as `~$Document.docx`) to be safely resolved and stored without raising validation errors.

#### Scenario: User uploads file with currency symbol
- **WHEN** an authenticated user uploads a file with a name containing `$` or Unicode currency symbols like `Invoice_$100.pdf` or `Receipt_€50.pdf`
- **THEN** the system resolves the storage path successfully and accepts the upload instead of returning HTTP 400 Bad Request

#### Scenario: User syncs Office temporary lockfile
- **WHEN** a client uploads or syncs a temporary file starting with `~$` such as `~$Project.docx`
- **THEN** the system resolves the storage path successfully and allows the operation without raising an unsafe path segment error
