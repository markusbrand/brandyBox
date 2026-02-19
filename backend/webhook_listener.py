import hmac
import hashlib
import subprocess
import os
from pathlib import Path

from flask import Flask, request, abort

# Load .env from backend directory so GITHUB_WEBHOOK_SECRET can be set there (file not committed)
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip("'\"")

app = Flask(__name__)

# Webhook secret: must match the value in GitHub repo → Settings → Webhooks → Secret.
# Set in backend/.env as GITHUB_WEBHOOK_SECRET=... or in the environment.
GITHUB_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "").encode("utf-8") or b"" 

def verify_signature(payload, signature):
    if not signature or not signature.startswith('sha256='):
        return False
    sha_name, sig = signature.split('=')
    mac = hmac.new(GITHUB_SECRET, msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    if not GITHUB_SECRET:
        abort(503)  # Secret not configured
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        abort(403)
    
    data = request.json
    # Wir reagieren, wenn der Build-Workflow erfolgreich abgeschlossen wurde
    if data.get('action') == 'completed' and data.get('workflow_run', {}).get('conclusion') == 'success':
        print("Neues Package bereit. Starte Update...")
        script_path = os.path.join(os.path.dirname(__file__), 'update_brandybox.sh')
        subprocess.Popen(['/bin/bash', script_path])
        return "Update angestoßen", 200
    
    return "Kein Update erforderlich", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "9000"))
    app.run(host='0.0.0.0', port=port)
