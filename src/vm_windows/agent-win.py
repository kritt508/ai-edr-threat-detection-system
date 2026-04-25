from flask import Flask, request, jsonify, send_file
import psutil
import subprocess
import os
import platform
import time

app = Flask(__name__)
app.url_map.strict_slashes = False

# ========================================================
# 1. GLOBAL CONFIGURATION
# ========================================================
CONFIG = {
    "VERSION": "1.7.7",
    "UPLOAD_FOLDER": r"C:\Users\cpe\AppData\Local\Temp\malware_uploads",
    "PROCMON_EXE": r"C:\Sysinternals\procmon.exe",
    "TSHARK_EXE": r"C:\Program Files\Wireshark\tshark.exe",
    "READINESS_RETRY": 15,
    "STABILIZATION_DELAY": 3,
    "CONVERSION_TIMEOUT_PML": 300,
    "CONVERSION_TIMEOUT_NET": 60
}

# Create upload folder if it doesn't exist
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
    try:
        return subprocess.getoutput("net session").find("Access is denied.") == -1
    except:
        return False

def is_process_running(name):
    for proc in psutil.process_iter(['name']):
        try:
            if name.lower() in proc.info['name'].lower(): return True
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return False

def kill_process_by_name(name):
    for proc in psutil.process_iter(['name']):
        try:
            if name.lower() in proc.info['name'].lower(): proc.kill()
        except: pass

# ========================================================
# 3. ROUTES
# ========================================================

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "os": platform.system(),
        "status": "online",
        "version": CONFIG["VERSION"], 
        "supported_commands": ["POST /upload", "POST /execute", "POST /terminate/<pid>", "GET /list", "GET /status"],
        "upload_directory": CONFIG["UPLOAD_FOLDER"]
    }), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    try:
        save_path = os.path.join(CONFIG["UPLOAD_FOLDER"], file.filename)
        file.save(save_path)
        return jsonify({
            "status": "success",
            "filename": file.filename,
            "path": save_path
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/list', methods=['GET'])
def list_files():
    try:
        files = os.listdir(CONFIG["UPLOAD_FOLDER"])
        return jsonify({"files": files, "count": len(files)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/execute', methods=['POST'])
def execute_malware():
    data = request.json or {}
    raw_path = data.get('file_path')
    if not raw_path: return jsonify({"error": "No file_path"}), 400
    
    # Path Fix: If only filename is provided, look in the upload folder
    if not os.path.isabs(raw_path):
        target_file = os.path.join(CONFIG["UPLOAD_FOLDER"], raw_path)
    else:
        target_file = raw_path

    # Check if file exists
    if not os.path.exists(target_file):
        return jsonify({"error": f"File not found: {target_file}"}), 404

    try:
        ts = int(time.time())
        STATE["current_pcap"] = os.path.join(CONFIG["UPLOAD_FOLDER"], f"capture_{ts}.pcap")
        STATE["current_log"] = os.path.join(CONFIG["UPLOAD_FOLDER"], f"proc_{ts}.pml")
        
        # 1. Start Tshark
        tshark_cmd = f'"{CONFIG["TSHARK_EXE"]}" -i 4 -f "not port 5000" -w "{STATE["current_pcap"]}" -l'
        STATE["tshark_process"] = subprocess.Popen(tshark_cmd, shell=True)
        
        # 2. Start Procmon
        kill_process_by_name("procmon")
        subprocess.run(f'"{CONFIG["PROCMON_EXE"]}" /Terminate /AcceptEula', shell=True)
        time.sleep(2)
        
        procmon_cmd = f'"{CONFIG["PROCMON_EXE"]}" /BackingFile "{STATE["current_log"]}" /Quiet /AcceptEula'
        subprocess.Popen(procmon_cmd, shell=True)
        
        # Wait for tools to be ready
        ready = False
        for _ in range(CONFIG["READINESS_RETRY"]):
            if is_process_running("tshark.exe") and is_process_running("procmon"):
                ready = True
                break
            time.sleep(1)
        
        time.sleep(CONFIG["STABILIZATION_DELAY"])
        
        # --- Critical Fix: Resolve WinError 123 by specifying explicit cwd ---
        process = subprocess.Popen(f'"{target_file}"', shell=True, cwd=CONFIG["UPLOAD_FOLDER"])
            
        return jsonify({
            "status": "executed", 
            "tools_ready": ready, 
            "is_admin": is_admin(),
            "main_pid": process.pid,
            "file_executed": target_file
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
    
    if STATE["tshark_process"]:
        try: STATE["tshark_process"].terminate()
        except: pass
        STATE["tshark_process"] = None
    
    subprocess.run(f'"{CONFIG["PROCMON_EXE"]}" /Terminate /AcceptEula', shell=True)
    time.sleep(5)

    response_data = {"status": "terminated"}

    # Convert PCAP to CSV
    if STATE["current_pcap"] and os.path.exists(STATE["current_pcap"]):
        net_csv = STATE["current_pcap"].replace(".pcap", "_net.csv")
        cmd = [CONFIG["TSHARK_EXE"], "-r", STATE["current_pcap"], "-T", "fields", "-E", "header=y", "-E", "separator=,", "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "_ws.col.Info"]
        with open(net_csv, "w") as f:
            subprocess.run(cmd, stdout=f, timeout=CONFIG["CONVERSION_TIMEOUT_NET"])
        if os.path.exists(net_csv): response_data["net_csv"] = os.path.basename(net_csv)

    # Convert PML to CSV
    if STATE["current_log"] and os.path.exists(STATE["current_log"]):
        filt_csv = STATE["current_log"].replace(".pml", "_filtered.csv")
        subprocess.run(f'"{CONFIG["PROCMON_EXE"]}" /OpenLog "{STATE["current_log"]}" /SaveAs "{filt_csv}" /Quiet /AcceptEula', shell=True, timeout=CONFIG["CONVERSION_TIMEOUT_PML"])
        if os.path.exists(filt_csv): 
            response_data["log_filtered"] = os.path.basename(filt_csv)

    return jsonify(response_data), 200

@app.route('/download', methods=['GET'])
def download_file_api():
    filename = request.args.get('filename')
    if not filename: return jsonify({"error": "No filename"}), 400
    file_path = os.path.join(CONFIG["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path): return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    print(f"Malware Analysis Agent v{CONFIG['VERSION']} is starting...")
    print(f"Monitoring folder: {CONFIG['UPLOAD_FOLDER']}")
    app.run(host='0.0.0.0', port=5000, threaded=True)

