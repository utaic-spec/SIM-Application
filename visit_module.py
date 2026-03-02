import streamlit as st
import pandas as pd
import requests
import time
from datetime import date, datetime, timedelta  # เพิ่ม timedelta เข้าไปตรงนี้

# ==============================================================================
# SECTION 1: CONFIGURATION & GLOBAL VARIABLES
# ==============================================================================
SALES_LIST = ["K.Utai", "K.Rewat", "K.Keng"]

# ==============================================================================
# SECTION 2: VISIT DASHBOARD & SEARCH SYSTEM
# ==============================================================================
def show_visit_dashboard(HEADERS, URL_VISIT):
    """หน้าจอหลักสำหรับดูตารางนัดหมายและสรุปผลการเข้าพบลูกค้า"""
    st.subheader("📅 Sales Visit Schedule & Summary")
    
    # ดึงข้อมูลล่าสุด (ดึงใหม่ทุกครั้งที่โหลดหน้านี้)
    res = requests.get(f"{URL_VISIT}?order=visit_date.desc", headers=HEADERS)
    
    if res.status_code == 200:
        df = pd.DataFrame(res.json())
        if not df.empty:
            df['visit_date'] = pd.to_datetime(df['visit_date']).dt.date
            
            # --- 2.1 ระบบกรองข้อมูล (Advanced Filters) ---
