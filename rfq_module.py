

import streamlit as st
import pandas as pd
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import time



# ==========================================
# 1. CONFIGURATION
# ==========================================
SENDER_EMAIL = "sim.mailalert@gmail.com"
SENDER_PASS = "fsuuilzghlocfuvf"

def send_auto_email(rfq_data):
    # เปลี่ยนจากการใช้ st.secrets มาเป็นการใช้ตัวแปร Global ที่ตั้งไว้ด้านบน
    sender_email = SENDER_EMAIL
    sender_pass = SENDER_PASS

    # 1. รายชื่อผู้รับ (Logic เดิมของคุณ) ######################################
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

###################### Test Mail ##############################################################

    # admin_team = ["utai.c@siamintermold.com"]
    
    # staff_team = []
    # bu = rfq_data.get('rfq_bu')
    # if bu == "Mass":
    #     staff_team = ["utai.c@siamintermold.com"]
    # elif bu == "Mold":
    #     staff_team = ["utai.c@siamintermold.com"]

####################################################################################
    
    receiver_emails = list(set([email.strip() for email in (admin_team + staff_team) if email]))

    if not receiver_emails:
        st.error("❌ ไม่พบรายชื่อผู้รับอีเมล")
        return False

    # 2. สร้างเนื้อหา (ใช้ MIMEMultipart)
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

    # 3. กระบวนการส่ง (ใช้ SMTP_SSL พอร์ต 465 เพื่อความเสถียร)
    try:
        # ใช้ 'with' เพื่อให้ Python ปิดการเชื่อมต่ออัตโนมัติเมื่อส่งเสร็จ
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

# --- 2. FULL DASHBOARD FUNCTION (คงเดิมตามที่คุณรุ่งส่งมา) ---
def show_rfq_dashboard(HEADERS, URL_RFQ):
    st.subheader("📋 RFQ Pipeline Dashboard")
    res = requests.get(f"{URL_RFQ}?order=timestamp.desc", headers=HEADERS)
    
    if res.status_code != 200:
        st.error("Connection Error")
        return
    
    data = res.json()
    if not data:
        st.info("No data found.")
        return
    
    df = pd.DataFrame(data)
    today = date.today()

    # --- 1. เตรียมข้อมูล & คำนวณค่า (Logic ใหม่ตามที่คุณต้องการ) ---
    df['price_clean'] = pd.to_numeric(df['offered_price'].astype(str).str.replace(',', '').str.replace('THB', ''), errors='coerce').fillna(0)
    df['volume_clean'] = pd.to_numeric(df['volumes_yearly'], errors='coerce').fillna(0)
    df['award_rate_clean'] = pd.to_numeric(df['award_rate'], errors='coerce').fillna(0)
    
    # มูลค่าเต็มของแต่ละงาน
    df['line_value'] = df['price_clean'] * df['volume_clean']
    
    # คำนวณมูลค่าที่คาดหวัง (Potential Value) 
    # Logic: ถ้าโอกาสได้งาน >= 80% ให้นับมูลค่าเต็ม (100%) ถ้าต่ำกว่านั้นไม่นับ
    df['potential_value'] = df.apply(lambda x: x['line_value'] if x['award_rate_clean'] >= 80 else 0, axis=1)
    
    df['Calculated Value'] = df['line_value'].apply(lambda x: f"{x:,.0f}")
    
    # --- 2. ระบบ Filter สำหรับ Sales Performance (วางตรงนี้!) ---
    # st.write("### 🔍 Sales Performance Analysis")
    available_rates = sorted(df['award_rate_clean'].unique().tolist())
    
    c_filt1, c_filt2 = st.columns([2, 1])
    with c_filt1:
        selected_rates = st.multiselect(
            "Filter by Achieve Rate (%)",
            options=available_rates,
            default=available_rates 
        )
    with c_filt2:
        high_conf_quick = st.toggle("Quick View: High Confidence (>=80%)")

    # --- 3. Logic การกรองข้อมูล ---
    filtered_df = df.copy()
    if selected_rates:
        filtered_df = filtered_df[filtered_df['award_rate_clean'].isin(selected_rates)]
    if high_conf_quick:
        filtered_df = filtered_df[filtered_df['award_rate_clean'] >= 80]
