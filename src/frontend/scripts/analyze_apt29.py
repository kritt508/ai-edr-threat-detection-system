import os
import sys

def analyze_file(file_path):
    print(f"[*] Analyzing: {file_path}")
    
    # 1. ตรวจสอบ IOCs (Indicators of Compromise) เบื้องต้น
    # เช่น การเช็คชื่อไฟล์, Path หรือค่า Hash ที่เกี่ยวข้องกับ APT29
    apt29_signatures = ["wellmess", "nobelium", "sunburst"]
    
    found_threats = []
    
    # สมมติว่าเป็นการสแกนหา String ในไฟล์
    try:
        with open(file_path, 'r', errors='ignore') as f:
            content = f.read().lower()
            for sig in apt29_signatures:
                if sig in content:
                    found_threats.append(sig)
    except Exception as e:
        return f"Error: {str(e)}"

    if found_threats:
        return f"[!] ALERT: Found APT29 related signatures: {found_threats}"
    else:
        return "[+] Clear: No known APT29 patterns found."

if __name__ == "__main__":
    # รับค่า Path ไฟล์จาก Command Line (เช่น python3 analyze_apt29.py sample.exe)
    if len(sys.argv) > 1:
        target = sys.argv[1]
        result = analyze_file(target)
        print(result)
    else:
        print("Usage: python3 analyze_apt29.py <file_path>")