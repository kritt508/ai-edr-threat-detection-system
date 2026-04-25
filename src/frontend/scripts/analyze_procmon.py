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

# Import CAPA library (if available)
try:
    import capa.main
    import capa.rules
    import capa.engine
    from capa.features.extractors.dnfile import DnfileFeatureExtractor
    from capa.features.extractors.pefile import PefileFeatureExtractor
    CAPA_AVAILABLE = True
except ImportError:
    CAPA_AVAILABLE = False

# Argument Parser Setup
parser = argparse.ArgumentParser(description='Hybrid Malware Analysis (Signature + Anomaly)')
parser.add_argument('--input', type=str, required=True, help='Input JSON string or file path')
parser.add_argument('--rules', type=str, default='/opt/capa-rules', help='Path to CAPA rules')
args = parser.parse_args()

# ==========================================
# 1. Anomaly Detection Module (Behavior)
# ==========================================

def calculate_entropy(data):
    """Calculates Shannon Entropy (Chapter 2.6.1) [cite: 210]"""
    if not data: return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(chr(x))) / len(data)
        if p_x > 0:
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def detect_beaconing(network_logs):
    """Detects Beaconing activity (Chapter 2.6.2) [cite: 213]"""
    beacon_scores = []
    if not network_logs: return []

    df = pd.DataFrame(network_logs)
    if 'UtcTime' not in df.columns or 'DestinationIp' not in df.columns:
        return []

    df['UtcTime'] = pd.to_datetime(df['UtcTime'])
    grouped = df.groupby('DestinationIp')

    for ip, group in grouped:
        if len(group) < 4: continue
        
        # Calculate time delta consistency (Variance)
        sorted_times = group['UtcTime'].sort_values()
        time_deltas = sorted_times.diff().dt.total_seconds().dropna()
        
        variance = time_deltas.var()
        mean_interval = time_deltas.mean()
        
        # Threshold: Variance < 10 indicates highly consistent timing (Robot/Botnet)
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
    """Analyzes PE file structure and CAPA capabilities"""
    results = []
    score_bump = 0.0
    
    if not os.path.exists(file_path):
        return [], 0.0

    try:
        pe = pefile.PE(file_path)
        
        # 2.1 Check Import Hash (Imphash)
        imphash = pe.get_imphash()
        results.append({"type": "Signature", "key": "Imphash", "value": imphash})
        
        # 2.2 Check Section Entropy (Look for Packed Code)
        for section in pe.sections:
            entropy = section.get_entropy()
            if entropy > 7.5: # Packed section detected
                score_bump += 0.3
                results.append({
                    "type": "Packed Section", 
                    "section": section.Name.decode('utf-8', 'ignore').strip(r'\x00'),
                    "entropy": f"{entropy:.2f}"
                })

        # 2.3 Capa Analysis (If library and rules exist)
        if CAPA_AVAILABLE and os.path.exists(args.rules):
            # Note: Calling CAPA via Python script is complex
            # Placeholder results are used here to prevent script failure; subprocess logic can be added later
            # For POC stability, basic PE checks are prioritized
            pass

    except Exception as e:
        results.append({"type": "Static Analysis Error", "error": str(e)})

    return results, score_bump

# ==========================================
# Main Execution
# ==========================================

def main():
    try:
        # 1. Ingest Input Data
        try:
            input_data = json.loads(args.input)
        except:
            if os.path.exists(args.input):
                with open(args.input, 'r', encoding='utf-8-sig') as f:
                    input_data = json.load(f)
            else:
                input_data = []

        # Convert single Dict input to List
        if isinstance(input_data, dict):
            input_data = [input_data]

        analysis_result = {
            "is_anomaly": False,
            "threat_score": 0.0,
            "details": []
        }

        # 2. Segregate Log Types
        network_events = [x for x in input_data if x.get('EventID') == 3]
        process_events = [x for x in input_data if x.get('EventID') == 1]

        # ---------------------------------------------------------
        # A. Hybrid Analysis: Signature & Static (If file exists)
        # ---------------------------------------------------------
        # Identify referenced files in the log (Image Path)
        target_files = set([x.get('Image') for x in process_events if x.get('Image')])
        
        for file_path in target_files:
            # Note: In Docker, Windows paths (C:\...) won't match Linux paths
            # Requires volume mapping or mock files in /home/node/malware_samples/
            # Check if file exists for testing purposes
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
        # D. Conclusion (Consensus Input)
        # ---------------------------------------------------------
        if analysis_result["threat_score"] > 0.8:
            analysis_result["is_anomaly"] = True
            
        # Limit score to 1.0 (100%) maximum
        analysis_result["threat_score"] = min(analysis_result["threat_score"], 1.0)

        print(json.dumps(analysis_result))

    except Exception as e:
        print(json.dumps({"error": str(e), "is_anomaly": False, "threat_score": 0.0}))

if __name__ == "__main__":
    main()