import streamlit as st
import pandas as pd
import requests
import time
from datetime import date

# Updated Sales List
SALES_LIST = ["K.Utai", "K.Rewat", "Sales 3"]

# --- 1. DASHBOARD ---
def show_visit_dashboard(HEADERS, URL_VISIT):
    st.subheader("📅 Sales Visit Schedule & Summary")
    res = requests.get(f"{URL_VISIT}?order=visit_date.desc", headers=HEADERS)
    
    if res.status_code == 200:
        df = pd.DataFrame(res.json())
        if not df.empty:
            df['visit_date'] = pd.to_datetime(df['visit_date']).dt.date
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    # ✅ ตัวกรองช่วงวันที่
                    date_range = st.date_input("📅 เลือกช่วงวันที่นัดหมาย", 
                                              value=(date.today().replace(day=1), date.today()),
                                              key="dash_date_filter")
                with c2:
                    q_cust = st.text_input("🔍 ค้นหาลูกค้า", key="d_cust")
                with c3:
                    q_sales = st.selectbox("👤 Sales", ["ทั้งหมด"] + SALES_LIST, key="d_sales")

            # Logic การกรอง
            mask = df['customer_name'].str.contains(q_cust, case=False, na=False)
            if q_sales != "ทั้งหมด":
                mask = mask & (df['sales_owner'] == q_sales)
            
            # ✅ กรองตามช่วงวันที่ (ตรวจสอบว่าเลือกครบทั้ง start และ end)
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                mask = mask & (df['visit_date'] >= start_date) & (df['visit_date'] <= end_date)
            
            df_filtered = df[mask]
            
            st.dataframe(
                df_filtered[['visit_date', 'customer_name', 'objective', 'status', 'summary', 'visit_report', 'sales_owner']],
                column_config={
                    "visit_date": st.column_config.DateColumn("วันที่", format="DD/MM/YYYY"),
                    "summary": "📝 แผนงาน (Plan)",
                    "visit_report": "✅ รายงานผล (Report)"
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("💡 ยังไม่มีบันทึกข้อมูล")

# --- 2. MANAGEMENT ---
def show_visit_management(HEADERS, URL_VISIT, current_user_name, user_role):
    st.subheader("⚙️ Visit Planning & Reporting")
    t_plan, t_report = st.tabs(["➕ New Plan", "📝 Post-Visit Report"])

    # --- TAB: NEW PLAN ---
    with t_plan:
        with st.form("f_visit_create", clear_on_submit=True):
            st.markdown("#### 🚀 สร้างแผนการเข้าพบลูกค้า")
            c1, c2 = st.columns(2)
            with c1:
                v_date = st.date_input("วันที่นัดหมาย", value=date.today())
                v_cust = st.text_input("ชื่อลูกค้า *")
            with c2:
                default_idx = SALES_LIST.index(current_user_name) if current_user_name in SALES_LIST else 0
                v_owner = st.selectbox("Sales ผู้รับผิดชอบ *", options=SALES_LIST, index=default_idx)
                v_obj = st.selectbox("วัตถุประสงค์", ["แนะนำบริษัท", "ติดตาม RFQ", "ติดตาม Quotation", "รับ Project ใหม่", "อื่นๆ"])
            
            v_plan_details = st.text_area("รายละเอียดแผนงาน (Plan Summary)")
            
            if st.form_submit_button("บันทึกนัดหมาย"):
                if v_cust:
                    payload = {
                        "visit_date": v_date.isoformat(),
                        "customer_name": v_cust,
                        "objective": v_obj,
                        "status": "Planned",
                        "summary": v_plan_details,
                        "sales_owner": v_owner
                    }
                    res = requests.post(URL_VISIT, headers=HEADERS, json=payload)
                    if res.status_code in [200, 201]:
                        st.success("✅ บันทึกแผนงานสำเร็จ!"); time.sleep(1); st.rerun()

    # --- TAB: POST-VISIT REPORT ---
    with t_report:
        st.markdown("#### 📝 สรุปผลการเข้าพบลูกค้า")
        
        # ดึงข้อมูลทั้งหมด
        res = requests.get(f"{URL_VISIT}?order=visit_date.asc", headers=HEADERS)
        
        if res.status_code == 200:
            all_data = pd.DataFrame(res.json())
            if not all_data.empty:
                # กรองเฉพาะ Planned (Case-insensitive)
                raw_df = all_data[all_data['status'].str.lower() == 'planned'].copy()
                
                # --- Filter Section ---
                with st.expander("🔍 กรองรายการเพื่อหาลูกค้า", expanded=True):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        f_cust = st.text_input("ค้นหาลูกค้า", key="f_report_cust")
                    with fc2:
                        f_sales = st.selectbox("กรองตาม Sales", ["ทั้งหมด"] + SALES_LIST, 
                                             index=SALES_LIST.index(current_user_name)+1 if current_user_name in SALES_LIST else 0)

                # Apply Filters
                df_to_report = raw_df[raw_df['customer_name'].str.contains(f_cust, case=False, na=False)]
                if f_sales != "ทั้งหมด":
                    df_to_report = df_to_report[df_to_report['sales_owner'] == f_sales]

                if not df_to_report.empty:
                    df_to_report['display'] = df_to_report['visit_date'].astype(str) + " | " + df_to_report['customer_name'] + " (" + df_to_report['sales_owner'] + ")"
                    
                    # --- FORM เริ่มต้นตรงนี้ ---
                    # --- FORM ที่แก้ไขแล้ว ---
                    with st.form("f_visit_report", clear_on_submit=True):
                        sel_v = st.selectbox("เลือกงานที่ต้องการรายงานผล", options=df_to_report['display'].tolist())
                        row = df_to_report[df_to_report['display'] == sel_v].iloc[0]
                        
                        c1, c2 = st.columns(2)
                        with c1: 
                            new_status = st.selectbox("ปรับสถานะ", ["Completed", "Postponed", "Cancelled"])
                        
                        # ✅ แก้ไข: ใช้ key แบบคงที่ (Static Key) เพื่อให้ Form จำค่าได้แม่นยำ
                        v_actual_report = st.text_area(
                            "สรุปผลการเข้าพบ (Actual Report)", 
                            value=""
                        )
                        
                        if st.form_submit_button("📤 ส่งรายงานผล"):
                            # ตรวจสอบว่ามีการพิมพ์ข้อมูลจริงหรือไม่
                            if v_actual_report: 
                                patch_data = {
                                    "status": new_status,
                                    "visit_report": v_actual_report
                                }
                                resp = requests.patch(f"{URL_VISIT}?id=eq.{row['id']}", headers=HEADERS, json=patch_data)
                                
                                if resp.status_code in [200, 204]:
                                    st.success("✅ บันทึกรายงานสำเร็จ!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ เกิดข้อผิดพลาดจากระบบ: {resp.status_code}")
                            else:
                                # กรณีไม่ได้พิมพ์อะไรเลย
                                st.warning("⚠️ กรุณากรอกรายละเอียดรายงานก่อนส่ง")