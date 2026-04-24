import streamlit as st
import requests
import json
import plotly.graph_objects as go
import pandas as pd
import time
import hashlib
import threading
from datetime import datetime
import io

# --- ⚙️ CONFIGURATION ---
API_URL = "http://streamlit_ui:5001/analyze" 

# --- 🎨 PAGE CONFIG ---
# อัปเดตชื่อบนแท็บเบราว์เซอร์
st.set_page_config(
    page_title="การออกแบบและพัฒนาระบบรักษาความปลอดภัยปลายทางด้วยโมเดลภาษาขนาดใหญ่เพื่อการตรวจจับและป้องกันภัยไซเบอร์",
    page_icon="🛡️",
    layout="wide"
)

# --- 💅 ENTERPRISE LIGHT THEME CSS (เหมาะสำหรับลงวิทยานิพนธ์) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&family=Share+Tech+Mono&display=swap');
    
    /* พื้นหลังหลักสีขาว ตัวหนังสือสีเทาเข้มเกือบดำ */
    .stApp { background-color: #ffffff; color: #24292f; font-family: 'Sarabun', sans-serif; }
    h1, h2, h3, h4 { color: #0969da; font-weight: 700; } /* หัวข้อสีน้ำเงินทางการ */
    code { font-family: 'Share Tech Mono', monospace; color: #cf222e; background-color: #f6f8fa; padding: 2px 6px; border-radius: 4px; border: 1px solid #d0d7de; }
    
    /* กล่องรายงานต่างๆ */
    .report-card { background: #ffffff; border: 1px solid #d0d7de; border-left: 4px solid #0969da; padding: 18px; border-radius: 6px; color: #24292f; line-height: 1.6; margin-bottom: 15px; white-space: pre-wrap; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    
    /* ป้ายสถานะความเสี่ยง (สีสว่างขึ้น) */
    .badge-malicious { color: #cf222e; border: 1px solid #ff8182; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 18px; background: #ffebe9; }
    .badge-suspicious { color: #9a6700; border: 1px solid #d4a72c; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 18px; background: #fff8c5; }
    .badge-safe { color: #1a7f37; border: 1px solid #4ac26b; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 18px; background: #dafeef; }
    
    .metric-box { background-color: #ffffff; padding: 15px; border-radius: 6px; border: 1px solid #d0d7de; color: #24292f; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .pre-analysis-box { background: #f3f8ff; border: 1px solid #0969da; border-left: 5px solid #0969da; color: #24292f; padding: 20px; border-radius: 6px; margin-bottom: 20px; }
    .criteria-box { background: #f6f8fa; border: 1px dashed #8c959f; padding: 15px; border-radius: 6px; font-size: 14px; color: #57606a; }
    
    /* กล่องแสดงเวลา (อัปเดตใหม่ แก้อักษรมองไม่เห็น) */
    .time-box-blue { background-color: #f0f7ff; border: 1px solid #d0d7de; border-left: 4px solid #0969da; padding: 12px 15px; border-radius: 6px; margin-bottom: 12px; color: #24292f; font-weight: bold; }
    .time-box-orange { background-color: #fff8c5; border: 1px solid #d0d7de; border-left: 4px solid #d4a72c; padding: 12px 15px; border-radius: 6px; margin-bottom: 12px; color: #24292f; font-weight: bold; }
    
    /* ปรับปุ่มดาวน์โหลด */
    .stDownloadButton button { background-color: #f6f8fa; border: 1px solid #d0d7de; color: #0969da; font-weight: bold; transition: all 0.2s; }
    .stDownloadButton button:hover { background-color: #0969da; color: #ffffff; border-color: #0969da; }
    
    /* อนิเมชั่นสำหรับการรัน Sandbox */
    @keyframes pulse-live { 0% { box-shadow: 0 0 0 0 rgba(9, 105, 218, 0.2); } 70% { box-shadow: 0 0 0 10px rgba(9, 105, 218, 0); } 100% { box-shadow: 0 0 0 0 rgba(9, 105, 218, 0); } }
    @keyframes blinker { 50% { opacity: 0; } }
    .live-sandbox-box { background: #ffffff; border: 1px solid #0969da; border-left: 5px solid #0969da; color: #24292f; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px; animation: pulse-live 2s infinite; font-size: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .live-sandbox-box span.blink-text { color: #cf222e; font-weight: bold; animation: blinker 1s linear infinite; }
    .completed-sandbox-box { background: #dafeef; border: 1px solid #1a7f37; border-left: 5px solid #1a7f37; color: #24292f; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px; }
    
    /* แต่ง Tabs ให้ดูเป็นเอกสารมากขึ้น */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #d0d7de; }
    .stTabs [data-baseweb="tab"] { background-color: #f6f8fa; border: 1px solid #d0d7de; border-bottom: none; border-radius: 6px 6px 0px 0px; padding: 8px 16px; color: #57606a; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #0969da; color: white; border-color: #0969da; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔍 1. ฟังก์ชันวิเคราะห์ไส้ในไฟล์ (แยก OS)
# ==========================================
def analyze_file_static(file_bytes, filename):
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    header = file_bytes[:4]
    magic_hex = header.hex().upper()
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    warning_msg = None
    target_env = "unknown"
    
    if file_bytes.startswith(b'MZ'):
        os_target = "ระบบปฏิบัติการ Windows (ไฟล์โปรแกรมที่รันได้ .exe/.dll)"
        sandbox_route = "🪟 ส่งไปยังกล่องทราย Windows (Azure VM)"
        target_env = "windows"
        os_reason = "ตรวจสอบพบโครงสร้างไฟล์แบบ 'MZ Header' ซึ่งเป็นมาตรฐานของโปรแกรมบน Windows"
        if ext and ext not in ['exe', 'dll', 'sys', 'scr', 'bin']: warning_msg = f"⚠️ ข้อสังเกต นามสกุลไฟล์คือ .{ext} แต่ไส้ในที่แท้จริงคือโปรแกรม Windows อาจเป็นการปลอมแปลงเพื่อหลอกผู้ใช้"
    elif file_bytes.startswith(b'\x7fELF'):
        os_target = "ระบบปฏิบัติการ Linux (ไฟล์โปรแกรมที่รันได้ ELF)"
        sandbox_route = "🐧 ส่งไปยังกล่องทราย Linux (Azure VM)"
        target_env = "linux"
        os_reason = "ตรวจสอบพบโครงสร้างไฟล์แบบ 'ELF Header' ซึ่งเป็นมาตรฐานของโปรแกรมบน Linux"
        if ext in ['exe', 'dll', 'txt', 'pdf', 'jpg', 'png']: warning_msg = f"⚠️ ข้อสังเกต นามสกุลไฟล์คือ .{ext} แต่ไส้ในที่แท้จริงคือโปรแกรม Linux"
    elif file_bytes.startswith(b'#!'):
        os_target = "ระบบปฏิบัติการ Linux (สคริปต์คำสั่ง)"
        sandbox_route = "🐧 ส่งไปยังกล่องทราย Linux (Azure VM)"
        target_env = "linux"
        os_reason = "ตรวจสอบพบสัญลักษณ์ '#!' (Shebang) ซึ่งใช้สำหรับรันสคริปต์บนระบบ Linux"
    elif ext in ['csv', 'pcap', 'log', 'txt', 'bat', 'sh']:
        filename_lower = filename.lower()
        if 'linux' in filename_lower or ext == 'sh':
            os_target = "สคริปต์หรือข้อมูลสำหรับระบบ Linux"
            sandbox_route = "🐧 ส่งไปยังกล่องทราย Linux (Azure VM)"
            target_env = "linux"
            os_reason = "ประเมินจากนามสกุลไฟล์ (.sh) หรือชื่อไฟล์"
        elif 'win' in filename_lower or 'proc' in filename_lower or ext == 'bat':
            os_target = "สคริปต์หรือข้อมูลสำหรับระบบ Windows"
            sandbox_route = "🪟 ส่งไปยังกล่องทราย Windows (Azure VM)"
            target_env = "windows"
            os_reason = "ประเมินจากนามสกุลไฟล์ (.bat) หรือชื่อไฟล์"
        else:
            os_target = "ข้อมูลหรือเอกสารทั่วไป (ไม่ใช่โปรแกรม)"
            sandbox_route = "📦 วิเคราะห์ด้วยระบบพื้นฐาน"
            target_env = "data"
            os_reason = "เป็นนามสกุลไฟล์เอกสารทั่วไป ไม่มีโครงสร้างที่ใช้รันโปรแกรมได้โดยตรง"
    else:
        os_target = "ไม่ทราบประเภทที่แน่ชัด"
        sandbox_route = "📦 เลือกระบบวิเคราะห์อัตโนมัติ"
        target_env = "unknown"
        os_reason = "ไม่พบ Header มาตรฐานที่ระบุระบบปฏิบัติการเป้าหมายได้ชัดเจน"
        if ext in ['exe', 'dll', 'elf', 'sh']: warning_msg = f"⚠️ ระวัง ไฟล์นามสกุล .{ext} แต่ไม่มีโครงสร้างโปรแกรมที่ถูกต้อง อาจเป็นไฟล์ที่ถูกดัดแปลง"

    return sha256_hash, os_target, sandbox_route, magic_hex, warning_msg, target_env, os_reason

def get_file_size_format(num_bytes):
    for unit in ['B', 'KB', 'MB']:
        if num_bytes < 1024.0: return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} GB"

def create_gauge_chart(score):
    v_color = "#1a7f37" if score <= 3 else "#d4a72c" if score <= 7 else "#cf222e"
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 10], 'tickcolor': "#24292f", 'tickwidth': 1},
            'bar': {'color': v_color},
            'bgcolor': "#f6f8fa",
            'steps': [
                {'range': [0, 3], 'color': '#dafeef'}, 
                {'range': [3, 7], 'color': '#fff8c5'},
                {'range': [7, 10], 'color': '#ffebe9'}
            ],
            'threshold': {'line': {'color': "#24292f", 'width': 3}, 'thickness': 0.75, 'value': score}
        }
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "#24292f", 'family': 'Sarabun'}, height=250, margin=dict(t=40, b=10, l=30, r=30))
    return fig

# ==========================================
# 🖥️ 2. UI LAYOUT & SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("### 🛠️ สถานะระบบ")
    st.status("เซิร์ฟเวอร์พร้อมใช้งาน", state="complete")
    st.divider()
    st.caption(f"โครงสร้างพื้นฐาน ห้องปฏิบัติการกล่องทราย (Sandbox)")
    st.caption(f"สภาพแวดล้อมจำลอง เครื่องเสมือน Azure (Windows และ Linux)")
    st.caption(f"เวลาปัจจุบัน {datetime.now().strftime('%H:%M:%S')}")

# อัปเดตหัวข้อหลักบนหน้าเว็บให้ตรงกับชื่อวิทยานิพนธ์
st.markdown("<h2 style='color: #0969da;'>🛡️ การออกแบบและพัฒนาระบบรักษาความปลอดภัยปลายทางด้วยโมเดลภาษาขนาดใหญ่<br>เพื่อการตรวจจับและป้องกันภัยไซเบอร์</h2>", unsafe_allow_html=True)
st.markdown("อัปโหลดไฟล์ต้องสงสัยเพื่อวิเคราะห์พฤติกรรมด้วย AI ภายในสภาพแวดล้อมจำลอง (Sandbox) ที่ปลอดภัย")

uploaded_file = st.file_uploader("📂 ลากไฟล์มาวาง หรือคลิกเพื่ออัปโหลดไฟล์ที่ต้องการตรวจสอบ", help="รองรับไฟล์ทุกประเภท เช่น .exe, .sh, .pdf, .bat")

if uploaded_file:
    t_start_perf = time.perf_counter()
    t_start_ms = int(time.time() * 1000)
    
    file_bytes = uploaded_file.getvalue()
    file_size_str = get_file_size_format(len(file_bytes))
    
    file_hash, os_type_detected, target_sandbox, magic_hex, spoofing_warning, target_env, os_reason = analyze_file_static(file_bytes, uploaded_file.name)
    
    t_static_done_perf = time.perf_counter()
    t_static_done_ms = int(time.time() * 1000)
    
    frontend_prep_ms = (t_static_done_perf - t_start_perf) * 1000
    
    warning_html = f"<div style='color: #cf222e; margin-top: 15px; padding: 12px; border: 1px solid #ff8182; border-radius: 4px; background: #ffebe9; font-size: 15px;'><strong>{spoofing_warning}</strong></div>" if spoofing_warning else ""

    st.markdown(f"""
    <div class='pre-analysis-box'>
        <h4>🔍 การตรวจสอบโครงสร้างไฟล์เบื้องต้น (ก่อนนำไปรันจริง)</h4>
        <strong>ชื่อไฟล์</strong> {uploaded_file.name} (ขนาด {file_size_str})<br>
        <strong>รหัสแฮช (SHA-256)</strong> <code>{file_hash}</code><br>
        <strong>รหัสข้อมูลส่วนหัว (Magic Bytes)</strong> <code>{magic_hex}</code><br>
        <strong>ประเภทระบบปฏิบัติการเป้าหมาย</strong> <span style="color:#0969da; font-weight:bold;">{os_type_detected}</span><br>
        <strong>เหตุผลการประเมิน</strong> {os_reason}<br><br>
        <strong style='color:#1a7f37;'>🎯 เส้นทางการวิเคราะห์ {target_sandbox}</strong>
        {warning_html}
    </div>
    """, unsafe_allow_html=True)
    
    session_done_key = f"done_{file_hash}"
    session_data_key = f"data_{file_hash}"
    session_error_key = f"error_{file_hash}"
    session_elapsed_key = f"elapsed_{file_hash}"
    session_timeline_key = f"timeline_{file_hash}"

    if not st.session_state.get(session_done_key, False):
        start_time_stamp = datetime.now().strftime('%H:%M:%S')
        live_tracker = st.empty()
        live_tracker.markdown(f"""
        <div class='live-sandbox-box'>
            📡 <strong><span class='blink-text'>กำลังรันไฟล์ในระบบจำลอง</span></strong> [{start_time_stamp}] &nbsp; ส่งข้อมูลไปยัง <strong style="color: #0969da;">{target_sandbox}</strong>...
        </div>
        """, unsafe_allow_html=True)

        with st.status(f"🔬 ระบบกำลังดำเนินการวิเคราะห์...", expanded=True) as status_box:
            st.write(f"📡 กำลังส่งข้อมูลไปยังระบบหลังบ้าน (n8n)...")
            progress_bar_container = st.progress(0)
            status_text_container = st.empty()
            start_time = time.time()
            api_result = {} 

            def call_api():
                try:
                    files = {'file': (uploaded_file.name, file_bytes, uploaded_file.type)}
                    target_url = f"{API_URL}?filename={uploaded_file.name}&target_os={target_env}&hash={file_hash}"
                    
                    req_start = int(time.time() * 1000)
                    res = requests.post(target_url, files=files, timeout=600) 
                    req_end = int(time.time() * 1000)
                    
                    api_result['response'] = res
                    api_result['req_start'] = req_start
                    api_result['req_end'] = req_end
                except requests.exceptions.Timeout:
                    api_result['error'] = "หมดเวลาการเชื่อมต่อ (เกิน 10 นาที) เครื่องจำลองอาจจะค้าง หรือเปิดไม่สำเร็จ"
                except Exception as e:
                    api_result['error'] = str(e)

            api_thread = threading.Thread(target=call_api)
            api_thread.start()

            progress = 0.0
            while api_thread.is_alive():
                if progress < 20: progress += 1.0     
                elif progress < 50: progress += 0.5   
                elif progress < 80: progress += 0.1   
                elif progress < 98: progress += 0.02  
                progress_bar_container.progress(int(progress))
                
                if progress < 20: msg = "กำลังสตาร์ทเครื่องจำลองบน Azure Cloud (รอประมาณ 1 นาที)..."
                elif progress < 50: msg = "ส่งไฟล์เข้าสู่เครื่องจำลองและสั่งรัน..."
                elif progress < 80: msg = "บันทึกพฤติกรรมไฟล์ และตรวจสอบการเชื่อมต่อเครือข่ายที่ผิดปกติ..."
                elif progress < 98: msg = "รวบรวม Log ส่งให้ AI วิเคราะห์ (ขั้นตอนนี้อาจใช้เวลาหลายนาที)..."
                else: msg = "กำลังสร้างรายงานสรุปผลภาษาไทย..."
                
                status_text_container.caption(f"**ความคืบหน้า {int(progress)}%** — {msg}")
                time.sleep(1) 

            progress_bar_container.progress(100)
            status_text_container.empty()
            
            t_final_render_ms = int(time.time() * 1000)
            
            st.session_state[session_timeline_key] = {
                "1_UI_File_Uploaded_MS": t_start_ms,
                "2_UI_Static_Analysis_Done_MS": t_static_done_ms,
                "3_API_Request_Sent_MS": api_result.get('req_start', t_static_done_ms),
                "4_API_Response_Received_MS": api_result.get('req_end', t_final_render_ms),
                "5_UI_Render_Complete_MS": t_final_render_ms,
                "Metrics": {
                    "Frontend_PreProcessing_Latency_MS": frontend_prep_ms, 
                    "Backend_API_Roundtrip_Latency_MS": api_result.get('req_end', t_final_render_ms) - api_result.get('req_start', t_static_done_ms)
                }
            }
            
            st.session_state[session_elapsed_key] = time.time() - start_time

            if 'error' in api_result:
                st.session_state[session_error_key] = api_result['error']
            elif 'response' in api_result:
                res = api_result['response']
                if res.status_code == 200:
                    try:
                        raw_data = res.json()
                        while isinstance(raw_data, list) and len(raw_data) > 0: raw_data = raw_data[0]
                        st.session_state[session_data_key] = raw_data
                    except ValueError:
                        st.session_state[session_error_key] = f"ระบบหลังบ้านส่งข้อมูลผิดพลาด\nรายละเอียด {res.text}"
                else:
                    st.session_state[session_error_key] = f"ข้อผิดพลาดจาก API {res.status_code}"
            
            st.session_state[session_done_key] = True
            live_tracker.empty()
            status_box.update(label="✅ การวิเคราะห์เสร็จสมบูรณ์ ดึงข้อมูลสำเร็จ", state="complete", expanded=False)

    # ==========================================
    # 📊 แสดงผลลัพธ์
    # ==========================================
    if st.session_state.get(session_done_key, False):
        if session_error_key in st.session_state:
            st.error(f"🛑 เกิดข้อผิดพลาดร้ายแรง {st.session_state[session_error_key]}")
        elif session_data_key in st.session_state:
            data = st.session_state[session_data_key]
            elapsed = st.session_state.get(session_elapsed_key, 0)
            ui_timeline = st.session_state.get(session_timeline_key, {})
            
            verdict = str(data.get("Status", "UNKNOWN")).upper()
            c2_flag = str(data.get("c2_detected", "No")).upper()
            summary_text = data.get("Analysis_Summary", "ไม่มีข้อมูลสรุปพฤติกรรม")
            full_report_str = data.get("Full_Report", "{}")
            
            if "APT29" in verdict or "MALWARE" in verdict:
                score, thai_verdict, v_class = 10, "เป็นมัลแวร์ร้ายแรง (อันตรายระดับสูง)", "badge-malicious"
            elif "BENIGN" in verdict:
                score, thai_verdict, v_class = 1, "ไม่เป็นมัลแวร์ (ปลอดภัย)", "badge-safe"
            else:
                score, thai_verdict, v_class = 5, "ไฟล์น่าสงสัย (ควรระวัง)", "badge-suspicious"

            st.markdown(f"""
            <div class='completed-sandbox-box'>
                ✅ <strong>วิเคราะห์สำเร็จ</strong> ประมวลผลเสร็จสิ้นเมื่อเวลา {datetime.now().strftime('%H:%M:%S')} (ใช้เวลารวม {elapsed:.1f} วินาที)
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 สรุปผลการวิเคราะห์", 
                "📄 รายงานพฤติกรรมเชิงลึกโดย AI", 
                "💻 ข้อมูลดิบจากระบบหลังบ้าน", 
                "⏱️ ค่าสำหรับการทดลองและเวลาประมวลผล"
            ])
            
            with tab1:
                res_col1, res_col2 = st.columns([1, 2])
                with res_col1:
                    st.plotly_chart(create_gauge_chart(score), use_container_width=True)
                    st.markdown(f"<div style='text-align:center; margin-bottom: 20px;'><span class='{v_class}'>{thai_verdict}</span></div>", unsafe_allow_html=True)
                    
                    st.markdown("""
                    <div class='criteria-box'>
                        <strong>ℹ️ เกณฑ์การให้คะแนนความเสี่ยง (1-10)</strong><br>
                        <span style="color:#1a7f37; font-weight:bold;">คะแนน 1-3 (ปลอดภัย)</span> ไฟล์ปกติ ไม่มีพฤติกรรมมุ่งร้าย<br>
                        <span style="color:#9a6700; font-weight:bold;">คะแนน 4-7 (น่าสงสัย)</span> พบพฤติกรรมแปลกๆ แต่ยังไม่ชี้ชัดว่าเป็นไวรัส<br>
                        <span style="color:#cf222e; font-weight:bold;">คะแนน 8-10 (อันตราย)</span> ตรวจพบพฤติกรรมโจมตี ดึงข้อมูล หรือติดต่อแฮกเกอร์
                    </div>
                    """, unsafe_allow_html=True)
                    
                    json_str = json.dumps(data, indent=4)
                    st.download_button(label="📥 ดาวน์โหลดรายงานฉบับเต็ม (JSON)", data=json_str, file_name=f"REPORT_{file_hash[:8]}.json", mime="application/json", use_container_width=True)

                with res_col2:
                    st.markdown("### 🧠 สรุปพฤติกรรมของไฟล์โดยปัญญาประดิษฐ์")
                    st.markdown(f"<div class='report-card'>{summary_text}</div>", unsafe_allow_html=True)
                    
                    c2_status = "🚨 <span style='color:#cf222e; font-weight:bold;'>ตรวจพบการเชื่อมต่อไปยังเซิร์ฟเวอร์อันตราย (C2)</span>" if "YES" in c2_flag else "✅ ไม่พบการแอบส่งข้อมูลออกภายนอก"
                    st.markdown(f"""
                    <div class='metric-box'>
                        🌐 <strong>การตรวจสอบระบบเครือข่ายและการขโมยข้อมูล</strong><br><br>{c2_status}
                    </div>
                    """, unsafe_allow_html=True)

            with tab2:
                st.markdown("### 📑 รายงานพฤติกรรมเชิงลึกระดับเทคนิค")
                try:
                    parsed_report = json.loads(full_report_str)
                    for key, val in parsed_report.items():
                        st.markdown(f"**หัวข้อการวิเคราะห์ ({key})**")
                        st.markdown(f"<div class='report-card'>{val}</div>", unsafe_allow_html=True)
                except:
                    st.markdown(f"<div class='report-card'>{full_report_str}</div>", unsafe_allow_html=True)
            
            with tab3:
                st.markdown("### 💻 ข้อมูลดิบที่ได้รับจาก n8n (JSON Format)")
                st.json(data)
                
            with tab4:
                st.markdown("### ⏱️ ข้อมูลเวลาสำหรับการเขียนรายงานการทดลองวิจัย")
                
                backend_total_ms = data.get("Total_Duration_MS", 0)
                vm_duration_ms = data.get("VM_Duration_MS", 0)
                activity_log_str = data.get("Activity_Log", "[]")
                try:
                    parsed_log = json.loads(activity_log_str)
                except:
                    parsed_log = []

                csv_data = []
                csv_data.append({"เวลาที่บันทึก (มิลลิวินาที)": ui_timeline.get("1_UI_File_Uploaded_MS"), "แหล่งที่มา": "หน้าเว็บ (Streamlit)", "เหตุการณ์": "ผู้ใช้อัปโหลดไฟล์สำเร็จ", "รายละเอียดเพิ่มเติม": uploaded_file.name})
                csv_data.append({"เวลาที่บันทึก (มิลลิวินาที)": ui_timeline.get("2_UI_Static_Analysis_Done_MS"), "แหล่งที่มา": "หน้าเว็บ (Streamlit)", "เหตุการณ์": "วิเคราะห์โครงสร้างไฟล์เสร็จสิ้น", "รายละเอียดเพิ่มเติม": f"ระบบปฏิบัติการที่พบ {os_type_detected}"})
                csv_data.append({"เวลาที่บันทึก (มิลลิวินาที)": ui_timeline.get("3_API_Request_Sent_MS"), "แหล่งที่มา": "หน้าเว็บ (Streamlit)", "เหตุการณ์": "ส่งไฟล์ให้ระบบหลังบ้าน", "รายละเอียดเพิ่มเติม": f"รหัสแฮช {file_hash[:10]}..."})
                
                for log_entry in parsed_log:
                    csv_data.append({
                        "เวลาที่บันทึก (มิลลิวินาที)": log_entry.get("timestamp_ms", ""),
                        "แหล่งที่มา": "ระบบหลังบ้าน (" + log_entry.get("source", "Backend") + ")",
                        "เหตุการณ์": log_entry.get("event", ""),
                        "รายละเอียดเพิ่มเติม": log_entry.get("details", "")
                    })
                
                csv_data.append({"เวลาที่บันทึก (มิลลิวินาที)": ui_timeline.get("4_API_Response_Received_MS"), "แหล่งที่มา": "หน้าเว็บ (Streamlit)", "เหตุการณ์": "ได้รับผลวิเคราะห์กลับมา", "รายละเอียดเพิ่มเติม": f"ผลสรุป {thai_verdict}"})
                csv_data.append({"เวลาที่บันทึก (มิลลิวินาที)": ui_timeline.get("5_UI_Render_Complete_MS"), "แหล่งที่มา": "หน้าเว็บ (Streamlit)", "เหตุการณ์": "แสดงผลขึ้นหน้าจอเสร็จสมบูรณ์", "รายละเอียดเพิ่มเติม": ""})

                df = pd.DataFrame(csv_data)
                df = df.dropna(subset=['เวลาที่บันทึก (มิลลิวินาที)']) 
                df['เวลาที่บันทึก (มิลลิวินาที)'] = pd.to_numeric(df['เวลาที่บันทึก (มิลลิวินาที)'])
                df = df.sort_values(by="เวลาที่บันทึก (มิลลิวินาที)").reset_index(drop=True)
                df['ระยะห่างจากขั้นตอนก่อนหน้า (มิลลิวินาที)'] = df['เวลาที่บันทึก (มิลลิวินาที)'].diff().fillna(0).astype(int)

                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_string = csv_buffer.getvalue()

                st.download_button(
                    label="📥 ดาวน์โหลดไฟล์ตารางเวลา (CSV)",
                    data=csv_string,
                    file_name=f"TIMELINE_METRICS_{file_hash[:8]}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col_front, col_back = st.columns(2)
                
                # --- อัปเดตส่วนแสดงผลเวลาให้เป็นกล่อง HTML ที่เห็นชัดเจน ---
                with col_front:
                    st.markdown("#### 🖥️ เวลาที่ใช้ส่วนแสดงผล (Frontend)")
                    frontend_prep_display = ui_timeline.get('Metrics', {}).get('Frontend_PreProcessing_Latency_MS', 0)
                    roundtrip_display = ui_timeline.get('Metrics', {}).get('Backend_API_Roundtrip_Latency_MS', 0)
                    
                    st.markdown(f"""
                    <div class='time-box-blue'>
                        ⏱️ เวลาเตรียมไฟล์ก่อนส่ง: <span style='color:#0969da;'>{frontend_prep_display:.2f} มิลลิวินาที</span>
                    </div>
                    <div class='time-box-blue'>
                        ⏱️ เวลารวมตั้งแต่ส่งจนได้รับผล: <span style='color:#0969da;'>{roundtrip_display} มิลลิวินาที</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_back:
                    st.markdown("#### ⚙️ เวลาที่ใช้ส่วนหลังบ้าน (Backend & VM)")
                    
                    st.markdown(f"""
                    <div class='time-box-orange'>
                        ⏱️ เวลารวมของระบบ n8n: <span style='color:#9a6700;'>{backend_total_ms} มิลลิวินาที</span>
                    </div>
                    <div class='time-box-orange'>
                        ⏱️ เวลาในส่วนของกล่องทราย (Sandbox): <span style='color:#9a6700;'>{vm_duration_ms} มิลลิวินาที</span>
                    </div>
                    """, unsafe_allow_html=True)