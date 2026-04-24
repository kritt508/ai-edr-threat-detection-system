from flask import Flask, request, jsonify, send_file
import psutil
import subprocess
import os
import platform
import time
import shutil
import ctypes
import sys

# ยกเลิกคำสั่ง shutdown ที่อาจถูกเรียกโดยมัลแวร์ทันทีเมื่อรัน Agent
os.system("shutdown /a")

app = Flask(__name__)
app.url_map.strict_slashes = False

# ========================================================
# 1. GLOBAL CONFIGURATION
# ========================================================
CONFIG = {
    "VERSION": "2.0.0", # อัปเดตเวอร์ชัน: Auto-Admin & Direct Capture
    "UPLOAD_FOLDER": r"C:\Users\cpe\AppData\Local\Temp\malware_uploads",
    "PROCMON_EXE": r"C:\Sysinternals\procmon.exe",
    "TSHARK_EXE": r"C:\Program Files\Wireshark\tshark.exe",
    "READINESS_RETRY": 15,
    "STABILIZATION_DELAY": 3,
    "CONVERSION_TIMEOUT_PML": 600, 
    "CONVERSION_TIMEOUT_NET": 600, 
    "CLEANUP_BEFORE_UPLOAD": True
}

if not os.path.exists(CONFIG["UPLOAD_FOLDER"]):
    os.makedirs(CONFIG["UPLOAD_FOLDER"])

STATE = {
    "tshark_process": None,
    "current_pcap": None,
    "current_log": None
}

# ========================================================
# 2. UTILITIES
# ========================================================

