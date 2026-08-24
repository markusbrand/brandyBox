import re

with open("backend/app/files/routes.py", "r") as f:
    content = f.read()

# I missed replacing the `uuid.UUID(upload_id)` when refactoring to rely on FastAPI type coercion!
content = content.replace('''    try:
        uuid.UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload_id format")

''', '')

with open("backend/app/files/routes.py", "w") as f:
    f.write(content)
