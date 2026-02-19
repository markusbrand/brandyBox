import hmac
import hashlib
import subprocess
import os
from flask import Flask, request, abort

app = Flask(__name__)

# Webhook secret: must match the value in GitHub repo → Settings → Webhooks → Secret.
# Prefer environment variable so the secret is not committed (e.g. set in .env or systemd).
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
    # Läuft auf Port 9000, den du via Cloudflare Tunnel ansprichst
    app.run(host='0.0.0.0', port=9000)