# --- 2.1 ระบบกรองข้อมูล (แก้ไข Error timedelta) ---
            with st.container(border=True):
                st.markdown("#### 🔍 Filter & Search")
                c1, c2, c3 = st.columns([1.5, 1, 1])
                with c1:
                    # ✅ ใช้ date.today() และ timedelta ที่ import มาโดยตรง
                    today = date.today()
                    first_day_of_month = today.replace(day=1)
                    
                    # หาวันสุดท้ายของเดือน: ไปวันที่ 28 แล้วบวกไป 4 วัน (เพื่อให้ทะลุไปเดือนหน้าแน่นอน) 
                    # แล้วลบออกด้วยจำนวนวันที่เกินมา
                    temp_date = first_day_of_month + timedelta(days=31)
                    last_day_of_month = temp_date - timedelta(days=temp_date.day)
                    
                    date_range = st.date_input(
                        "📅 ช่วงวันที่นัดหมาย (Default: เดือนนี้)", 
                        value=(first_day_of_month, last_day_of_month),
                        key="dash_date_filter_monthly_v3"
                    )
                with c2:
                    q_cust = st.text_input("🏢 ชื่อลูกค้า / วัตถุประสงค์", key="d_cust")
                with c3:
                    q_sales = st.selectbox("👤 Sales Owner", ["ทั้งหมด"] + SALES_LIST, key="d_sales")

            # --- 2.2 ประมวลผลการกรอง (Filter Logic) ---
            mask = df['customer_name'].str.contains(q_cust, case=False, na=False) | \
                   df['objective'].str.contains(q_cust, case=False, na=False)
            
            if q_sales != "ทั้งหมด":
                mask = mask & (df['sales_owner'] == q_sales)
            
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
                mask = mask & (df['visit_date'] >= start_date) & (df['visit_date'] <= end_date)
            
            df_filtered = df[mask]
            
            # --- 2.3 แสดงตารางข้อมูล ---
            st.write(f"พบข้อมูลทั้งหมด {len(df_filtered)} รายการ")
            st.dataframe(
                df_filtered[['visit_date', 'customer_name', 'objective', 'status', 'summary', 'visit_report', 'sales_owner']],
                column_config={
                    "visit_date": st.column_config.DateColumn("วันที่", format="DD/MM/YYYY"),
                    "customer_name": "ลูกค้า",
                    "objective": "วัตถุประสงค์",
                    "status": "สถานะ",
                    "summary": "📝 แผนงาน (Plan)",
                    "visit_report": "✅ รายงานผล (Report)",
                    "sales_owner": "Sales"
                },
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("💡 ยังไม่มีบันทึกข้อมูลในระบบ")
    else:
        st.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้ (Error: {res.status_code})")

# ==============================================================================
# SECTION 3: VISIT MANAGEMENT (PLANNING & REPORTING)
# ==============================================================================
def show_visit_management(HEADERS, URL_VISIT, current_user_name, user_role):
    """หน้าจัดการสำหรับ Sales: สร้างแผนงานใหม่ และ รายงานผลหลังเข้าพบ"""
    st.subheader("⚙️ Visit Planning & Reporting")
    
    t_plan, t_report = st.tabs(["➕ Create New Plan", "📝 Post-Visit Report"])

    # --- 3.1 TAB: สร้างแผนงานใหม่ (New Plan) ---
    with t_plan:
        with st.form("f_visit_create", clear_on_submit=True):
            st.markdown("#### 🚀 วางแผนเข้าพบลูกค้าใหม่")
            c1, c2 = st.columns(2)
            with c1:
                v_date = st.date_input("วันที่นัดหมาย", value=date.today())
                v_cust = st.text_input("ชื่อลูกค้า *", placeholder="ระบุชื่อบริษัทลูกค้า")
            with c2:
                # เลือกชื่อ Sales ปัจจุบันให้อัตโนมัติ
                default_idx = SALES_LIST.index(current_user_name) if current_user_name in SALES_LIST else 0
                v_owner = st.selectbox("Sales ผู้รับผิดชอบ *", options=SALES_LIST, index=default_idx)
                v_obj = st.selectbox("วัตถุประสงค์", ["แนะนำบริษัท", "ติดตาม RFQ", "ติดตาม Quotation", "รับ Project ใหม่", "อื่นๆ"])
            
            v_plan_details = st.text_area("รายละเอียดแผนงาน (Plan Summary)", placeholder="ระบุรายละเอียดสิ่งที่ตั้งใจจะเข้าไปคุย...")
            
            if st.form_submit_button("💾 บันทึกนัดหมาย", use_container_width=True, type="primary"):
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
                        st.success("✅ บันทึกแผนงานสำเร็จ!")
                        time.sleep(1)
                        st.rerun() # บังคับ Refresh เพื่อให้ Dashboard เห็นข้อมูลใหม่
                    else:
                        st.error(f"❌ บันทึกไม่สำเร็จ: {res.text}")
                else:
                    st.warning("⚠️ กรุณากรอกชื่อลูกค้า")

    # --- 3.2 TAB: สรุปผลการเข้าพบ (Post-Visit Report) ---
    with t_report:
        st.markdown("#### 📝 รายงานผลการทำงาน")
        
        # ดึงข้อมูลเฉพาะรายการที่ยังเป็น Planned เพื่อมารายงานผล
        res = requests.get(f"{URL_VISIT}?status=eq.Planned&order=visit_date.asc", headers=HEADERS)
        
        if res.status_code == 200:
            raw_data = res.json()
            if not raw_data:
                st.info("✨ ไม่มีรายการค้างรายงานผล (Planned) ในขณะนี้")
            else:
                df_pending = pd.DataFrame(raw_data)
                
                # Filter ย่อยภายในหน้า Report
                with st.expander("🔍 กรองรายการค้าง", expanded=False):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        f_cust = st.text_input("ค้นหาลูกค้า", key="f_report_cust")
                    with fc2:
                        f_sales = st.selectbox("กรองตาม Sales", ["ทั้งหมด"] + SALES_LIST, 
                                             index=SALES_LIST.index(current_user_name)+1 if current_user_name in SALES_LIST else 0)

                # ประมวลผล Filter
                df_to_report = df_pending[df_pending['customer_name'].str.contains(f_cust, case=False, na=False)]
                if f_sales != "ทั้งหมด":
                    df_to_report = df_to_report[df_to_report['sales_owner'] == f_sales]

                if not df_to_report.empty:
                    df_to_report['display'] = df_to_report['visit_date'].astype(str) + " | " + df_to_report['customer_name']
                    
                    # --- ฟอร์มรายงานผล ---
                    with st.form("f_visit_report_update"):
                        sel_v = st.selectbox("เลือกงานที่ต้องการรายงานผล", options=df_to_report['display'].tolist())
                        selected_row = df_to_report[df_to_report['display'] == sel_v].iloc[0]
                        
                        st.divider()
                        st.write(f"📅 **วันที่นัด:** {selected_row['visit_date']} | 🏢 **ลูกค้า:** {selected_row['customer_name']}")
                        st.info(f"📋 **แผนเดิม:** {selected_row['summary']}")
                        
                        c1, c2 = st.columns(2)
                        with c1: 
                            new_status = st.selectbox("ปรับสถานะงาน", ["Completed", "Postponed", "Cancelled"])
                        
                        v_actual_report = st.text_area("✍️ สรุปผลการเข้าพบ (Actual Report)", placeholder="พิมพ์สรุปเนื้อหาที่ได้คุยกับลูกค้าที่นี่...")
                        
                        if st.form_submit_button("📤 ส่งรายงานผล", use_container_width=True, type="primary"):
                            if v_actual_report: 
                                patch_data = {
                                    "status": new_status,
                                    "visit_report": v_actual_report
                                }
                                # ใช้ row['id'] หรือรหัสอ้างอิงของ Supabase
                                resp = requests.patch(f"{URL_VISIT}?id=eq.{selected_row['id']}", headers=HEADERS, json=patch_data)
                                
                                if resp.status_code in [200, 204]:
                                    st.success("✅ อัปเดตสถานะและรายงานผลเรียบร้อย!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ ไม่สามารถส่งข้อมูลได้: {resp.text}")
                            else:
                                st.warning("⚠️ กรุณากรอกรายละเอียดผลการเข้าพบก่อนส่ง")
                else:
                    st.warning("🔎 ไม่พบรายการที่ตรงกับเงื่อนไขการค้นหา")

