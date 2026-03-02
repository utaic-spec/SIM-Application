
import streamlit as st
import pandas as pd
import requests
import time
from datetime import date


# --- 🔗 Import Functions (ฉบับรวมร่าง) ---
try:
    from sales_module import show_sales_performance_report
    from po_module import (
        show_po_dashboard, 
        show_po_create, 
        show_planning_update, 
        show_logistic_update,
        show_po_update_center,
        show_ddp_cost_analysis
    )
    from rfq_module import (
        show_rfq_dashboard, 
        show_rfq_create, 
        show_rfq_update, 
        # show_rfq_management_summary
    )
    from visit_module import (
        show_visit_dashboard, 
        show_visit_management
    )
except ImportError as e:
    st.error(f"❌ ไม่พบไฟล์โมดูลลูก หรือชื่อฟังก์ชันไม่ถูกต้อง: {e}")
    st.stop()
########################################

# ==================================================
# 1. CONFIG & API
# ==================================================
URL_PO = "https://yqljvjfffrthnlbyitfw.supabase.co/rest/v1/po_records"
URL_RFQ = "https://yqljvjfffrthnlbyitfw.supabase.co/rest/v1/rfq_records"
URL_VISIT = "https://yqljvjfffrthnlbyitfw.supabase.co/rest/v1/visit_records"
HEADERS = {
    "apikey": "sb_secret_TfzEalDLlSQ8fvrrAuPUXg_JZeZAFLg",
    "Authorization": "Bearer sb_secret_TfzEalDLlSQ8fvrrAuPUXg_JZeZAFLg",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

USER_DB = {
    "director": {"pwd": "2573", "role": "admin", "name": "K.Utai"},
    "sales_admin": {"pwd": "sales2026", "role": "sales_admin", "name": "K.Fern"},
    "sales1": {"pwd": "s12026", "role": "sales", "name": "Keng"},
    "sales2": {"pwd": "s22026", "role": "sales", "name": "Sales 2"},
    "sales3": {"pwd": "s32026", "role": "sales", "name": "Sales 3"},
    "logistic": {"pwd": "logistic2026", "role": "planning", "name": "K.Rung"},
    "mold_admin": {"pwd": "mold2026", "role": "mold_planning", "name": "K.jack"},
    "mold_production": {"pwd": "prod_mold2026", "role": "mold_production", "name": "K.wat"}
}

st.set_page_config(page_title="SIM Master 2026", layout="wide")

# --- LOGIN LOGIC ---
if 'user' not in st.session_state:
    col_login = st.columns([1, 1.2, 1])[1]
    with col_login:
        st.write("##")
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 SIM Login</h2>", unsafe_allow_html=True)
            u = st.text_input("User ID")
            p = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True, type="primary"):
                if u in USER_DB and USER_DB[u]['pwd'] == p:
                    st.session_state.user = USER_DB[u]
                    st.session_state.user_id = u 
                    st.rerun()
                else: st.error("❌ ID หรือ Password ไม่ถูกต้อง")
    st.stop()

user = st.session_state.user
role = user['role']
current_user_id = st.session_state.user_id

with st.sidebar:
    st.title("🚀 SIM System")
    st.write(f"👤 User: **{user['name']}**")
    st.write(f"🔑 Role: `{role}`")
    st.divider()
    if st.button("🚪 Log out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ==================================================
# 3. NAVIGATION LOGIC & GROUPING (แก้ไขตามค่า Debug)
# ==================================================

# 1. นิยามกลุ่มเมนู
po_group = ["📊 Dashboard PO", "➕ Create PO", "🔄 PO Status Update", "📊 DDP Cost Analysis"]
rfq_group = ["📋 RFQ Dashboard", "➕ Create RFQ", "📈 RFQ Update"]
visit_group = ["📅 Visit Dashboard", "➕ Plan & Report Visit"]
# ✅ เพิ่มกลุ่มใหม่
sales_report_group = ["📈 Sales Performance"] 

# รวมลำดับทั้งหมด
master_order = po_group + rfq_group + visit_group + sales_report_group

# 2. เริ่มต้นรวบรวมสิทธิ์
allowed_raw = ["📊 Dashboard PO"]
u_role = str(role).lower().strip()
u_id = str(current_user_id).lower().strip()

if u_id in ["director", "sales_admin"]:
    allowed_raw = master_order  # Director เห็นทุกอย่างรวมถึง Sales Report
    
elif u_role == "sales":
    # หากต้องการให้ Sales เห็น Report ของตัวเองด้วย ให้เพิ่มรายการในลิสต์นี้
    allowed_raw.extend(["📋 RFQ Dashboard", "📈 RFQ Update", "📅 Visit Dashboard", 
                        "➕ Plan & Report Visit", "➕ Create PO", "📈 Sales Performance"])
# 🔥 แก้ไขตรงนี้: ถ้า User ID คือ 'logistic' ให้เห็น DDP ทันที 
# ไม่ว่า Role ในระบบจะเป็น planning หรืออะไรก็ตาม
elif u_id == "logistic" or "log" in u_role:
    allowed_raw.extend(["🔄 PO Status Update", "📊 DDP Cost Analysis"])

elif "planning" in u_role or "mold" in u_role:
    allowed_raw.append("🔄 PO Status Update")

# 3. สร้างรายการแท็บจริง
allowed_tabs = [menu for menu in master_order if menu in allowed_raw]
# ==================================================
# 4. UI RENDER & ROUTING
# ==================================================
if allowed_tabs:
    tabs = st.tabs(allowed_tabs) 
    
    for idx, tab_name in enumerate(allowed_tabs):
        with tabs[idx]:
            # --- ระบบ PO ---
            if tab_name == "📊 Dashboard PO":
                show_po_dashboard(HEADERS, URL_PO, role)
            elif tab_name == "➕ Create PO":
                show_po_create(HEADERS, URL_PO)
            elif tab_name == "🔄 PO Status Update":
                show_po_update_center(HEADERS, URL_PO, role)
            elif tab_name == "📊 DDP Cost Analysis": # ✅ ย้ายขึ้นมาในกลุ่ม PO
                show_ddp_cost_analysis(HEADERS, URL_PO, role)

            # --- ระบบ RFQ ---
            elif tab_name == "📋 RFQ Dashboard": 
                show_rfq_dashboard(HEADERS, URL_RFQ)
            elif tab_name == "➕ Create RFQ": 
                show_rfq_create(HEADERS, URL_RFQ)
            elif tab_name == "📈 RFQ Update": 
                show_rfq_update(HEADERS, URL_RFQ)
            
            # --- ระบบ Sales Visit ---
            elif tab_name == "📅 Visit Dashboard": 
                show_visit_dashboard(HEADERS, URL_VISIT)
            elif tab_name == "➕ Plan & Report Visit": 
                show_visit_management(HEADERS, URL_VISIT, user['name'], role)

            # --- ✅ เพิ่มระบบ Sales Performance Report ---
            # ใน loop ของ allowed_tabs
            elif tab_name == "📈 Sales Performance":
                show_sales_performance_report() # เรียกใช้ฟังก์ชันจากไฟล์ใหม่

            # --- เมนูเดิม (กันเหนียว) ---
            elif tab_name == "🏭 Planning Update":
                show_planning_update(HEADERS, URL_PO, role)
            elif tab_name == "🚚 Logistic Update":
                show_logistic_update(HEADERS, URL_PO, role)

