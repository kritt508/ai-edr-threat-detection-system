import sys
import pandas as pd
import json

# Path ของไฟล์ CSV ที่ถูกส่งมาจาก n8n
file_path = sys.argv[1]

# คอลัมน์จาก ProcMon ที่มีประโยชน์ที่สุดในการวิเคราะห์พฤติกรรม
RELEVANT_COLUMNS = [
    'Operation', 
    'Path', 
    'Detail'
]

try:
    # อ่านไฟล์ CSV
    df = pd.read_csv(file_path, on_bad_lines='skip')

    # ตรวจสอบว่ามีคอลัมน์ที่เราสนใจหรือไม่
    available_columns = [col for col in RELEVANT_COLUMNS if col in df.columns]

    if not available_columns:
        print(json.dumps({"error": "CSV does not contain 'Operation', 'Path', or 'Detail' columns.", "file_path": file_path}))
        sys.exit()

    # กรอง DataFrame ให้เหลือเฉพาะคอลัมน์ที่จำเป็น
    filtered_df = df[available_columns]

    # ลบแถวที่ข้อมูลเป็นค่าว่างทั้งหมด
    filtered_df = filtered_df.dropna(how='all')

    # --- ส่วนสำคัญ: สรุปข้อมูล (Data Reduction) ---
    # เพื่อป้องกัน AI Token Limit เกิน
    # เราจะนับพฤติกรรม (แถว) ที่ซ้ำกัน
    event_counts = filtered_df.groupby(available_columns).size().reset_index(name='count')

    # จัดเรียงจากมากไปน้อย และเลือก 50 อันดับแรก
    top_events_df = event_counts.sort_values(by='count', ascending=False).head(50)

    # แปลง DataFrame สรุปนี้เป็น JSON string
    events_json = top_events_df.to_json(orient='records')

    # เตรียมข้อมูลส่งออก
    output = {
        "file_name": file_path.split('/')[-1],
        "total_unique_events": len(event_counts),
        "top_50_events_for_analysis": json.loads(events_json) # แปลงกลับเป็น JSON object ให้ n8n
    }

    # พิมพ์ผลลัพธ์เป็น JSON String ให้ n8n (stdout)
    print(json.dumps(output))

except Exception as e:
    print(json.dumps({"error": str(e), "file_path": file_path}))