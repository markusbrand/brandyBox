## ADDED Requirements

### Requirement: Admin User Creation Password Handling
The desktop client SHALL perform administrative user creation without bypassing server-side email notifications, and SHALL present any returned temporary password directly to the administrator with clipboard copy support.

#### Scenario: User creation with server-configured SMTP
- **WHEN** an administrator creates a new user through the desktop client and the server has SMTP configured
- **THEN** the client does not send the `X-E2E-Return-Temp-Password` header, allowing the server to deliver the initial password email, and informs the administrator that credentials have been emailed

#### Scenario: User creation without server SMTP or with returned temporary password
- **WHEN** an administrator creates a new user through the desktop client and the server returns a temporary password in the response payload
- **THEN** the client displays the temporary password in a completion dialog with an option to copy the password to the clipboard before dismissing
