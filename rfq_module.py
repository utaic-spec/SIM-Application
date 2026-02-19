import streamlit as st
import pandas as pd
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import time

# ==============================================================================
# SECTION 1: CONFIGURATION & GLOBAL VARIABLES
# ==============================================================================
SENDER_EMAIL = "sim.mailalert@gmail.com"
SENDER_PASS = "fsuuilzghlocfuvf"

# ==============================================================================
# SECTION 2: EMAIL NOTIFICATION SYSTEM
# ==============================================================================
def send_auto_email(rfq_data):
    """ส่งเมลแจ้งเตือนอัตโนมัติเมื่อมีการลงทะเบียน RFQ ใหม่"""
    sender_email = SENDER_EMAIL
    sender_pass = SENDER_PASS

    # --- 2.1 กำหนดรายชื่อผู้รับตาม Business Unit ---
    admin_team = [
        "wattanapon.s@siamintermold.com", "paitoon.b@siamintermold.com",
        "utai.c@siamintermold.com", "rewat.m@siamintermold.com",
        "admincenter@siamintermold.com"
    ]
    
    staff_team = []
    bu = rfq_data.get('rfq_bu')
    if bu == "Mass":
        staff_team = ["natthapol.p@siamintermold.com"]
    elif bu == "Mold":
        staff_team = ["thawat.t@siamintermold.com", "waiphop.b@siamintermold.com"]
    elif bu == "Mass&Mold":
        staff_team = ["natthapol.p@siamintermold.com", "thawat.t@siamintermold.com"]

    receiver_emails = list(set([email.strip() for email in (admin_team + staff_team) if email]))

    if not receiver_emails:
        st.error("❌ ไม่พบรายชื่อผู้รับอีเมล")
        return False

    # --- 2.2 จัดทำเนื้อหาอีเมล (Email Body) ---
    message = MIMEMultipart()
    message["From"] = f"SIM Master Alert <{sender_email}>"
    message["To"] = ", ".join(receiver_emails)
    
    prefix = "🚨 [URGENT OVERDUE]" if rfq_data.get('is_overdue') else "📢 [New RFQ Alert]"
    message["Subject"] = f"{prefix} ID: {rfq_data.get('rfq_id')} | Part: {rfq_data.get('part_no')}"

    body = f"""
Dear Core Team,

A new RFQ has been registered in the system.
Please review the details and provide your feedback or comments accordingly.

- RFQ ID: {rfq_data.get('rfq_id')}
- Part No: {rfq_data.get('part_no')}
- Customer: {rfq_data.get('customer')}
- Business Unit: {rfq_data.get('rfq_bu')}
- Target Date: {rfq_data.get('quotation_date_target')}
- Data Link: {rfq_data.get('file_link', 'N/A')}
- Sales Remark: {rfq_data.get('remark')}

This is an automated email from SIM Master 2026.
    """
    message.attach(MIMEText(body, "plain"))

    # --- 2.3 กระบวนการส่งผ่าน SMTP ---
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(sender_email, sender_pass)
            server.send_message(message)
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Gmail Login Fail: รหัสผ่าน App Password ผิดหรือหมดอายุ")
        return False
    except Exception as e:
        st.error(f"❌ ระบบส่งเมลขัดข้อง: {str(e)}")
        return False

