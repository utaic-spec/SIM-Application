
import streamlit as st
import pandas as pd
import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart # ✅ ตัวนี้แหละที่ขาดไป
from email.mime.base import MIMEBase
from email import encoders


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
        staff_team = ["natthapol.p@siamintermold.com","rungnapa.p@siamintermold.com","waiphop.b@siamintermold.com"]

    all_receivers = list(set(admin_team + staff_team))
    ####################################################### Test #####################################
    # admin_team = ["utai.c@siamintermold.com" ]
    
    # staff_team = []
    # # ดึงค่า Product Type มาตรวจสอบ (เช่น "Mold", "Mold-Part", "Mass-Part")
    # product_type = po_data.get('product', 'Other') 

    # # --- Logic ใหม่: ถ้ามีคำว่า 'Mold' อยู่ในชื่อประเภทสินค้า ---
    # if "Mold" in product_type:
    #     # ครอบคลุมทั้ง "Mold" และ "Mold-Part"
    #     staff_team = ["utai.c@siamintermold.com"]
    # else:
    #     # สำหรับ "Mass-Part", "Steel Bush", "Other" ส่งหาคุณ Natthapol
    #     staff_team = ["utai.c@siamintermold.com"]

    # all_receivers = list(set(admin_team + staff_team))
    ####################################################################################

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
######################################################
def show_ddp_cost_analysis(HEADERS, URL_PO, role):
    st.subheader("📊 Steel Bush DDP Cost Analysis (Multi-Currency)")
    st.markdown("---")
    
    # 1. Fetch only Steel Bush records
    query_url = f"{URL_PO}?product=ilike.*Steel Bush*&select=*" 
    response = requests.get(query_url, headers=HEADERS)
    
    if response.status_code == 200:
        df = pd.DataFrame(response.json())
        if df.empty:
            st.warning("🔍 No 'Steel Bush' items found in PO database.")
            return

        # 2. Select by po_id (as requested)
        po_list = df['po_id'].unique()
        selected_id = st.selectbox("🎯 Select PO ID to Analyze", ["-- Select ID --"] + list(po_list))
        
        if selected_id != "-- Select ID --":
            po_data = df[df['po_id'] == selected_id].iloc[0]
            qty = float(po_data.get('po_qty', 1))

            col_left, col_right = st.columns([1, 1], gap="large")
            
            with col_left:
                st.markdown("### 💰 Revenue & Currency")
                with st.container(border=True):
                    # Select Currency of the Sales Price
                    currency = st.selectbox("Sales Currency", ["USD", "CNY", "THB"])
                    unit_price_foreign = st.number_input(f"Unit Price ({currency})", 
                                                       value=float(po_data.get('unit_price', 0)))
                    
                    # Exchange Rate Input (Visible if not THB)
                    if currency != "THB":
                        ex_rate_sales = st.number_input(f"Current Exchange Rate (1 {currency} = ? THB)", 
                                                       value=33.00 if currency == "USD" else 4.40, 
                                                       format="%.4f")
                    else:
                        ex_rate_sales = 1.0

                    # Calculate Revenue in THB
                    total_revenue_thb = (unit_price_foreign * qty) * ex_rate_sales
                    st.success(f"**Total Revenue:** {total_revenue_thb:,.2f} THB")

                st.markdown("### 📝 Actual Costs (THB)")
                with st.container(border=True):
                    base_unit_cost_thb = st.number_input("Cost per Unit (THB)", value=float(po_data.get('base_cost', 5.95)))
                    total_sb_cost_thb = base_unit_cost_thb * qty
                    
                    trans_cost = st.number_input("Total Transportation Cost (THB)", min_value=0.0)
                    tariff = st.number_input("Total Tariff / Duty (THB)", min_value=0.0)
                    gst_vat = st.number_input("Total Destination GST/VAT (THB)", min_value=0.0)
                    interest = st.number_input("Interest on Credit Term (THB)", min_value=0.0)

            with col_right:
                st.markdown("### 📈 Profitability (Normalized to THB)")
                
                # Calculation Logic
                total_actual_cost_thb = total_sb_cost_thb + trans_cost + tariff + gst_vat + interest
                actual_profit_thb = total_revenue_thb - total_actual_cost_thb
                margin_pct = (actual_profit_thb / total_revenue_thb * 100) if total_revenue_thb > 0 else 0
                
                # Comparison with Original Plan
                planned_profit_thb = float(po_data.get('expected_profit', 0))
                gp_gap = actual_profit_thb - planned_profit_thb

                with st.container(border=True):
                    st.metric("Total Revenue (THB)", f"{total_revenue_thb:,.2f}")
                    st.metric("Total Shipment Cost (THB)", f"{total_actual_cost_thb:,.2f}")
                    st.metric("Actual Profit (THB)", f"{actual_profit_thb:,.2f}", delta=f"{gp_gap:,.2f} vs Plan")
                    st.metric("Final Margin", f"{margin_pct:.2f} %")

                # Visual Warning for GP Gap
                if gp_gap < 0:
                    st.error(f"🔴 Lower than planned by {abs(gp_gap):,.2f} THB")
                else:
                    st.success(f"🟢 Higher than planned by {gp_gap:,.2f} THB")

                st.info(f"💡 Profit per unit: {(actual_profit_thb/qty):,.2f} THB")

    else:
        st.error("❌ Data connection failed.")
