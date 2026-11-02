## MODIFIED Requirements

### Requirement: Correlated trace timeline command
The CLI SHALL provide a command to display the chronological sequence of client and server actions for a given trace identifier.

#### Scenario: User inspects a specific sync run
- **WHEN** the user executes `brandybox-doctor --trace <trace_id>`
- **THEN** the tool queries client diagnostic events and backend logs associated with `<trace_id>` and renders a unified, chronological timeline of operations and failure points, sorting mixed naive and timezone-aware timestamps safely without errors.