##########################
# --- แทรกส่วนนี้: คำนวณ Project Value แยกตาม BU (ยอดเต็มตาม Filter) ---
    # ใช้ 'line_value' (ยอดเงินเต็ม) คำนวณจาก filtered_df ที่ผ่านตัวกรองหลักมาแล้ว
    bu_mold_total = filtered_df[filtered_df['rfq_bu'] == 'Mold']['line_value'].sum()
    bu_mass_total = filtered_df[filtered_df['rfq_bu'] == 'Mass']['line_value'].sum()

    # st.write(" 🏢 Project Value by Business Unit (Selected Filter)")
    # cb1, cb2 = st.columns(2)
    # cb1.metric("Total Mold BU", f"{bu_mold_total:,.0f} THB")
    # cb2.metric("Total Mass BU", f"{bu_mass_total:,.0f} THB")
    # st.divider()
    # -----------------------------------------------------------------
 ####################
    # --- 4. แสดง Metrics (ตัวเลขจะเปลี่ยนตามที่ Filter) ---
# --- ส่วนการจัดหน้าใหม่ ---
    # st.write("### 📊 RFQ Financial Summary")
    
    # สร้าง Container เพื่อตีกรอบให้ดูเป็นสัดส่วน (ถ้า Streamlit version ใหม่จะเห็นขอบชัด)
    with st.container(border=True):
        # แถวที่ 1: แยกตาม Business Unit
        col_bu1, col_bu2 = st.columns(2)
        with col_bu1:
            st.metric("🏗️ Total Mold BU", f"{bu_mold_total:,.0f} THB")
        with col_bu2:
            st.metric("🏭 Total Mass BU", f"{bu_mass_total:,.0f} THB")
        
        st.divider() # เส้นคั่นกลางระหว่าง BU กับ สรุปรวม

        # แถวที่ 2: สรุปภาพรวม (3 Metrics หลัก)
        m1, m2, m3 = st.columns(3)
        m1.metric("📝 Selected RFQs", f"{len(filtered_df)} Jobs")
        m2.metric("💰 Project Value (Total)", f"{filtered_df['line_value'].sum():,.0f} THB")
        
        # ใส่สีเขียวให้ Expected Revenue เพื่อเน้นว่าเป็นยอดเป้าหมาย
        expected_val = filtered_df['potential_value'].sum()
        m3.metric("🎯 Expected Revenue", f"{expected_val:,.0f} THB", delta="High Confidence" if expected_val > 0 else None)

    st.write("") # เพิ่มช่องว่างด้านล่างเล็กน้อยก่อนขึ้นตาราง
    
    # --- 5. ตาราง Master Tracking (จะโชว์เฉพาะที่กรองไว้) ---
    st.write("### 📑 Master RFQ Tracking")
    display_cols = ["rfq_id", "customer", "part_no", "status", "award_rate", "Calculated Value", "remark"]
    existing_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[existing_cols],
        column_config={
            "rfq_id": st.column_config.TextColumn("RFQ ID", width="small"),
            "award_rate": st.column_config.ProgressColumn("Achieve %", format="%d%%", min_value=0, max_value=100),
            "Calculated Value": st.column_config.TextColumn("Total Value (THB)"),
        },
        hide_index=True,
        use_container_width=True
    )

    # --- ส่วนที่เหลือ (Full Database / Overdue Alerts) วางต่อจากตรงนี้ ---
    
    # ... (ส่วนของ Full Database และ Overdue Alerts ด้านล่างคงเดิม) ...

    st.divider()
    #########################
    # --- 5. Full Database View (Hide/Show Logic) ---
    st.subheader("🗂️ Data Management")

    # สร้าง Toggle สำหรับ เปิด-ปิด การแสดงผล
    show_full_db = st.toggle("Show Full RFQ Database", value=False)

    if show_full_db:
        st.write("### 📑 Master RFQ Database (All Records)")
        
        # เพิ่มความสามารถในการ Search/Filter เบื้องต้น
        search_query = st.text_input("🔍 ค้นหาใน Database (ID, Customer, Part No.,)", "")
        
        display_df = df.copy()
        if search_query:
            # ค้นหาคำที่พิมพ์ในทุกคอลัมน์
            mask = display_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            display_df = display_df[mask]

        # แสดง DataFrame แบบเต็ม
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # เพิ่มปุ่ม Download ให้ในกรณีที่เปิดดู
        csv = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download current view as CSV",
            data=csv,
            file_name=f"rfq_full_export_{date.today()}.csv",
            mime="text/csv",
        )

        ###########################
    
    st.write("### 🚨 Overdue Alerts")
    overdue_list = []
    for rfq in data:
        try:
            target_dt = datetime.strptime(rfq['quotation_date_target'], "%Y-%m-%d").date()
            if rfq.get('status') == "Pending" and target_dt < today:
                overdue_list.append(rfq)
        except: continue
    if not overdue_list:
        st.success("✅ No overdue items requiring mail alerts.")
    else:
        for item in overdue_list:
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.write(f"**{item['rfq_id']}** - {item['customer']}")
                    st.caption(f"Deadline was: {item['quotation_date_target']} | BU: {item.get('rfq_bu', 'N/A')}")
                with c2:
                    if item.get('alert_status') == "Sent":
                        st.info("📩 Sent")
                    else:
                        if st.button("📧 Alert", key=f"mail_{item['rfq_id']}"):
                            with st.spinner("Sending..."):
                                success, msg = send_specific_overdue_alert(item)
                                if success:
                                    requests.patch(f"{URL_RFQ}?rfq_id=eq.{item['rfq_id']}", headers=HEADERS, json={"alert_status": "Sent"})
                                    st.success("Sent!")
                                    time.sleep(1); st.rerun()
                                else:
                                    st.error("Failed")
            st.divider()