#########################################
import pandas as pd
import requests
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. ฟังก์ชันส่ง Email (ประกาศไว้ก่อน) ---
def send_ddp_approval_email(po_id, data_summary):
    SENDER_EMAIL = "sim.mailalert@gmail.com"
    SENDER_PASS = "fsuuilzghlocfuvf" 
    
    admin_team = [
        "wattanapon.s@siamintermold.com", "paitoon.b@siamintermold.com", 
        "utai.c@siamintermold.com", "rewat.m@siamintermold.com", 
        "rungnapa.p@siamintermold.com"
    ]
    
    message = MIMEMultipart()
    message["From"] = f"SIM System Alert <{SENDER_EMAIL}>"
    message["To"] = ", ".join(admin_team)
    message["Subject"] = f"🔔 [Request Approval] DDP Cost Analysis - PO ID: {po_id}"

    # กำหนดสถานะและสี
    status_color = "#D4EFDF" if data_summary['margin'] >= 16 else "#FCF3CF"
    status_text = "AUTO-APPROVED" if data_summary['margin'] >= 16 else "WAIT FOR REVIEW"

    body = f"""
    <html>
    <body style="font-family: sans-serif; color: #333;">
        <h3 style="color: #2E86C1;">Steel Bush DDP Cost Analysis for Approval</h3>
        <p>เรียน ทีมบริหาร,</p>
        <p>คุณรุ่ง (Logistic) ได้วิเคราะห์ต้นทุน DDP สำหรับ <b>{data_summary['product']}</b> เรียบร้อยแล้ว:</p>
        
        <table border="1" style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr style="background-color: #f2f2f2;">
                <th colspan="2" style="padding: 10px; text-align: center;">สรุปรายการวิเคราะห์ (Summary)</th>
            </tr>
            <tr><td style="padding: 8px; width: 40%;">PO ID</td><td style="padding: 8px;">{po_id}</td></tr>
            <tr><td style="padding: 8px;">จำนวน (Quantity)</td><td style="padding: 8px;">{data_summary['qty']:,.0f} units</td></tr>
            <tr style="background-color: #EBF5FB;">
                <td style="padding: 8px;"><b>รายได้รวม (Total Revenue)</b></td>
                <td style="padding: 8px;"><b>{data_summary['revenue']:,.2f} THB</b></td>
            </tr>
            
            <tr style="background-color: #f2f2f2;">
                <th colspan="2" style="padding: 10px; text-align: center;">รายละเอียดต้นทุน (Cost Breakdown)</th>
            </tr>
            <tr><td style="padding: 8px;">ต้นทุนสินค้า (Base Cost)</td><td style="padding: 8px;">{data_summary['base_cost_total']:,.2f} THB</td></tr>
            <tr><td style="padding: 8px;">ค่าขนส่ง (Transportation)</td><td style="padding: 8px;">{data_summary['trans_cost']:,.2f} THB</td></tr>
            <tr><td style="padding: 8px;">ภาษีนำเข้า (Tariff/Duty)</td><td style="padding: 8px;">{data_summary['tariff']:,.2f} THB</td></tr>
            <tr><td style="padding: 8px;">Destination VAT/GST</td><td style="padding: 8px;">{data_summary['gst_vat']:,.2f} THB</td></tr>
            <tr><td style="padding: 8px;">ดอกเบี้ย (Interest)</td><td style="padding: 8px;">{data_summary['interest']:,.2f} THB</td></tr>
            <tr style="background-color: #FDEDEC;">
                <td style="padding: 8px;"><b>รวมต้นทุนทั้งหมด</b></td>
                <td style="padding: 8px;"><b>{data_summary['total_cost']:,.2f} THB</b></td>
            </tr>

            <tr style="background-color: #f2f2f2;">
                <th colspan="2" style="padding: 10px; text-align: center;">ตัวชี้วัดกำไร (Profitability)</th>
            </tr>
            <tr style="font-size: 1.1em;">
                <td style="padding: 10px;"><b>กำไรสุทธิ (Actual Profit)</b></td>
                <td style="padding: 10px; color: blue;"><b>{data_summary['profit']:,.2f} THB</b></td>
            </tr>
            <tr style="font-size: 1.2em; background-color: {status_color};">
                <td style="padding: 10px;"><b>GP % (Margin)</b></td>
                <td style="padding: 10px;"><b>{data_summary['margin']:.2f}%</b></td>
            </tr>
            <tr style="background-color: {status_color};">
                <td style="padding: 10px;"><b>สถานะการอนุมัติ</b></td>
                <td style="padding: 10px;"><b>{status_text}</b></td>
            </tr>
        </table>
        
        <p style="margin-top: 20px;">กรุณาพิจารณารายละเอียดต้นทุนด้านบนเพื่อการตัดสินใจ</p>
        <hr>
        <p style="font-size: 0.8em; color: gray;">ส่งโดยระบบอัตโนมัติ SIM System</p>
    </body>
    </html>
    """
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(message)
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

