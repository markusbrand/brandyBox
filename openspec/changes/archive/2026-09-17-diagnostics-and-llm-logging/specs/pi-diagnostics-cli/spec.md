## Purpose

Provides a command-line diagnostic tool (`brandybox-doctor`) runnable on the Raspberry Pi host to inspect cross-client sync health, trace correlated failures, and export LLM-optimized diagnostic bundles.

## ADDED Requirements

### Requirement: System and client health summary command
The CLI SHALL provide a command to display a consolidated health overview of all known clients and the backend server.

#### Scenario: User requests diagnostic summary
- **WHEN** the user executes `brandybox-doctor --summary` on the host or inside the container
- **THEN** the tool outputs server storage metrics, database status, client versions, and a summary of recent errors across all clients in the past 24 hours.

### Requirement: Correlated trace timeline command
The CLI SHALL provide a command to display the chronological sequence of client and server actions for a given trace identifier.

#### Scenario: User inspects a specific sync run
- **WHEN** the user executes `brandybox-doctor --trace <trace_id>`
- **THEN** the tool queries client diagnostic events and backend logs associated with `<trace_id>` and renders a unified, chronological timeline of operations and failure points.

### Requirement: LLM prompt bundle export command
The CLI SHALL provide a command to format diagnostic context, system specifications, and failure timelines into a structured Markdown prompt ready for LLM root-cause analysis.

#### Scenario: User exports diagnostic context for an AI assistant
- **WHEN** the user executes `brandybox-doctor --llm-prompt` (optionally filtered with `--last-error` or `--trace <trace_id>`)
- **THEN** the tool outputs a structured Markdown block containing system context, error details, relevant timeline steps, and a diagnostic task directive suitable for pasting into an LLM.
