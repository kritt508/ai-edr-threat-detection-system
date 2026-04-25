from flask import Flask, request, jsonify, send_file
import psutil
import subprocess
import os
import platform
import time
import re
import signal
import sys

app = Flask(__name__)
app.url_map.strict_slashes = False

# ========================================================
# 1. GLOBAL CONFIGURATION (LINUX VERSION)
# ========================================================
CONFIG = {
    "VERSION": "2.0.0-Linux-Root-Enforced", # Version Update
    "UPLOAD_FOLDER": "/tmp/malware_uploads",
    "TSHARK_EXE": "/usr/bin/tshark",
    "STRACE_EXE": "/usr/bin/strace",
    "READINESS_RETRY": 5,
    "STABILIZATION_DELAY": 2
}

if not os.path.exists(CONFIG["UPLOAD_FOLDER"]):
    os.makedirs(CONFIG["UPLOAD_FOLDER"], exist_ok=True)

STATE = {
    "tshark_pid": None,
    "current_pcap": None,
    "current_log": None
}

def get_default_route_info():
    try:
        route_output = subprocess.check_output(["ip", "route", "show", "default"]).decode()
        interface = re.search(r"dev (\S+)", route_output).group(1)
        addr_output = subprocess.check_output(["ip", "-4", "addr", "show", interface]).decode()
        ip_addr = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", addr_output).group(1)
        return ip_addr, interface
    except:
        return "127.0.0.1", "eth0"

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "os": platform.system(),
        "status": "online",
        "version": CONFIG["VERSION"],
        "is_root": os.geteuid() == 0, # Inform n8n if running with root privileges
        "supported_commands": ["POST /upload", "POST /execute", "POST /terminate/<pid>", "GET /list", "GET /status"],
        "upload_directory": CONFIG["UPLOAD_FOLDER"]
    }), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        file_path = os.path.join(CONFIG["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            if content.startswith(b'#!') or file.filename.endswith('.sh'):
                if b'\r\n' in content:
                    content = content.replace(b'\r\n', b'\n')
                    with open(file_path, 'wb') as f:
                        f.write(content)
        except Exception as e:
            pass

        os.chmod(file_path, 0o755)

        return jsonify({
            "message": "File uploaded successfully",
            "file_path": file_path
        }), 200

@app.route('/list', methods=['GET'])
def list_files():
    try:
        file_list = []
        with os.scandir(CONFIG["UPLOAD_FOLDER"]) as entries:
            for entry in entries:
                if entry.is_file():
                    file_list.append({
                        "name": entry.name,
                        "size_bytes": entry.stat().st_size
                    })

        return jsonify({
            "files": file_list,
            "count": len(file_list),
            "directory": CONFIG["UPLOAD_FOLDER"]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/execute', methods=['POST'])
def execute_malware():
    data = request.json or {}
    file_path = data.get('file_path')
    if not file_path: return jsonify({"error": "No file_path"}), 400

    if ":" in file_path or "/" not in file_path:
        file_path = os.path.join(CONFIG["UPLOAD_FOLDER"], os.path.basename(file_path))

    try:
        ts = int(time.time())
        STATE["current_pcap"] = os.path.join(CONFIG["UPLOAD_FOLDER"], f"capture_{ts}.pcap")
        STATE["current_log"] = os.path.join(CONFIG["UPLOAD_FOLDER"], f"strace_{ts}.log")

        host_ip, interface = get_default_route_info()
        exclude_mgmt = f"(host {host_ip} and (port 80 or port 5000))"
        exclude_ssh_in = f"(dst host {host_ip} and port 22)"
        cap_filter = f"not ({exclude_mgmt} or {exclude_ssh_in})"

        tshark_cmd = [
            CONFIG["TSHARK_EXE"], "-i", interface,
            "-f", cap_filter,
            "-w", STATE["current_pcap"], "-l"
        ]
        t_proc = subprocess.Popen(tshark_cmd)
        STATE["tshark_pid"] = t_proc.pid

        time.sleep(CONFIG["STABILIZATION_DELAY"])

        strace_cmd = [
            CONFIG["STRACE_EXE"], "-f", "-tt", "-v", "-s", "1024",
            "-o", STATE["current_log"], file_path
        ]

        os.chmod(file_path, 0o755)
        process = subprocess.Popen(strace_cmd, cwd=os.path.dirname(file_path))

        return jsonify({
            "status": "executed",
            "main_pid": process.pid,
            "pcap_file": os.path.basename(STATE["current_pcap"]),
            "log_file": os.path.basename(STATE["current_log"])
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/terminate/<int:pid>', methods=['POST'])
def terminate_api(pid):
    response_data = {"status": "terminated"}
    try:
        # 1. Terminate malware process
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except psutil.NoSuchProcess:
            pass

        # 2. Safely stop Tshark to prevent PCAP corruption
        if STATE["tshark_pid"]:
            try:
                os.kill(STATE["tshark_pid"], signal.SIGINT)
                time.sleep(2) # Wait for Tshark to finish file writing
                os.kill(STATE["tshark_pid"], signal.SIGKILL) # Force terminate if still running
            except ProcessLookupError:
                pass
            STATE["tshark_pid"] = None

        time.sleep(2)

        # 3. Convert PCAP file with timeout protection (30s limit)
        if STATE["current_pcap"] and os.path.exists(STATE["current_pcap"]):
            net_csv = STATE["current_pcap"].replace(".pcap", "_net.csv")
            tshark_conv = [
                CONFIG["TSHARK_EXE"], "-r", STATE["current_pcap"],
                "-T", "fields", "-E", "header=y", "-E", "separator=,",
                "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "_ws.col.Info"
            ]
            try:
                with open(net_csv, "w") as f:
                    subprocess.run(tshark_conv, stdout=f, timeout=30)
            except subprocess.TimeoutExpired:
                print("TShark conversion timed out, returning raw data.")

            response_data["net_csv"] = os.path.basename(net_csv)

            if os.path.exists(net_csv):
                with open(net_csv, "r", encoding="utf-8", errors="ignore") as f:
                    net_lines = f.readlines()
                    response_data["network_preview"] = "".join(net_lines[-100:])

        if STATE["current_log"] and os.path.exists(STATE["current_log"]):
            response_data["log_filtered"] = os.path.basename(STATE["current_log"])

            with open(STATE["current_log"], "r", encoding="utf-8", errors="ignore") as f:
                log_lines = f.readlines()
                response_data["log_preview"] = "".join(log_lines[-500:])

    except Exception as e:
        response_data["error"] = str(e)

    return jsonify(response_data), 200

@app.route('/download_pcap', methods=['GET'])
def download_file():
    filename = request.args.get('filename')
    file_path = os.path.join(CONFIG["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    # ========================================================
    # Enforce Root Privileges
    # ========================================================
    if os.geteuid() != 0:
        print("[!] ERROR: This agent MUST be run as root to capture network traffic and system calls.")
        print("[*] Please restart the agent using: sudo python3 agent.py")
        sys.exit(1)

    print("-" * 50)
    print(f"Linux Malware Analysis Agent v{CONFIG['VERSION']}")
    print("Privilege Status: [ OK ] - Running as ROOT")
    print("-" * 50)

    app.run(host='0.0.0.0', port=5000, threaded=True)