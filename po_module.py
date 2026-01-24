
import streamlit as st
import pandas as pd
import requests
import time

def show_po_dashboard(HEADERS, URL_PO, role):
    st.subheader("📊 Purchase Order Tracking System")

    # 1. Fetch Data
    res = requests.get(f"{URL_PO}?order=timestamp.desc", headers=HEADERS)
    if res.status_code != 200:
        st.error("ไม่สามารถเชื่อมต่อฐานข้อมูลได้")
        return

    raw_data = res.json()
    if not raw_data:
        st.info("💡 ยังไม่มีข้อมูล PO ในระบบ")
        # # If Sales/Admin, show the create form even if no data exists
        # if role in ["admin", "sales"]:
        #     show_po_create(HEADERS, URL_PO)
        return

    df = pd.DataFrame(raw_data)
    
    # 2. Financial Calculations
    df['po_qty'] = pd.to_numeric(df.get('po_qty', 0), errors='coerce').fillna(0)
    df['unit_price'] = pd.to_numeric(df.get('unit_price', 0), errors='coerce').fillna(0)
    df['total_value'] = df['po_qty'] * df['unit_price']

    # 3. Date Formatting
    for col in ['timestamp', 'customer_eta_date', 'planning_production_date', 'logistic_ship_date']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.date

    # 4. Filter Console
    with st.container(border=True):
        st.markdown("#### 🛠️ Filter Console")
        c1, c2, c3 = st.columns(3)
        with c1:
            on_cust = st.checkbox("กรองโดย: Customer")
            f_cust = st.multiselect("เลือกรายชื่อลูกค้า", options=sorted(df['customer'].unique()) if 'customer' in df.columns else [], disabled=not on_cust)
        with c2:
            on_prod = st.checkbox("กรองโดย: Product Type")
            f_prod = st.multiselect("เลือกประเภทสินค้า", options=sorted(df['product'].unique()) if 'product' in df.columns else [], disabled=not on_prod)
        with c3:
            on_search = st.checkbox("กรองโดย: PO ID / Part No")
            f_search = st.text_input("ระบุรหัส PO หรือ Part No", disabled=not on_search)

    # 5. Filtering Logic
    filtered = df.copy()
    if on_cust and f_cust: filtered = filtered[filtered['customer'].isin(f_cust)]
    if on_prod and f_prod: filtered = filtered[filtered['product'].isin(f_prod)]
    if on_search and f_search: 
        filtered = filtered[filtered['po_id'].astype(str).str.contains(f_search, case=False, na=False) | 
                            filtered['part_no'].astype(str).str.contains(f_search, case=False, na=False)]

    # 6. Financial Summary Metrics
    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("Selected Items", f"{len(filtered)} รายการ")
        m2.metric("Total Qty", f"{filtered['po_qty'].sum():,.0f}")
        m3.metric("Grand Total Value", f"{filtered['total_value'].sum():,.2f} THB")

    # 7. Data Display (ตารางแสดงข้อมูล)
    st.write("📋 **PO Status List**")
    display_cols = [
        'po_id', 'customer', 'part_no', 'po_qty', 'total_value', 
        'customer_eta_date', 'planning_production_date', 'logistic_ship_date', 'delivery_status'
    ]
    actual_cols = [c for c in display_cols if c in filtered.columns]
    
    st.dataframe(
        filtered[actual_cols],
        column_config={
            "total_value": st.column_config.NumberColumn("Total Value", format="%.2f"),
            "customer_eta_date": "ETA Date",
            "planning_production_date": "Prod. Finished",
            "logistic_ship_date": "Shipped Date"
        },
        use_container_width=True,
        hide_index=True
    )

    # --- จบฟังก์ชัน show_po_dashboard แค่ตรงนี้ ---
    ######################################### Mail Alert #############################
