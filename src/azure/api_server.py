from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# ระบุ Path ภายใน Docker ให้ตรงกับที่ Mount ไว้ใน docker-compose
SCRIPT_PATH = "/home/node/azure/vm-control-api.sh"

def get_target_os():
    """ดักจับเป้าหมาย VM จาก Query Parameter หรือ Hostname"""
    # 1. เช็คจากพารามิเตอร์ตรงๆ (เช่น ?target=win) - วิธีนี้เสถียรที่สุดสำหรับ URL ชุดใหม่ของคุณ
    target = request.args.get('target')
    if target:
        return target.lower()

    # 2. เช็คจากชื่อโดเมน (Fallback ในกรณีไม่ได้ใส่พารามิเตอร์)
    host = request.headers.get('X-Forwarded-Host', request.host).lower()
    if 'win.sandbox' in host:
        return 'win'
    elif 'linux.sandbox' in host:
        return 'linux'
    
    return ''

def execute_bash(action):
    """ส่งคำสั่งไปประมวลผลผ่าน Shell Script"""
    target = get_target_os()
    
    if not target:
        return {
            "status": "error", 
            "message": "Missing target. Please use ?target=win or ?target=linux"
        }

    cmd = ["/bin/bash", SCRIPT_PATH, action, target]
    print(f"🚀 EXECUTING: {' '.join(cmd)}")

    try:
        # บังคับรันในโฟลเดอร์ที่เก็บสคริปต์เพื่อให้ get-token.sh ทำงานได้ถูกต้อง
        result = subprocess.run(
            cmd, 
            cwd="/home/node/azure", 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        return {
            "status": "success",
            "action": action,
            "target": target,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- API Endpoints ---

@app.route('/start', methods=['GET', 'POST'])
def api_start():
    return jsonify(execute_bash("start"))

@app.route('/stop', methods=['GET', 'POST'])
def api_stop():
    return jsonify(execute_bash("stop"))

@app.route('/status', methods=['GET'])
def api_status():
    return jsonify(execute_bash("status"))

if __name__ == '__main__':
    print("=========================================")
    print(" 🛡️ AZURE VM CONTROL API ONLINE")
    print(" 🌐 URL: http://azure.sandbox.npu.world:5000")
    print("=========================================")
    app.run(host='0.0.0.0', port=5000)