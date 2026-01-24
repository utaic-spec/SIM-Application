
import streamlit as st
import pandas as pd
import requests
import time
from datetime import date

# --- 🔗 Import Functions (ฉบับรวมร่าง) ---
try:
    from po_module import (
        show_po_dashboard, 
        show_po_create, 
        show_planning_update, 
        show_logistic_update,
        show_po_update_center 
    )
    from rfq_module import (
        show_rfq_dashboard, 
        show_rfq_create, 
        show_rfq_update, 
        show_rfq_management_summary
    )
    from visit_module import (
        show_visit_dashboard, 
        show_visit_management
    )
except ImportError as e:
    st.error(f"❌ ไม่พบไฟล์โมดูลลูก หรือชื่อฟังก์ชันไม่ถูกต้อง: {e}")
    st.stop()

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
    "sales1": {"pwd": "s12026", "role": "sales", "name": "Sales 1"},
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
# 3. NAVIGATION LOGIC & GROUPING (แก้ไขเพื่อให้เมนูขยับจัดกลุ่ม)
# ==================================================

# 1. รวบรวมสิทธิ์เบื้องต้น (ห้ามใช้ list(dict.fromkeys) ตอนท้าย)
allowed_raw = ["📊 Dashboard PO"]

if current_user_id in ["director", "sales_admin"]:
    allowed_raw.extend([
        "📋 RFQ Dashboard", "📊 RFQ Summary", "➕ Create RFQ", "📈 RFQ Update", 
        "📅 Visit Dashboard", "➕ Plan & Report Visit", "➕ Create PO"
    ])
elif role == "sales":
    allowed_raw.extend([
        "📋 RFQ Dashboard", "📈 RFQ Update", "📅 Visit Dashboard", "➕ Plan & Report Visit", "➕ Create PO"
    ])
elif role in ["planning", "mold_planning", "mold_production", "logistic"]:
    allowed_raw.append("🔄 PO Status Update")

# 2. 🔥 จุดสำคัญ: กำหนดลำดับกลุ่มที่เราต้องการ (จัดให้ใหม่ตามนี้)
po_group = ["📊 Dashboard PO", "➕ Create PO", "🔄 PO Status Update"]
rfq_group = ["📋 RFQ Dashboard", "📊 RFQ Summary", "➕ Create RFQ", "📈 RFQ Update"]
visit_group = ["📅 Visit Dashboard", "➕ Plan & Report Visit"]

# รวมลำดับแม่บท (Master Order)
master_order = po_group + rfq_group + visit_group

# 3. 🔥 บังคับเรียงลำดับตามกลุ่มที่กำหนดไว้
# บรรทัดนี้จะทำให้เมนู "ขยับ" มาเรียงเป็นกลุ่ม PO -> RFQ -> Visit ทันที
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
            
            # --- ระบบ RFQ ---
            elif tab_name == "📋 RFQ Dashboard": 
                show_rfq_dashboard(HEADERS, URL_RFQ)
            elif tab_name == "📊 RFQ Summary": 
                show_rfq_management_summary(HEADERS, URL_RFQ)
            elif tab_name == "➕ Create RFQ": 
                show_rfq_create(HEADERS, URL_RFQ)
            elif tab_name == "📈 RFQ Update": 
                show_rfq_update(HEADERS, URL_RFQ)
            
            # --- ระบบ Sales Visit ---
            elif tab_name == "📅 Visit Dashboard": 
                show_visit_dashboard(HEADERS, URL_VISIT)
            elif tab_name == "➕ Plan & Report Visit": 
                show_visit_management(HEADERS, URL_VISIT, user['name'], role)

            # --- เมนูเดิม (กันเหนียว) ---
            elif tab_name == "🏭 Planning Update":
                show_planning_update(HEADERS, URL_PO, role)
            elif tab_name == "🚚 Logistic Update":
                show_logistic_update(HEADERS, URL_PO, role)