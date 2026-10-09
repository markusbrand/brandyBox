## Purpose

Provides native macOS menu bar status item integration, dock icon suppression, visual sync state tracking using official branding, and standalone desktop runtime behavior for Brandy Box.

## ADDED Requirements

### Requirement: macOS Dock suppression
The macOS application SHALL operate strictly as an accessory UI element without presenting an icon in the macOS Dock or App Switcher.

#### Scenario: Background accessory operation
- **WHEN** the macOS application launches or runs in the background
- **THEN** the system process reports `background only: true` and does not display an icon in the macOS Dock.

### Requirement: Top-right status item placement
The desktop client SHALL position its status bar icon within the visible top-right section of the macOS menu bar, avoiding obstruction by screen cutouts or notches.

#### Scenario: Initial launch preferred position
- **WHEN** the application starts on macOS without prior user repositioning
- **THEN** it configures a preferred menu bar position placing it into the active right-hand status area.

#### Scenario: Status item menu interaction
- **WHEN** the user clicks or right-clicks the status menu item
- **THEN** the application presents a context menu containing actions for "Settings", "Open sync folder", "Sync now", and "Quit".

### Requirement: Cross-platform logo consistency
The desktop client SHALL display the official Brandy Box "B" logo with real-time sync state indications consistently across macOS and Linux platforms.

#### Scenario: State indication using official branding
- **WHEN** the application is idle/synced, syncing, or encountering an error
- **THEN** the menu bar / tray icon renders the full-color official Brandy Box square logo with white "B" (blue when synced, orange with status dot when syncing, red with status dot on error).

### Requirement: Settings window focus on menu selection
The desktop client SHALL restore, display, and bring the Settings window into active user focus when selected from the status menu.

#### Scenario: User selects Settings from status menu
- **WHEN** the user selects the "Settings" item from the tray menu
- **THEN** the Settings window is unminimized, shown, and activated in front of other running applications.

### Requirement: Production frontend embedding
The desktop client production binary SHALL bundle and serve all user interface frontend assets locally without relying on an external development server.

#### Scenario: Standalone client runtime without dev server
- **WHEN** the application is opened in production without a local Vite server running on port 1420
- **THEN** the Settings window immediately displays the complete user interface rather than a connection failure.
