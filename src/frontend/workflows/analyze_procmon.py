import sys
import json
import pandas as pd
import os

# รับ Path ของไฟล์ Log จาก Argument ที่ n8n ส่งมา
if len(sys.argv) < 2:
    print(json.dumps({"error": "No input file provided"}))
    sys.exit(1)

log_file_path = sys.argv[1]
ioc_file_path = '/home/node/project_malware/workflows/apt29_iocs.json'

results = {
    "status": "clean",
    "detected_threats": [],
    "analysis_summary": "No threats detected."
}

try:
    # 1. โหลด IoCs ของ APT29
    if os.path.exists(ioc_file_path):
        with open(ioc_file_path, 'r') as f:
            iocs = json.load(f)
    else:
        iocs = []

    # 2. อ่านไฟล์ Log (สมมติว่าเป็น CSV จาก Sysmon/Procmon)
    # ถ้าไฟล์จริงเป็น JSON ให้เปลี่ยนเป็น pd.read_json
    df = pd.read_csv(log_file_path, encoding='utf-8-sig', on_bad_lines='skip')
    
    # 3. เริ่มกระบวนการวิเคราะห์ (Threat Hunting)
    detected = []

    # 3.1 ตรวจสอบชื่อไฟล์อันตราย (RDP Files ตามคลิปวิดีโอ)
    rdp_threats = [ioc['value'] for ioc in iocs if ioc['type'] == 'filename']
    for threat in rdp_threats:
        # สมมติ column ใน log ชื่อ 'ProcessName' หรือ 'TargetFilename'
        if 'TargetFilename' in df.columns:
            matches = df[df['TargetFilename'].str.contains(threat, case=False, na=False)]
            if not matches.empty:
                detected.append(f"CRITICAL: Found APT29 Phishing File -> {threat}")

    # 3.2 ตรวจสอบ Command Line (เช่น Powershell encoded)
    cmd_threats = [ioc['value'] for ioc in iocs if ioc['type'] == 'command_line']
    for threat in cmd_threats:
        if 'CommandLine' in df.columns:
            matches = df[df['CommandLine'].str.contains(threat, case=False, na=False)]
            if not matches.empty:
                detected.append(f"SUSPICIOUS: Potential Living-off-the-Land tactic -> {threat}")

    # 3.3 ตรวจสอบ IP Address (C2 Communication)
    ip_threats = [ioc['value'] for ioc in iocs if ioc['type'] == 'ip']
    for threat in ip_threats:
        if 'DestinationIp' in df.columns:
            matches = df[df['DestinationIp'] == threat]
            if not matches.empty:
                detected.append(f"HIGH: Connection to known APT29 C2 -> {threat}")

    # 4. สรุปผล
    if detected:
        results["status"] = "infected"
        results["detected_threats"] = detected
        results["analysis_summary"] = f"Detected {len(detected)} potential threats linked to Midnight Blizzard."
    
    # ส่งผลลัพธ์กลับไปให้ n8n ในรูปแบบ JSON
    print(json.dumps(results))

except Exception as e:
    error_response = {
        "status": "error",
        "message": str(e)
    }
    print(json.dumps(error_response))