# --- 3. หน้าลงทะเบียน RFQ (FIXED: เพิ่มการส่งเมลหลังบันทึก) ---
def show_rfq_create(HEADERS, URL_RFQ):
    st.subheader("➕ Register New RFQ")
    with st.form("f_rfq_create", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            r_id = st.text_input("RFQ ID *")
            r_part = st.text_input("Part No. *")
            r_bu = st.selectbox("RFQ BU", ["Mold", "Mass"])
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
                    
                    # --- จุดที่แก้ไข: เพิ่มการส่งเมลหลังจาก Save สำเร็จ ---
                    with st.spinner("📧 กำลังส่งเมลแจ้งเตือนทีมงาน..."):
                        if send_auto_email(payload):
                            st.success("ส่งเมลสำเร็จ!")
                        else:
                            st.warning("บันทึกสำเร็จ แต่เมลไม่ส่ง (เช็ค Error ด้านบน)")
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Error: {res.text}")
            else:
                st.warning("⚠️ Fill required fields (*)")

# --- 4. หน้าอัปเดตงาน --- (Corrected to reset alerts)
def show_rfq_update(HEADERS, URL_RFQ):
    st.subheader("📤 Quotation Submission & Sales Update")
    
    # 1. ดึงข้อมูลจากฐานข้อมูลมาทั้งหมด
    res = requests.get(f"{URL_RFQ}?order=timestamp.desc", headers=HEADERS)
    
    if res.status_code == 200 and res.json():
        full_df = pd.DataFrame(res.json())
        
        # --- 2. ระบบค้นหา (Search System) ---
        # ให้ Sales พิมพ์ค้นหาได้เลย ระบบจะกรอง Selectbox ด้านล่างให้เอง
        search_txt = st.text_input("🔍 ค้นหา RFQ ID หรือ ชื่อลูกค้า", placeholder="พิมพ์เพื่อค้นหา...", key="main_search_input")
        
        # กรองข้อมูลใน Python
        if search_txt:
            mask = (full_df['rfq_id'].astype(str).str.contains(search_txt, case=False) | 
                    full_df['customer'].astype(str).str.contains(search_txt, case=False))
            df = full_df[mask]
        else:
            df = full_df

        if not df.empty:
            # 3. ส่วนการเลือกรายการ (เหลือแค่ตารางเดียว/อันเดียว)
            df['display_name'] = df['rfq_id'].astype(str) + " | " + df['customer'].astype(str)
            selected_item = st.selectbox(
                f"พบข้อมูล {len(df)} รายการ (เลือกรายการด้านล่างเพื่อจัดการ):", 
                df['display_name'].tolist(),
                key="unified_selectbox"
            )
            
            sel_rfq = selected_item.split(" | ")[0].strip()
            row = df[df['rfq_id'] == sel_rfq].iloc[0]
            
            # แสดงสถานะปัจจุบันให้ Sales มั่นใจ
            current_status = row.get('status', 'Pending')
            st.info(f"📌 กำลังจัดการ: **{sel_rfq}** | สถานะ: **{current_status}**")

            # --- 4. ฟอร์มจัดการข้อมูล (Integrated Form) ---
            # ใช้ Unique Key โดยการเอา ID มาต่อท้าย ป้องกัน Error Form ซ้ำ
            with st.form(key=f"form_sync_{sel_rfq}", clear_on_submit=False):
                c1, c2 = st.columns(2)
                with c1:
                    q_link = st.text_input("🔗 Quotation Link", value=row.get('quotation_link', '') or "")
                    q_price = st.text_input("💰 Offered Price", value=row.get('offered_price', '') or "")
                with c2:
                    # ป้องกัน Error award_rate ไม่เป็นตัวเลข
                    try:
                        curr_rate = int(row.get('award_rate', 0)) if row.get('award_rate') else 0
                    except:
                        curr_rate = 0
                    q_score = st.select_slider("🎯 Achieve Rate (%)", options=[0, 30, 50, 80, 100], value=curr_rate)
                    q_rev = st.text_input("🔢 Revision No.", value=row.get('rfq_rev', '0'))
                
                q_cond = st.text_area("📦 Sales Conditions", value=row.get('offered_condition', '') or "")
                q_plan = st.text_area("📅 Follow-up Plan", value=row.get('follow_up_plan', '') or "")
                q_rem = st.text_area("💬 Sales Note / Remark", value=row.get('remark', '') or "")
                
                # ปุ่มเดียวที่ฉลาดพอจะเปลี่ยนชื่อตามสถานะ
                btn_label = "🚀 Submit Quotation" if current_status == 'Pending' else "🔄 Update Revision"
                submitted = st.form_submit_button(btn_label)
                
                if submitted:
                    # เตรียมข้อมูลให้ตรงกับ DB (บังคับ int4 สำหรับ award_rate)
                    up_payload = {
                        "quotation_link": q_link,
                        "offered_price": q_price,
                        "rfq_rev": q_rev,
                        "offered_condition": q_cond,
                        "follow_up_plan": q_plan,
                        "remark": q_rem,
                        "award_rate": int(q_score),
                        "status": "Submitted" # เปลี่ยนสถานะอัตโนมัติ
                    }
                    
                    # ส่งไปที่ Supabase โดยใช้ rfq_id เป็นตัวอ้างอิง
                    patch_url = f"{URL_RFQ}?rfq_id=eq.{sel_rfq}"
                    res_patch = requests.patch(patch_url, headers=HEADERS, json=up_payload)
                    
                    if res_patch.status_code in [200, 204]:
                        st.success(f"✅ ดำเนินการ RFQ {sel_rfq} สำเร็จ!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ เกิดข้อผิดพลาด: {res_patch.text}")
        else:
            st.warning("⚠️ ไม่พบข้อมูลที่ตรงกับคำค้นหา")
    else:
        st.info("✨ ไม่มีข้อมูล RFQ ในระบบ")
    ######################################

def show_rfq_management_summary(HEADERS, URL_RFQ):
    st.subheader("📊 Management RFQ Summary")
    
    res = requests.get(f"{URL_RFQ}?order=timestamp.desc", headers=HEADERS)
    if res.status_code != 200:
        st.error("Could not fetch data for summary.")
        return

    df = pd.DataFrame(res.json())
    if df.empty:
        st.info("No data available for analysis.")
        return

    # --- Data Cleaning ---
    # Convert price string to number (removes commas and 'THB')
    def clean_price(val):
        if not val: return 0
        try:
            return float(str(val).replace(',', '').replace('THB', '').strip())
        except:
            return 0

    df['price_numeric'] = df['offered_price'].apply(clean_price)
    
    # --- Top Level Metrics ---
    total_quoted = df['price_numeric'].sum()
    high_conf_df = df[df['award_rate'] >= 80]
    high_conf_value = high_conf_df['price_numeric'].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Quoted Value", f"{total_quoted:,.2f} THB")
    c2.metric("High Confidence (80%+)", f"{high_conf_value:,.2f} THB")
    c3.metric("Win Rate (%)", f"{(len(df[df['status']=='Submitted']) / len(df) * 100):.1f}%")

    st.divider()

    # --- Funnel Chart ---
    st.write("### 🎯 Sales Pipeline Funnel")
    # Grouping by award rate to see the funnel
    funnel_data = df.groupby('award_rate').agg({
        'rfq_id': 'count',
        'price_numeric': 'sum'
    }).reset_index().sort_values('award_rate', ascending=False)
    
    funnel_data.columns = ['Confidence (%)', 'Count', 'Total Value']
    st.table(funnel_data) # You can also use st.bar_chart(funnel_data.set_index('Confidence (%)')['Total Value'])

    # --- BU Performance ---
    st.write("### 🏗️ Business Unit Breakdown")
    bu_data = df.groupby('rfq_bu')['price_numeric'].sum()
    st.bar_chart(bu_data)