def send_po_auto_email(po_data, total_val):
    SENDER_EMAIL = "sim.mailalert@gmail.com"
    SENDER_PASS = "fsuuilzghlocfuvf"

    # 1. รายชื่อผู้รับ (Admin Team)
    admin_team = [
        "wattanapon.s@siamintermold.com", "paitoon.b@siamintermold.com", 
        "utai.c@siamintermold.com", "rewat.m@siamintermold.com", 
        "admincenter@siamintermold.com"
    ]
    
    staff_team = []
    # ดึงค่า Product Type มาตรวจสอบ (เช่น "Mold", "Mold-Part", "Mass-Part")
    product_type = po_data.get('product', 'Other') 

    # --- Logic ใหม่: ถ้ามีคำว่า 'Mold' อยู่ในชื่อประเภทสินค้า ---
    if "Mold" in product_type:
        # ครอบคลุมทั้ง "Mold" และ "Mold-Part"
        staff_team = ["thawat.t@siamintermold.com", "waiphop.b@siamintermold.com"]
    else:
        # สำหรับ "Mass-Part", "Steel Bush", "Other" ส่งหาคุณ Natthapol
        staff_team = ["natthapol.p@siamintermold.com","rungnapa.p@siamintermold.com"]

    all_receivers = list(set(admin_team + staff_team))

    # 2. สร้างเนื้อหาอีเมล (Email Content)
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = ", ".join(all_receivers)
    msg['Subject'] = f"🔔 [New PO Created] - {po_data.get('po_id')} | {po_data.get('customer')}"

    body = f"""
    เรียน ทีมงานที่เกี่ยวข้อง,

    มีการสร้างรายการสั่งซื้อ (PO) ใหม่ในระบบ:

    • PO ID: {po_data.get('po_id')}
    • Customer: {po_data.get('customer')}
    • Product Type: {product_type}
    • Part No/Name: {po_data.get('part_no')} / {po_data.get('part_name')}
    • Quantity: {po_data.get('po_qty', 0):,.0f}
    • Total Value: {total_val:,.2f} THB
    • ETA Date: {po_data.get('customer_eta_date')}
    • Delivery Round: {po_data.get('delivery_round')}

    ลิ้งค์เอกสาร: {po_data.get('file_link')}
    """
    msg.attach(MIMEText(body, 'plain'))

    # 3. ส่งอีเมลผ่าน SMTP
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"⚠️ ไม่สามารถส่งอีเมลได้: {e}")
        return False
# ==================================================
# 2. CREATE PO (Detailed Version)
# ==================================================
def show_po_create(HEADERS, URL_PO):
    st.subheader("➕ Create New PO")
    
    with st.form(key='po_form_unique_key_001'):
        st.markdown("##### 📦 Product Information")
        c1, c2 = st.columns(2)
        with c1:
            p_id = st.text_input("PO Number / ID *")
            p_cust = st.text_input("Customer Name *")
            p_no = st.text_input("Part Number *")
            p_name = st.text_input("Part Name")
        with c2:
            p_prod = st.selectbox("Product Type", ["Mold", "Mold-Part", "Mass-Part", "Steel Bush", "Other"])
            p_qty = st.number_input("Quantity *", min_value=0)
            p_price = st.number_input("Unit Price (THB) *", min_value=0.0, format="%.2f")
            p_link = st.text_input("Google Drive Link")

        st.divider()
        
        st.markdown("##### 🚚 Delivery & Split Shipment")
        d1, d2, d3 = st.columns(3)
        with d1:
            p_round = st.text_input("Delivery Round", value="1", help="เช่น 1, 2 หรือ 1/3")
        with d2:
            p_eta = st.date_input("Customer ETA Date")
        with d3:
            p_status = st.selectbox("Delivery Status", ["Pending", "Partial Shipped", "Fully Shipped"])

        p_remark = st.text_area("Internal Remark (ระบุรายละเอียดการแบ่งส่ง)")

        # --- ส่วนคำนวณเงินโชว์ก่อนกดส่ง ---
        total_preview = p_qty * p_price
        if total_preview > 0:
            st.info(f"💰 **Estimated Total Value:** {total_preview:,.2f} THB")

        if st.form_submit_button("Submit PO"):
            if p_id and p_cust and p_no:
                payload = {
                    "po_id": p_id, 
                    "customer": p_cust, 
                    "product": p_prod, 
                    "part_no": p_no,
                    "part_name": p_name,
                    "po_qty": p_qty, 
                    "unit_price": p_price,
                    "delivery_round": p_round,
                    "delivery_status": p_status,
                    "remark_internal": p_remark,
                    "customer_eta_date": p_eta.isoformat(), 
                    "file_link": p_link
                }
                
                res = requests.post(URL_PO, headers=HEADERS, json=payload)
                
                if res.status_code in [200, 201]:
                    st.success(f"✅ บันทึก PO {p_id} เรียบร้อย!")
                    
                    # --- 📧 ADD THIS PART TO SEND EMAIL ---
                    with st.spinner("กำลังส่งอีเมลแจ้งเตือน..."):
                        # We pass the 'payload' dict and the 'total_preview' we calculated earlier
                        email_sent = send_po_auto_email(payload, total_preview)
                        if email_sent:
                            st.toast("ส่งอีเมลแจ้งเตือนสำเร็จ!", icon="📧")
                    # --------------------------------------
                    
                    time.sleep(2) 
                    st.rerun()
                else:
                    st.error(f"❌ Error: {res.text}")
            else: 
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญ (PO ID, Customer, Part No) ให้ครบ")
# ==================================================
# 3. PLANNING UPDATE (Refined Selectbox)
# ==================================================
def show_planning_update(HEADERS, URL_PO, role, filter_type=None):
    st.subheader(f"🏗️ {filter_type} Production Feedback")
    
    # ดึงเฉพาะรายการที่ยังไม่ได้ลงวันที่ผลิตเสร็จ
    res = requests.get(f"{URL_PO}?planning_production_date=is.null&order=timestamp.desc", headers=HEADERS)
    
    if res.status_code == 200:
        df = pd.DataFrame(res.json())
        if not df.empty:
            # ✅ กรองแยกประเภทตามที่เลือกจากหน้า Console
            if filter_type == "Mold":
                df = df[df['product'].str.contains("Mold", case=False, na=False)]
            elif filter_type == "Mass":
                # แสดงงานที่ไม่ใช่ Mold (เช่น Mass-Part, Steel Bush, etc.)
                df = df[~df['product'].str.contains("Mold", case=False, na=False)]

            if not df.empty:
                df['display'] = df['po_id'] + " | " + df['customer'] + " (" + df['part_no'] + ")"
                
                with st.form(f"planning_form_{filter_type}"):
                    target_job = st.selectbox("เลือกรายการที่ผลิตเสร็จแล้ว:", df['display'].tolist())
                    p_id = target_job.split(" | ")[0]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        actual_finish = st.date_input("วันที่ผลิตเสร็จจริง (Actual Finish Date)")
                    with c2:
                        original_eta = df[df['po_id'] == p_id]['customer_eta_date'].values[0]
                        st.info(f"📅 Customer ETA: {original_eta}")
                    
                    p_remark = st.text_area("หมายเหตุการผลิต (Planning Remark)")
                    
                    if st.form_submit_button("Confirm Production Completed"):
                        payload = {
                            "planning_production_date": actual_finish.isoformat(),
                            "planning_remark": p_remark
                        }
                        res_up = requests.patch(f"{URL_PO}?po_id=eq.{p_id}", headers=HEADERS, json=payload)
                        if res_up.status_code in [200, 204]:
                            st.success(f"✅ ยืนยันการผลิต {p_id} สำเร็จ!"); time.sleep(1); st.rerun()
            else:
                st.success(f"🎉 ไม่มีงานค้างในส่วนของ {filter_type}")