# --- 2. ฟังก์ชันหลักสำหรับ UI ---
def show_ddp_cost_analysis(HEADERS, URL_PO, role):
    st.subheader("📊 Steel Bush DDP Cost Analysis (Multi-Currency)")
    st.markdown("---")
    
    query_url = f"{URL_PO}?product=ilike.*Steel Bush*&select=*" 
    response = requests.get(query_url, headers=HEADERS)
    
    if response.status_code == 200:
        df = pd.DataFrame(response.json())
        if df.empty:
            st.warning("🔍 No 'Steel Bush' items found.")
            return

        po_list = df['po_id'].unique()
        selected_id = st.selectbox("🎯 Select PO ID to Analyze", ["-- Select ID --"] + list(po_list))
        
        if selected_id != "-- Select ID --":
            po_data = df[df['po_id'] == selected_id].iloc[0]
            qty = float(po_data.get('po_qty', 1))

            col_left, col_right = st.columns([1, 1], gap="large")
            
            with col_left:
                st.markdown("### 💰 Revenue & Currency")
                with st.container(border=True):
                    currency = st.selectbox("Sales Currency", ["USD", "CNY", "THB"])
                    unit_price_foreign = st.number_input(f"Unit Price ({currency})", value=float(po_data.get('unit_price', 0)))
                    ex_rate_sales = st.number_input("Exchange Rate (1 Foreign = ? THB)", value=33.0 if currency=="USD" else 4.4 if currency=="CNY" else 1.0)
                    total_revenue_thb = (unit_price_foreign * qty) * ex_rate_sales
                    st.success(f"**Total Revenue:** {total_revenue_thb:,.2f} THB")

                st.markdown("### 📝 Actual Costs (THB)")
                with st.container(border=True):
                    base_unit_cost_thb = st.number_input("Cost per Unit (THB)", value=float(po_data.get('base_cost', 5.95)))
                    total_sb_cost_thb = base_unit_cost_thb * qty
                    trans_cost = st.number_input("Transportation Cost", min_value=0.0)
                    tariff = st.number_input("Tariff / Duty", min_value=0.0)
                    gst_vat = st.number_input("Destination GST/VAT", min_value=0.0)
                    interest = st.number_input("Interest Cost", min_value=0.0)

            with col_right:
                st.markdown("### 📈 Profitability")
                total_actual_cost_thb = total_sb_cost_thb + trans_cost + tariff + gst_vat + interest
                actual_profit_thb = total_revenue_thb - total_actual_cost_thb
                margin_pct = (actual_profit_thb / total_revenue_thb * 100) if total_revenue_thb > 0 else 0
                
                planned_profit_thb = float(po_data.get('expected_profit', 0))
                gp_gap = actual_profit_thb - planned_profit_thb

                with st.container(border=True):
                    st.metric("Total Revenue", f"{total_revenue_thb:,.2f}")
                    st.metric("Total Cost", f"{total_actual_cost_thb:,.2f}")
                    st.metric("Actual Profit", f"{actual_profit_thb:,.2f}", delta=f"{gp_gap:,.2f} vs Plan")
                    st.subheader(f"GP%: {margin_pct:.2f}%")
                    
                    if margin_pct >= 16.0:
                        st.success("✅ **Status: Auto-Approved** (GP ≥ 16%)")
                    else:
                        st.warning("⚠️ **Status: Wait for Approval** (GP < 16%)")

                if gp_gap < 0:
                    st.error(f"🔴 Lower than planned by {abs(gp_gap):,.2f}")
                else:
                    st.success(f"🟢 Higher than planned by {gp_gap:,.2f}")

            # --- ปุ่มส่งอีเมล (อยู่ภายใต้ IF selected_id) ---
            # --- 1. เตรียมชุดข้อมูลสำหรับส่งเมลไว้ก่อน (ข้างนอกปุ่มกด) ---
            summary_data = {
                "product": po_data.get('product'),
                "qty": qty,
                "revenue": total_revenue_thb,
                "base_cost_total": total_sb_cost_thb,
                "trans_cost": trans_cost,
                "tariff": tariff,
                "gst_vat": gst_vat,
                "interest": interest,
                "total_cost": total_actual_cost_thb,
                "profit": actual_profit_thb,
                "margin": margin_pct,
                "gap": gp_gap
            }

            st.markdown("---")
            
            # --- 2. ปุ่มกดเรียกใช้ฟังก์ชันส่งเมล ---
            if st.button("🚀 ส่งรายงานและขออนุมัติ (Send Mail to Admin Team)", use_container_width=True, type="primary"):
                with st.spinner("กำลังส่งอีเมลรายละเอียดต้นทุน..."):
                    # ตอนนี้ summary_data มีค่าแน่นอนแล้ว เพราะเตรียมไว้ด้านบน
                    if send_ddp_approval_email(selected_id, summary_data):
                        st.success(f"✅ ส่งรายงาน PO ID {selected_id} เรียบร้อยแล้ว")
                        st.balloons()
                    else:
                        st.error("❌ การส่งอีเมลล้มเหลว กรุณาตรวจสอบการตั้งค่า")