# ==============================================================================
# SECTION 3: DASHBOARD & DATA VISUALIZATION (WITH ADVANCED FILTERS)
# ==============================================================================
def show_rfq_dashboard(HEADERS, URL_RFQ):
    """หน้าจอหลักสำหรับดูภาพรวมและสถานะของ RFQ พร้อมระบบกรองข้อมูลละเอียด"""
    st.subheader("📋 RFQ Pipeline Dashboard")
    
    # 3.1 ดึงข้อมูลจากฐานข้อมูล
    res = requests.get(f"{URL_RFQ}?order=timestamp.desc", headers=HEADERS)
    if res.status_code != 200:
        st.error("Connection Error: ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
        return
    
    data = res.json()
    if not data:
        st.info("No data found in database.")
        return
    
    df = pd.DataFrame(data)
    today = date.today()
    
    # 3.2 การคำนวณ Logic พื้นฐาน (Mass, Mold, Mass&Mold)
    df['price_clean'] = pd.to_numeric(df['offered_price'].astype(str).str.replace(',', '').str.replace('THB', ''), errors='coerce').fillna(0)
    df['mold_price_clean'] = pd.to_numeric(df.get('mold_price', 0), errors='coerce').fillna(0)
    df['volume_clean'] = pd.to_numeric(df['volumes_yearly'], errors='coerce').fillna(0)
    df['award_rate_clean'] = pd.to_numeric(df['award_rate'], errors='coerce').fillna(0)

    # แยกมูลค่าตามประเภทธุรกิจ
    df['mass_val'] = df.apply(lambda x: x['price_clean'] * x['volume_clean'] if x['rfq_bu'] in ['Mass', 'Mass&Mold'] else 0, axis=1)
    df['mold_val'] = df.apply(lambda x: x['price_clean'] if x['rfq_bu'] == "Mold" else (x['mold_price_clean'] if x['rfq_bu'] == "Mass&Mold" else 0), axis=1)
    df['line_value'] = df['mass_val'] + df['mold_val']
    df['potential_value'] = df.apply(lambda x: x['line_value'] if x['award_rate_clean'] >= 80 else 0, axis=1)
    df['Calculated Value'] = df['line_value'].apply(lambda x: f"{x:,.0f}")

    # --- 3.3 ระบบ Search & Filter UI (จัดกลุ่มให้ใช้ง่าย) ---
    with st.expander("🔍 Filter Options (คลิกเพื่อค้นหาละเอียด)", expanded=True):
        # แถวที่ 1: ค้นหาคำอิสระ และ กรองตามสถานะ
        c_search, c_status = st.columns([2, 1])
        with c_search:
            search_query = st.text_input("🔎 ค้นหา", placeholder="RFQ ID, ชื่อลูกค้า, หรือ Part No...")
        with c_status:
            status_list = ["All"] + sorted(df['status'].unique().tolist())
            selected_status = st.selectbox("📌 สถานะ", options=status_list)

        # แถวที่ 2: กรองตาม Achieve Rate
        available_rates = sorted(df['award_rate_clean'].unique().tolist())
        c_rate, c_toggle = st.columns([2, 1])
        with c_rate:
            selected_rates = st.multiselect("🎯 Achieve Rate (%)", options=available_rates, default=available_rates)
        with c_toggle:
            st.write("") # เว้นระยะ
            high_conf_only = st.toggle("🚀 Show High Confidence Only (>=80%)")

    # --- 3.4 ประมวลผลการกรอง (Filtering Execution) ---
    filtered_df = df.copy()

    # กรองตามคำค้นหา
    if search_query:
        q = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['rfq_id'].astype(str).str.lower().str.contains(q) |
            filtered_df['customer'].astype(str).str.lower().str.contains(q) |
            filtered_df['part_no'].astype(str).str.lower().str.contains(q)
        ]

    # กรองตามสถานะ
    if selected_status != "All":
        filtered_df = filtered_df[filtered_df['status'] == selected_status]

    # กรองตามช่วงคะแนน Achieve Rate
    if selected_rates:
        filtered_df = filtered_df[filtered_df['award_rate_clean'].isin(selected_rates)]

    # กรองเฉพาะงานมั่นใจสูง
    if high_conf_only:
        filtered_df = filtered_df[filtered_df['award_rate_clean'] >= 80]

    # --- 3.5 แสดงผล Metrics (ตัวเลขจะเปลี่ยนตาม Filter ทันที) ---
    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("🏗️ Total Mold BU", f"{filtered_df['mold_val'].sum():,.0f} THB")
        m2.metric("🏭 Total Mass BU", f"{filtered_df['mass_val'].sum():,.0f} THB")
        m3.metric("💰 Total Project Value", f"{filtered_df['line_value'].sum():,.0f} THB")
        
        # แสดงยอด Expected Revenue เพิ่มเติมเพื่อความชัดเจน
        st.caption(f"💡 Expected Revenue (Confidence >=80%): {filtered_df['potential_value'].sum():,.0f} THB")

    # --- 3.6 ตารางแสดงผล Master Tracking ---
    st.write(f"### 📑 Master RFQ Tracking (พบ {len(filtered_df)} รายการ)")
    display_cols = ["rfq_id", "customer", "part_no", "rfq_bu", "status", "award_rate", "Calculated Value"]
    
    st.dataframe(
        filtered_df[display_cols],
        column_config={
            "rfq_id": st.column_config.TextColumn("RFQ ID", width="small"),
            "award_rate": st.column_config.ProgressColumn("Achieve %", format="%d%%", min_value=0, max_value=100),
            "Calculated Value": st.column_config.TextColumn("Total Value (THB)"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.divider()
    
    # (Section 3.5 เดิม: Data Management และ Overdue Alerts อยู่ต่อท้ายตรงนี้ได้เลย)
# ==============================================================================
# SECTION 4: RFQ REGISTRATION (NEW ENTRY)
# ==============================================================================
def show_rfq_create(HEADERS, URL_RFQ):
    """หน้าสำหรับกรอกข้อมูลเพื่อลงทะเบียน RFQ ใหม่ลงในระบบ"""
    st.subheader("➕ Register New RFQ")
    with st.form("f_rfq_create", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_id = st.text_input("RFQ ID *")
            r_part = st.text_input("Part No. *")
            r_bu = st.selectbox("RFQ BU", ["Mold", "Mass","Mass&Mold"])
            r_cust = st.text_input("Customer Name *")
        with c2:
            r_proc = st.multiselect("Process", ["Die Casting", "FN", "SB", "T5", "Coating", "MC", "New-Mold", "Mold-Part", "Mold-OH", "Mold-Repair"])
            r_mat = st.text_input("Material")
            r_tool = st.multiselect("Tooling", ["New Mold", "Transferred Mold", "New Jigs", "Transferred Jigs"])
        with c3:
            r_vol = st.number_input("Volumes (Yearly)", min_value=0)
            r_target = st.date_input("Quotation Target Date")
            r_sales = st.selectbox("Sales Owner", ["K.Utai", "K.Rewat", "Sales"])
        
        r_link = st.text_input("🔗 Google Drive Folder Link")
        r_rem = st.text_area("Remark / Detail")
        
        if st.form_submit_button("Submit & Save"):
            if r_id and r_cust and r_part:
                payload = {
                    "rfq_id": r_id, "part_no": r_part, "rfq_bu": r_bu, "customer": r_cust,
                    "process": ", ".join(r_proc), "material": r_mat, "tooling_type": ", ".join(r_tool),
                    "volumes_yearly": r_vol, "quotation_date_target": r_target.isoformat(),
                    "sales_owner": r_sales, "file_link": r_link, "remark": r_rem,
                    "status": "Pending", "award_rate": 0
                }
                res = requests.post(URL_RFQ, headers=HEADERS, json=payload)
                if res.status_code in [200, 201]:
                    st.success("✅ บันทึกข้อมูล RFQ เรียบร้อย!")
                    with st.spinner("📧 กำลังส่งเมลแจ้งเตือนทีมงาน..."):
                        if send_auto_email(payload):
                            st.success("ส่งเมลสำเร็จ!")
                        else:
                            st.warning("บันทึกสำเร็จ แต่เมลไม่ส่ง")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Error: {res.text}")
            else:
                st.warning("⚠️ Fill required fields (*)")

# ==============================================================================
# SECTION 5: RFQ UPDATE & QUOTATION SUBMISSION
# ==============================================================================
def show_rfq_update(HEADERS, URL_RFQ):
    """หน้าสำหรับ Sales ในการอัปเดตข้อมูลการส่งใบเสนอราคา (Quotation)"""
    st.subheader("📤 Quotation Submission & Sales Update")
    
    res = requests.get(f"{URL_RFQ}?order=timestamp.desc", headers=HEADERS)
    if res.status_code == 200 and res.json():
        full_df = pd.DataFrame(res.json())
        
        # ค้นหาข้อมูล
        search_txt = st.text_input("🔍 ค้นหา RFQ ID หรือ ชื่อลูกค้า", placeholder="พิมพ์เพื่อค้นหา...", key="main_search_input")
        if search_txt:
            mask = (full_df['rfq_id'].astype(str).str.contains(search_txt, case=False) |
                    full_df['customer'].astype(str).str.contains(search_txt, case=False))
            df = full_df[mask]
        else:
            df = full_df

        if not df.empty:
            df['display_name'] = df['rfq_id'].astype(str) + " | " + df['customer'].astype(str)
            selected_item = st.selectbox(f"พบ {len(df)} รายการ:", df['display_name'].tolist(), key="unified_selectbox")
            
            sel_rfq = selected_item.split(" | ")[0].strip()
            row = df[df['rfq_id'] == sel_rfq].iloc[0]
            current_status = row.get('status', 'Pending')
            st.info(f"📌 กำลังจัดการ: **{sel_rfq}** | สถานะ: **{current_status}**")

            # ฟอร์มการอัปเดตข้อมูล
            with st.form(key=f"unified_rfq_form_{sel_rfq}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    q_link = st.text_input("🔗 Quotation Link", value=row.get('quotation_link', '') or "")
                    q_price = st.text_input("💰 Offered Price (Part)", value=row.get('offered_price', '') or "")
                with c2:
                    curr_mold = row.get('mold_price', 0)
                    q_mold_price = st.number_input("🏗️ Mold Price (THB)", value=float(curr_mold) if curr_mold else 0.0)
                    q_rev = st.text_input("🔢 Revision No.", value=row.get('rfq_rev', '0'))
                with c3:
                    try:
                        curr_rate = int(row.get('award_rate', 0)) if row.get('award_rate') else 0
                    except:
                        curr_rate = 0
                    q_score = st.select_slider("🎯 Achieve Rate (%)", options=[0, 30, 50, 80, 100], value=curr_rate)
                
                q_rem = st.text_area("💬 Sales Note / Remark", value=row.get('remark', '') or "")
                btn_label = "🚀 Submit Quotation" if current_status == 'Pending' else "🔄 Update & Save Data"
                
                if st.form_submit_button(btn_label, use_container_width=True, type="primary"):
                    up_payload = {
                        "quotation_link": q_link, "offered_price": q_price,
                        "mold_price": q_mold_price, "rfq_rev": q_rev,
                        "remark": q_rem, "award_rate": int(q_score), "status": "Submitted" 
                    }
                    patch_url = f"{URL_RFQ}?rfq_id=eq.{sel_rfq}"
                    res_patch = requests.patch(patch_url, headers=HEADERS, json=up_payload)
                    if res_patch.status_code in [200, 204]:
                        st.success(f"✅ ดำเนินการ {sel_rfq} เรียบร้อยแล้ว")
                        time.sleep(1); st.rerun()
                    else:
                        st.error(f"❌ Error: {res_patch.text}")
# ==============================================================================
# SECTION 5: SALES PERFORMANCE REPORT (TAB STRUCTURE)
# ==============================================================================
def show_sales_performance_report():
    st.subheader("📊 Sales Performance Analysis 2025")
    
    # --- 5.1 ส่วนหัว: ตัวเลือกเดือน (แชร์ใช้ร่วมกันทุก Tab) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        with c1:
            start_m = st.selectbox("📅 เริ่มจาก", months, index=0, key="sr_start")
        with c2:
            end_m = st.selectbox("📅 ถึง", months, index=date.today().month-1, key="sr_end")
        with c3:
            st.metric("Report Year", "2025")

    # --- 5.2 สร้าง Tabs ย่อยภายในหน้า Report ---
    t_mass, t_mold, t_onesim = st.tabs(["🏭 MASS BU", "🏗️ Mold BU", "🎯 One-SIM (Overall)"])

    # --- 5.3 เนื้อหาในแต่ละ Tab (นำ Logic เดิมมาเสียบ) ---
    with t_mass:
        st.markdown("### รายงานยอดขายชิ้นส่วน (Mass Sales)")
        # [ใส่ Logic การคำนวณและกราฟของ MASS จาก Code เดิมที่นี่]
        # ตัวอย่าง:
        # render_mass_logic(start_m, end_m) 

    with t_mold:
        st.markdown("### รายงานยอดขายแม่พิมพ์ (Mold Sales)")
        # [ใส่ Logic การคำนวณและกราฟของ Mold จาก Code เดิมที่นี่]

    with t_onesim:
        st.markdown("### สรุปภาพรวมยอดขายบริษัท (Total Sales)")
        # [แสดงกราฟเปรียบเทียบ Target vs Actual ของทั้งบริษัท]
