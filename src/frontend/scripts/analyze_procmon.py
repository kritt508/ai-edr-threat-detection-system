import sys
import json
import math
import argparse
import os
import pandas as pd
import numpy as np
import pefile
import hashlib
from collections import Counter

# นำเข้า Library สำหรับ Capa (ถ้ามี)
try:
    import capa.main
    import capa.rules
    import capa.engine
    from capa.features.extractors.dnfile import DnfileFeatureExtractor
    from capa.features.extractors.pefile import PefileFeatureExtractor
    CAPA_AVAILABLE = True
except ImportError:
    CAPA_AVAILABLE = False

# ตั้งค่า Argument Parser
parser = argparse.ArgumentParser(description='Hybrid Malware Analysis (Signature + Anomaly)')
parser.add_argument('--input', type=str, required=True, help='Input JSON string or file path')
parser.add_argument('--rules', type=str, default='/opt/capa-rules', help='Path to CAPA rules')
args = parser.parse_args()

# ==========================================
# 1. Anomaly Detection Module (Behavior)
# ==========================================

def calculate_entropy(data):
    """คำนวณ Shannon Entropy (บทที่ 2.6.1) [cite: 210]"""
    if not data: return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(chr(x))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def detect_beaconing(network_logs):
    """ตรวจจับ Beaconing (บทที่ 2.6.2) [cite: 213]"""
    beacon_scores = []
    if not network_logs: return []

    df = pd.DataFrame(network_logs)
    if 'UtcTime' not in df.columns or 'DestinationIp' not in df.columns:
        return []

    df['UtcTime'] = pd.to_datetime(df['UtcTime'])
    grouped = df.groupby('DestinationIp')

    for ip, group in grouped:
        if len(group) < 4: continue
        
        # คำนวณความสม่ำเสมอของเวลา (Variance)
        sorted_times = group['UtcTime'].sort_values()
        time_deltas = sorted_times.diff().dt.total_seconds().dropna()
        
        variance = time_deltas.var()
        mean_interval = time_deltas.mean()
        
        # Threshold: Variance < 10 ถือว่าจังหวะเป๊ะมาก (Robot/Botnet)
        if variance < 10.0 and mean_interval > 0:
            beacon_scores.append({
                "type": "Beaconing Detected",
                "target_ip": ip,
                "interval_avg": f"{mean_interval:.2f}s",
                "variance": f"{variance:.2f}",
                "confidence": "High"
            })
    return beacon_scores

# ==========================================
# 2. Signature Detection Module (Static)
# ==========================================

def analyze_pe_file(file_path):
    """วิเคราะห์โครงสร้างไฟล์ PE และ Capa Capabilities """
    results = []
    score_bump = 0.0
    
    if not os.path.exists(file_path):
        return [], 0.0

    try:
        pe = pefile.PE(file_path)
        
        # 2.1 ตรวจสอบ Import Hash (Imphash)
        imphash = pe.get_imphash()
        results.append({"type": "Signature", "key": "Imphash", "value": imphash})
        
        # 2.2 ตรวจสอบ Section Entropy (หา Packed Code)
        for section in pe.sections:
            entropy = section.get_entropy()
            if entropy > 7.5: # Packed section detected
                score_bump += 0.3
                results.append({
                    "type": "Packed Section", 
                    "section": section.Name.decode('utf-8', 'ignore').strip(r'\x00'),
                    "entropy": f"{entropy:.2f}"
                })

        # 2.3 Capa Analysis (ถ้ามี Library และ Rules)
        if CAPA_AVAILABLE and os.path.exists(args.rules):
            # หมายเหตุ: การเรียก Capa ผ่าน Python script ค่อนข้างซับซ้อน 
            # ในที่นี้จะจำลองผลลัพธ์เพื่อไม่ให้ Script พัง หรือใส่ Logic เรียก subprocess ได้
            # เพื่อความเสถียรของ POC เราจะเช็ค PE เบื้องต้นก่อน
            pass

    except Exception as e:
        results.append({"type": "Static Analysis Error", "error": str(e)})

    return results, score_bump

# ==========================================
# Main Execution
# ==========================================

def main():
    try:
        # 1. รับข้อมูล Input
        try:
            input_data = json.loads(args.input)
        except:
            if os.path.exists(args.input):
                with open(args.input, 'r', encoding='utf-8-sig') as f:
                    input_data = json.load(f)
            else:
                input_data = []

        # ถ้า Input เข้ามาเป็น Dict เดียว ให้แปลงเป็น List
        if isinstance(input_data, dict):
            input_data = [input_data]

        analysis_result = {
            "is_anomaly": False,
            "threat_score": 0.0,
            "details": []
        }

        # 2. แยกประเภท Log
        network_events = [x for x in input_data if x.get('EventID') == 3]
        process_events = [x for x in input_data if x.get('EventID') == 1]

        # ---------------------------------------------------------
        # A. Hybrid Analysis: Signature & Static (ถ้ามีไฟล์จริง)
        # ---------------------------------------------------------
        # เช็คว่าใน Log มีการอ้างถึงไฟล์ไหนบ้าง (Image Path)
        target_files = set([x.get('Image') for x in process_events if x.get('Image')])
        
        for file_path in target_files:
            # หมายเหตุ: ใน Docker, path ของ Windows (C:\...) จะไม่ตรงกับ Linux
            # ต้องมีการ Map Volume หรือ Mock file ใน /home/node/malware_samples/
            # แต่ถ้าเป็นการทดสอบ ให้ลองเช็คว่าไฟล์มีจริงไหม
            if os.path.exists(file_path):
                static_details, score = analyze_pe_file(file_path)
                analysis_result["threat_score"] += score
                analysis_result["details"].extend(static_details)

        # ---------------------------------------------------------
        # B. Anomaly Analysis: Entropy (Command Line)
        # ---------------------------------------------------------
        for event in process_events:
            cmd_line = event.get('CommandLine', '')
            entropy = calculate_entropy(cmd_line)
            if entropy > 6.0:
                analysis_result["threat_score"] += 0.4
                analysis_result["details"].append({
                    "type": "High Entropy Command",
                    "value": f"{entropy:.2f}",
                    "command": cmd_line[:30] + "..."
                })

        # ---------------------------------------------------------
        # C. Anomaly Analysis: Beaconing (Network)
        # ---------------------------------------------------------
        beacons = detect_beaconing(network_events)
        if beacons:
            analysis_result["threat_score"] += 0.6 * len(beacons)
            analysis_result["details"].extend(beacons)

        # ---------------------------------------------------------
        # D. สรุปผล (Consensus Input)
        # ---------------------------------------------------------
        if analysis_result["threat_score"] > 0.8:
            analysis_result["is_anomaly"] = True
            
        # จำกัด Score ไม่ให้เกิน 1.0 (หรือ 100%)
        analysis_result["threat_score"] = min(analysis_result["threat_score"], 1.0)

        print(json.dumps(analysis_result))

    except Exception as e:
        print(json.dumps({"error": str(e), "is_anomaly": False, "threat_score": 0.0}))

if __name__ == "__main__":
    main()