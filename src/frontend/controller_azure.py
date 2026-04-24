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
        print(f"🔍 ตรวจสอบสถานะเครื่องเสมือนสำหรับ: {target}...")
        result = subprocess.run(
            ["/bin/bash", AZURE_SCRIPT, "status", target],
            cwd=AZURE_DIR,
            capture_output=True,
            text=True
        )
        output = result.stdout.strip()
        print(f"📊 ผลลัพธ์สถานะ: {output}")
        
        if "VM running" in output:
            return "running"
        elif "VM starting" in output:
            return "starting"
        elif "VM deallocated" in output:
            return "stopped"
        else:
            return "unknown"
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการตรวจสอบสถานะ: {str(e)}")
        return "error"

def azure_control(action, target):
    try:
        print(f"⚙️ สั่งการ Azure: {action} -> {target}")
        result = subprocess.run(
            ["/bin/bash", AZURE_SCRIPT, action, target],
            cwd=AZURE_DIR,
            capture_output=True,
            text=True
        )
        print(f"✅ ผลลัพธ์จาก Azure: {result.stdout.strip()}")
        return result.stdout.strip()
    except Exception as e:
        print(f"❌ ข้อผิดพลาดในการควบคุม Azure: {str(e)}")
        return str(e)

@app.route('/analyze', methods=['POST'])
def analyze():
    print("\n" + "="*50)
    print("🚀 ได้รับคำร้องขอการวิเคราะห์ไฟล์")
    print("="*50)

    # 1. รับข้อมูลจากหน้าเว็บ
    if 'file' not in request.files:
        return jsonify({"error": "ไม่พบไฟล์ที่อัปโหลด"}), 400
    
    file = request.files['file']
    file_content = file.read()
    
    # รับค่าเสริมจาก Query Parameters ที่หน้าเว็บส่งมา
    filename = request.args.get('filename') or file.filename
    received_os = request.args.get('target_os') # รับ Windows/Linux จากหน้าเว็บ
    received_hash = request.args.get('hash')    # รับ Hash จากหน้าเว็บ
    
    # ถ้าไม่มีการส่งมา ให้คำนวณและวิเคราะห์เองใหม่ (Fallback)
    file_hash = received_hash if received_hash else get_file_hash(file_content)
    
    if not received_os:
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        os_target = "win" if ext in ['exe', 'dll', 'msi', 'bat', 'ps1', 'py', 'csv'] else "linux"
    else:
        # แปลงค่าให้ตรงกับสคริปต์ Azure (windows -> win)
        os_target = "win" if "win" in received_os.lower() else "linux"
    
    print(f"📂 ชื่อไฟล์: {filename}")
    print(f"💻 ระบบปฏิบัติการเป้าหมาย: {os_target}")
    print(f"🔑 รหัสแฮช (SHA256): {file_hash}")

    try:
        # 2. จัดการสถานะเครื่องเสมือนบน Azure
        current_status = check_vm_status(os_target)
        if current_status == "stopped":
            print(f"⚠️ เครื่องเสมือนถูกปิดอยู่ กำลังเริ่มระบบ {os_target}...")
            azure_control("start", os_target) 
            time.sleep(2)
        elif current_status in ["running", "starting"]:
            print(f"✅ เครื่องเสมือนอยู่ในสถานะ {current_status} พร้อมใช้งาน")
        else:
            print("⚠️ ไม่ทราบสถานะที่แน่ชัด กำลังพยายามเริ่มระบบ...")
            azure_control("start", os_target)

        # 3. ส่งข้อมูลทั้งหมดไปยัง n8n Webhook
        print(f"📤 กำลังส่งข้อมูลไปยัง n8n: {N8N_WEBHOOK_URL}")
        
        # แนบข้อมูลสำคัญไปกับ URL เพื่อความแม่นยำในการบันทึกข้อมูล
        n8n_target_url = f"{N8N_WEBHOOK_URL}?filename={filename}&os={os_target}&hash={file_hash}"
        
        n8n_response = requests.post(
            n8n_target_url,
            files={'file': (filename, file_content, file.content_type)},
            data={
                'filename': filename,
                'os': os_target,
                'sha256': file_hash
            },
            timeout=900 # รอการวิเคราะห์ 15 นาที
        )

        print(f"📩 การตอบกลับจาก n8n (Status Code): {n8n_response.status_code}")
        
        if n8n_response.status_code == 200:
            result_data = n8n_response.json()
            print("✅ กระบวนการวิเคราะห์เสร็จสมบูรณ์")
            return jsonify(result_data)
        else:
            print(f"❌ ข้อผิดพลาดจาก n8n: {n8n_response.text}")
            return jsonify({"error": "กระบวนการวิเคราะห์ล้มเหลว", "details": n8n_response.text}), 500

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดร้ายแรง: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🌟 ระบบควบคุมเครื่องเสมือนวิเคราะห์มัลแวร์พร้อมทำงาน (พอร์ต 5001)")
    app.run(host='0.0.0.0', port=5001, debug=True)