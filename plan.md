1. Modify `get_user_by_email` in `backend/app/users/service.py` to use `session.get(User, email)` instead of `session.execute(select(User).where(User.email == email))`.
   - Reason: `session.get()` caches the entity in the identity map, which drastically speeds up repeated lookups (like authenticating API endpoints or looking up users).

2. Modify `get_current_user` in `backend/app/auth/dependencies.py` to use `session.get(User, email)` instead of `session.execute(select(User).where(User.email == email))`.
   - Reason: This is called on every authenticated request, making it a hot path. `session.get()` avoids hitting the DB for repeat lookups within the same session or for simple primary key access, making the app much faster.

3. Update `.jules/bolt.md` with this critical learning.

4. Run `ruff check --fix backend/` and `python -m pytest backend/tests/` to verify everything works.