# ==================================================
# 4. LOGISTIC UPDATE
# ==================================================
def show_logistic_update(HEADERS, URL_PO, role):
    st.subheader("🚚 Logistic & Shipping Feedback")
    
    # ดึงงานที่ผลิตเสร็จแล้วแต่ยังไม่ได้ส่ง
    res = requests.get(f"{URL_PO}?logistic_ship_date=is.null&planning_production_date=not.is.null&order=timestamp.desc", headers=HEADERS)
    
    if res.status_code == 200:
        df = pd.DataFrame(res.json())
        if not df.empty:
            df['display'] = df['po_id'] + " | " + df['customer'] + " (Round: " + df['delivery_round'].astype(str) + ")"
            
            with st.form("logistic_form_v2"):
                target_job = st.selectbox("เลือกรายการที่จัดส่งสำเร็จ:", df['display'].tolist())
                p_id = target_job.split(" | ")[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    ship_date = st.date_input("วันที่ส่งของจริง (Actual Ship Date)")
                with c2:
                    p_status = st.selectbox("Update Status", ["Fully Shipped", "Partial Shipped"])
                
                l_remark = st.text_area("หมายเหตุการจัดส่ง (Logistic Remark)")
                
                if st.form_submit_button("Confirm Shipment"):
                    payload = {
                        "logistic_ship_date": ship_date.isoformat(),
                        "logistic_remark": l_remark,
                        "delivery_status": p_status
                    }
                    res_up = requests.patch(f"{URL_PO}?po_id=eq.{p_id}", headers=HEADERS, json=payload)
                    if res_up.status_code in [200, 204]:
                        st.success(f"✅ บันทึกการส่งของ PO {p_id} สำเร็จ!"); time.sleep(1); st.rerun()
        else:
            st.info("📦 ยังไม่มีงานที่รอการจัดส่ง")
##################################################################
# --- เพิ่มฟังก์ชันนี้ต่อท้ายใน po_module.py (ห้ามแก้ของเดิม) ---

def show_po_update_center(HEADERS, URL_PO, role):
    st.subheader("🔄 PO Status Update Center")
    st.markdown("---")
    
    # สร้าง Tab ย่อยภายในหน้าอัปเดต เพื่อแยกหน้าที่ของแต่ละแผนก
    t_mold, t_mass, t_logis = st.tabs(["🏗️ Mold Work", "🏭 Mass Work", "🚚 Logistic"])
    
    with t_mold:
        # เรียกใช้ฟังก์ชันเดิม แต่ส่ง parameter เพื่อกรองงาน Mold
        show_planning_update(HEADERS, URL_PO, role, filter_type="Mold")
        
    with t_mass:
        # เรียกใช้ฟังก์ชันเดิม แต่ส่ง parameter เพื่อกรองงาน Mass
        show_planning_update(HEADERS, URL_PO, role, filter_type="Mass")
        
    with t_logis:
        # เรียกใช้ฟังก์ชันเดิมของ Logistic
        show_logistic_update(HEADERS, URL_PO, role)