from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import hashlib
import subprocess
import time
import os

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
N8N_WEBHOOK_URL = os.getenv("API_URL", "http://n8n_core:5678/webhook/analyze-malware")
AZURE_DIR = "/home/node/azure"
AZURE_SCRIPT = "./vm-control-api.sh"

def get_file_hash(file_content):
    return hashlib.sha256(file_content).hexdigest()

def check_vm_status(target):
    try:
        print(f"🔍 Checking VM status for: {target}...")
        result = subprocess.run(
            ["/bin/bash", AZURE_SCRIPT, "status", target],
            cwd=AZURE_DIR,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()
        print(f"📊 Status result: {output}")
        
        if "VM running" in output:
            return "running"
        elif "VM starting" in output:
            return "starting"
        elif "VM deallocated" in output:
            return "stopped"
        else:
            return "unknown"
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        return "error"

def azure_control(action, target):
    try:
        print(f"⚙️ Azure command: {action} -> {target}")
        result = subprocess.run(
            ["/bin/bash", AZURE_SCRIPT, action, target],
            cwd=AZURE_DIR,
            capture_output=True,
            text=True
        )
        print(f"✅ Result from Azure: {result.stdout.strip()}")
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ Error controlling Azure: {str(e)}")
        return str(e)

@app.route('/analyze', methods=['POST'])
def analyze():
    print("\n" + "="*50)
    print("🚀 Analysis request received")
    print("="*50)

    # 1. รับข้อมูลจากหน้าเว็บ
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    file_content = file.read()
    
    # Extract additional parameters from web query
    filename = request.args.get('filename') or file.filename
    received_os = request.args.get('target_os') # OS target from web
    received_hash = request.args.get('hash')    # Hash from web
    
    # Fallback: calculate hash if not provided
    file_hash = received_hash if received_hash else get_file_hash(file_content)
    
    if not received_os:
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        os_target = "win" if ext in ['exe', 'dll', 'msi', 'bat', 'ps1', 'py', 'csv'] else "linux"
    else:
        # Map OS to Azure script convention (windows -> win)
        os_target = "win" if "win" in received_os.lower() else "linux"
    
    print(f"📂 Filename: {filename}")
    print(f"💻 Target OS: {os_target}")
    print(f"🔑 Hash (SHA256): {file_hash}")

    try:
        # 2. Manage Azure VM status
        current_status = check_vm_status(os_target)
        if current_status == "stopped":
            print(f"⚠️ VM is deallocated. Starting {os_target} system...")
            azure_control("start", os_target) 
            time.sleep(2)
        elif current_status in ["running", "starting"]:
            print(f"✅ VM is {current_status} and ready for use")
        else:
            print("⚠️ Unknown status. Attempting to start system...")
            azure_control("start", os_target)

        # 3. Dispatch data to n8n Webhook
        print(f"📤 Forwarding data to n8n: {N8N_WEBHOOK_URL}")
        
        # Append critical data to URL for precise tracking
        n8n_target_url = f"{N8N_WEBHOOK_URL}?filename={filename}&os={os_target}&hash={file_hash}"
        
        n8n_response = requests.post(
            n8n_target_url,
            files={'file': (filename, file_content, file.content_type)},
            data={
                'filename': filename,
                'os': os_target,
                'sha256': file_hash
            },
            timeout=900 # Wait for analysis (15-minute timeout)
        )

        print(f"📩 Response from n8n (Status Code): {n8n_response.status_code}")
        
        if n8n_response.status_code == 200:
            result_data = n8n_response.json()
            print("✅ Analysis process complete")
            return jsonify(result_data)
        else:
            print(f"❌ Error from n8n: {n8n_response.text}")
            return jsonify({"error": "Analysis process failed", "details": n8n_response.text}), 500

    except Exception as e:
        print(f"❌ Critical error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🌟 Malware Analysis VM Controller is ready (Port 5001)")
    app.run(host='0.0.0.0', port=5001, debug=True)