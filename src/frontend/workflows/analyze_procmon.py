import sys
import json
import pandas as pd
import os

# Receive log file path from argument passed by n8n
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
    # 1. Load APT29 IoCs
    if os.path.exists(ioc_file_path):
        with open(ioc_file_path, 'r') as f:
            iocs = json.load(f)
    else:
        iocs = []

    # 2. Read log file (Assuming CSV from Sysmon/Procmon)
    # If actual file is JSON, use pd.read_json instead
    df = pd.read_csv(log_file_path, encoding='utf-8-sig', on_bad_lines='skip')
    
    # 3. Initiate Threat Hunting analysis
    detected = []

    # 3.1 Check for malicious filenames (e.g., malicious RDP files)
    rdp_threats = [ioc['value'] for ioc in iocs if ioc['type'] == 'filename']
    for threat in rdp_threats:
        # Assume log column is named 'ProcessName' or 'TargetFilename'
        if 'TargetFilename' in df.columns:
            matches = df[df['TargetFilename'].str.contains(threat, case=False, na=False)]
            if not matches.empty:
                detected.append(f"CRITICAL: Found APT29 Phishing File -> {threat}")

    # 3.2 Check command line arguments (e.g., encoded PowerShell)
    cmd_threats = [ioc['value'] for ioc in iocs if ioc['type'] == 'command_line']
    for threat in cmd_threats:
        if 'CommandLine' in df.columns:
            matches = df[df['CommandLine'].str.contains(threat, case=False, na=False)]
            if not matches.empty:
                detected.append(f"SUSPICIOUS: Potential Living-off-the-Land tactic -> {threat}")

    # 3.3 Check IP addresses (C2 Communication)
    ip_threats = [ioc['value'] for ioc in iocs if ioc['type'] == 'ip']
    for threat in ip_threats:
        if 'DestinationIp' in df.columns:
            matches = df[df['DestinationIp'] == threat]
            if not matches.empty:
                detected.append(f"HIGH: Connection to known APT29 C2 -> {threat}")

    # 4. Summary
    if detected:
        results["status"] = "infected"
        results["detected_threats"] = detected
        results["analysis_summary"] = f"Detected {len(detected)} potential threats linked to Midnight Blizzard."
    
    # Return results to n8n in JSON format
    print(json.dumps(results))

except Exception as e:
    error_response = {
        "status": "error",
        "message": str(e)
    }
    print(json.dumps(error_response))