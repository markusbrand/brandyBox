## Purpose

Provides an administrative web dashboard interface to screen syncing client health, inspect structured diagnostic error events, and export diagnostic context directly to the clipboard for LLM error analysis.

## Requirements

### Requirement: Client synchronization status matrix
The Web UI SHALL display a consolidated matrix of all active and historical client connections with their current sync state and timing.

#### Scenario: Admin views client sync status
- **WHEN** an administrator navigates to the Diagnostics section in the Web UI
- **THEN** the system displays a table of clients indicating device name, client type, version, last sync time, duration, and status (OK, warning, or error).

### Requirement: Searchable and filterable diagnostic error event feed
The Web UI SHALL provide an interactive feed of diagnostic error events with expandable technical details.

#### Scenario: Admin filters and inspects a failure event
- **WHEN** an administrator views the event feed and selects an error entry
- **THEN** the interface reveals the structured metadata including trace identifier, error code, file path, chunk index, and HTTP response context.

### Requirement: One-click LLM diagnostic context clipboard export
The Web UI SHALL provide a single-click action to copy formatted diagnostic details of any error or sync run to the system clipboard for use with an LLM.

#### Scenario: Admin clicks copy LLM context
- **WHEN** an administrator clicks "Copy LLM Context" on an error event or failed sync summary
- **THEN** the application formats the system version, client specs, error chain, and timeline into a clean Markdown block and copies it to the clipboard with a confirmation toast.