def is_admin():
    """ตรวจสอบว่า Agent กำลังรันด้วยสิทธิ์ Administrator หรือไม่"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def cleanup_upload_folder():
    """ล้างไฟล์ทั้งหมดในโฟลเดอร์อัปโหลด"""
    print("Cleaning up upload folder...")
    for filename in os.listdir(CONFIG["UPLOAD_FOLDER"]):
        file_path = os.path.join(CONFIG["UPLOAD_FOLDER"], filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def kill_process_by_name(name):
    subprocess.run(f'taskkill /F /T /IM {name}.exe', shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

def get_tshark_interface():
    """ค้นหาหมายเลข Interface ของการ์ดแลนที่ใช้งานจริงแบบอัตโนมัติ"""
    try:
        output = subprocess.check_output([CONFIG["TSHARK_EXE"], "-D"], text=True)
        for line in output.splitlines():
            if any(key in line for key in ["Ethernet", "Network", "Wi-Fi", "Microsoft"]):
                interface_id = line.split('.')[0].strip()
                print(f"Auto-selected Interface: {interface_id}")
                return interface_id
        return "1" 
    except Exception as e:
        print(f"Error detecting interface: {e}")
        return "1"

# ========================================================
# 3. ROUTES
# ========================================================

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "os": platform.system(),
        "status": "online",
        "version": CONFIG["VERSION"],
        "is_admin": is_admin(),
        "upload_directory": CONFIG["UPLOAD_FOLDER"]
    }), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if CONFIG["CLEANUP_BEFORE_UPLOAD"]:
        cleanup_upload_folder()

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    
    try:
        save_path = os.path.join(CONFIG["UPLOAD_FOLDER"], file.filename)
        file.save(save_path)
        return jsonify({"status": "success", "filename": file.filename}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/execute', methods=['POST'])
def execute_malware():
    if not is_admin():
        return jsonify({"error": "Agent is not running as Administrator. Capture tools will fail."}), 403

    data = request.json or {}
    raw_path = data.get('file_path')
    if not raw_path: return jsonify({"error": "No file_path"}), 400
    
    target_file = os.path.join(CONFIG["UPLOAD_FOLDER"], raw_path) if not os.path.isabs(raw_path) else raw_path

    if not os.path.exists(target_file):
        return jsonify({"error": f"File not found: {target_file}"}), 404

    try:
        ts = int(time.time())
        STATE["current_pcap"] = os.path.join(CONFIG["UPLOAD_FOLDER"], f"capture_{ts}.pcap")
        STATE["current_log"] = os.path.join(CONFIG["UPLOAD_FOLDER"], f"proc_{ts}.pml")
        
        # 1. Start Tshark (อัปเดต BPF Filter ให้จับ C2 ขาออกได้แม่นขึ้น)
        active_interface = get_tshark_interface()
        # ตัด Localhost และ Port ของ Flask/RDP ออก เพื่อจับเฉพาะ C2
        bpf_filter = "not port 5000 and not port 3389 and not net 127.0.0.0/8" 
        tshark_cmd = [CONFIG["TSHARK_EXE"], "-i", active_interface, "-f", bpf_filter, "-w", STATE["current_pcap"], "-l"]
        STATE["tshark_process"] = subprocess.Popen(tshark_cmd)
        
        # 2. Start Procmon
        kill_process_by_name("procmon")
        subprocess.run(f'"{CONFIG["PROCMON_EXE"]}" /Terminate /AcceptEula', shell=True)
        time.sleep(2)
        
        procmon_cmd = f'"{CONFIG["PROCMON_EXE"]}" /BackingFile "{STATE["current_log"]}" /Quiet /AcceptEula'
        subprocess.Popen(procmon_cmd, shell=True)
        
        time.sleep(CONFIG["STABILIZATION_DELAY"])
        
        # 3. Execute Malware (อัปเดตให้รันตรงๆ เพื่อจับ PID แม่นๆ)
        if target_file.lower().endswith('.bat'):
            # ถ้าเป็นสคริปต์ ให้รันผ่าน cmd
            process = subprocess.Popen(['cmd.exe', '/c', target_file], cwd=CONFIG["UPLOAD_FOLDER"])
        else:
            # ถ้าเป็น .exe ให้รันตรงๆ แบบไม่ผ่าน shell
            process = subprocess.Popen(f'"{target_file}"', shell=True, cwd=CONFIG["UPLOAD_FOLDER"])
            
        return jsonify({
            "status": "executed", 
            "main_pid": process.pid, 
            "file_executed": target_file,
            "is_admin": True
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/terminate/<int:pid>', methods=['POST'])
def terminate_api(pid):
    try:
        p = psutil.Process(pid)
        for child in p.children(recursive=True): child.kill()
        p.kill()
    except: pass

    subprocess.run(f'taskkill /F /T /IM tshark.exe', shell=True, stderr=subprocess.DEVNULL)
    subprocess.run(f'"{CONFIG["PROCMON_EXE"]}" /Terminate /AcceptEula', shell=True, stderr=subprocess.DEVNULL)
    
    time.sleep(15) 

    response_data = {"status": "terminated", "net_csv": None, "log_filtered": None}

    # แปลง PCAP เป็น CSV
    if STATE["current_pcap"] and os.path.exists(STATE["current_pcap"]):
        if os.path.getsize(STATE["current_pcap"]) > 0:
            net_csv = STATE["current_pcap"].replace(".pcap", "_net.csv")
            cmd = [CONFIG["TSHARK_EXE"], "-r", STATE["current_pcap"], "-T", "fields", "-E", "header=y", "-E", "separator=,", "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "_ws.col.Info"]
            try:
                with open(net_csv, "w", encoding='utf-8') as f:
                    subprocess.run(cmd, stdout=f, timeout=CONFIG["CONVERSION_TIMEOUT_NET"])
                if os.path.exists(net_csv): response_data["net_csv"] = os.path.basename(net_csv)
            except Exception as e: print(f"Error converting PCAP: {e}")

    # แปลง PML เป็น CSV
    if STATE["current_log"] and os.path.exists(STATE["current_log"]):
        filt_csv = STATE["current_log"].replace(".pml", "_filtered.csv")
        try:
            subprocess.run(f'"{CONFIG["PROCMON_EXE"]}" /OpenLog "{STATE["current_log"]}" /SaveAs "{filt_csv}" /Quiet /AcceptEula', 
                           shell=True, timeout=CONFIG["CONVERSION_TIMEOUT_PML"])
            if os.path.exists(filt_csv): response_data["log_filtered"] = os.path.basename(filt_csv)
        except Exception as e: print(f"Error converting PML: {e}")

    return jsonify(response_data), 200

@app.route('/download', methods=['GET'])
def download_file_api():
    filename = request.args.get('filename')
    file_path = os.path.join(CONFIG["UPLOAD_FOLDER"], filename) if filename else ""
    if os.path.exists(file_path): return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    # ========================================================
    # ระบบบังคับขอสิทธิ์ Administrator อัตโนมัติ (UAC Prompt)
    # ========================================================
    if not is_admin():
        print("[-] Agent needs Administrator privileges to capture malware logs.")
        print("[*] Requesting UAC elevation...")
        try:
            # สั่งรันตัวเองใหม่ด้วยสิทธิ์ Admin
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0) # ปิดโปรเซสตัวเก่าที่ไม่มีสิทธิ์ทิ้ง
        except Exception as e:
            print(f"[!] Elevation failed: {e}. Please manually run as Administrator.")
            sys.exit(1)
            
    print("-" * 50)
    print(f"Malware Analysis Agent v{CONFIG['VERSION']}")
    print(f"Running on: {platform.system()} {platform.release()}")
    print("Privilege Status: [ OK ] - Running as Administrator")
    print("-" * 50)
    
    app.run(host='0.0.0.0', port=5000, threaded=True)
