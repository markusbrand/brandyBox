# Brandy Box backend - Raspberry Pi
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY app/ ./app/

EXPOSE 8080

# No secrets in CMD; use env for BRANDYBOX_*
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
