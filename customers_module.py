import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px 

def show_customer_module(headers, url, role):
    st.subheader("👥 Customer Database Management")

    # รายชื่อ Sales สำหรับใช้ทั้งไฟล์
    SALES_LIST = ["K.Keng", "K.Utai", "K.Rewat"]

# ==================================================
    # 📊 1. CUSTOMER STRATEGIC DASHBOARD (FULL SET - FIXED)
    # ==================================================
    with st.expander("📈 คลิกเพื่อเปิด/ปิด แดชบอร์ดวิเคราะห์ข้อมูลลูกค้า", expanded=False):
        res_dash = requests.get(f"{url}?select=*", headers=headers)
        
        # 1. เช็คว่าดึงข้อมูลสำเร็จไหม
        if res_dash.status_code == 200 and res_dash.json():
            df_dash = pd.DataFrame(res_dash.json())
            
            # --- KPI CARDS ---
            kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
            kpi_col1.metric("👥 ลูกค้ารวม", f"{len(df_dash):,}")
            if 'mkt_status' in df_dash.columns:
                active_rfq = len(df_dash[df_dash['mkt_status'] == 'RFQ'])
                kpi_col2.metric("📈 อยู่ระหว่าง RFQ", f"{active_rfq} ราย")
            if 'industry_segment' in df_dash.columns and not df_dash['industry_segment'].isnull().all():
                top_seg = df_dash['industry_segment'].value_counts().idxmax()
                kpi_col3.metric("🏢 อุตสาหกรรมหลัก", top_seg)

            st.divider()

            # --- แถวที่ 1: กราฟ Pie และ กราฟอุตสาหกรรม ---
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                if 'mkt_status' in df_dash.columns:
                    df_mkt = df_dash['mkt_status'].value_counts().reset_index()
                    df_mkt.columns = ['Status', 'Count']
                    fig_mkt = px.pie(df_mkt, values='Count', names='Status', title='📊 สัดส่วนสถานะการตลาด',
                                   hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                    st.plotly_chart(fig_mkt, use_container_width=True)

            with chart_col2:
                if 'industry_segment' in df_dash.columns:
                    df_segment = df_dash['industry_segment'].value_counts().reset_index()
                    df_segment.columns = ['Segment', 'Count']
                    fig_seg = px.bar(df_segment, x='Segment', y='Count', title='🏢 การกระจายตัวตามกลุ่มอุตสาหกรรม',
                                   color='Count', color_continuous_scale='Blues', text_auto=True)
                    fig_seg.update_traces(textposition='outside')
                    st.plotly_chart(fig_seg, use_container_width=True)

            st.divider()

            # --- แถวที่ 2: กราฟ BU และ กราฟ Sales ---
            chart_col3, chart_col4 = st.columns(2)
            with chart_col3:
                if 'bu_type' in df_dash.columns:
                    df_bu = df_dash['bu_type'].dropna().str.split(', ').explode().value_counts().reset_index()
                    df_bu.columns = ['BU Type', 'Count']
                    fig_bu = px.bar(df_bu, x='Count', y='BU Type', orientation='h', title='📈 พอร์ตโฟลิโอตาม BU',
                                   color='Count', color_continuous_scale='Reds', text_auto=True)
                    fig_bu.update_traces(textposition='outside')
                    st.plotly_chart(fig_bu, use_container_width=True)

            with chart_col4:
                if 'sales_owner' in df_dash.columns:
                    df_sales = df_dash['sales_owner'].fillna('No Sales').value_counts().reset_index()
                    df_sales.columns = ['Sales Name', 'Count']
                    fig_sales = px.bar(df_sales, x='Sales Name', y='Count', title='👤 จำนวนลูกค้าแยกตาม Sales',
                                     color='Sales Name', color_discrete_sequence=px.colors.qualitative.Pastel, text_auto=True)
                    fig_sales.update_traces(textposition='outside')
                    st.plotly_chart(fig_sales, use_container_width=True)

            # --- แถวที่ 3: วิเคราะห์เจาะลึก (Deep Dive Analysis) ---
            st.divider()
            st.markdown("#### 🔍 Sales Performance Breakdown (%)")
            
            if 'sales_owner' in df_dash.columns and 'mkt_status' in df_dash.columns:
                # 1. เตรียมข้อมูล: นับจำนวนแยกตาม Sales และ Status
                df_breakdown = df_dash.groupby(['sales_owner', 'mkt_status']).size().reset_index(name='Count')
                
                # 2. คำนวณ % ของแต่ละ Status เทียบกับลูกค้าทั้งหมดของ Sales คนนั้นๆ
                df_breakdown['pct'] = df_breakdown.groupby('sales_owner')['Count'].transform(lambda x: (x / x.sum() * 100).round(1))
                
                # 3. สร้างกราฟ Stacked Bar Chart
                fig_breakdown = px.bar(
                    df_breakdown, 
                    x='sales_owner', 
                    y='Count', 
                    color='mkt_status',
                    title='📊 สัดส่วนสถานะลูกค้าแยกตามรายชื่อ Sales (แสดงจำนวน และ %)',
                    barmode='stack',
                    # ใช้ text เพื่อแสดงทั้ง จำนวน และ % พร้อมกัน
                    text=df_breakdown.apply(lambda row: f"{row['Count']} ({row['pct']}%)", axis=1),
                    color_discrete_map={
                        "Potentials": '#FFA500', 
                        'RFQ': '#1E90FF', 
                        'Award': '#32CD32', 
                        'Not Interest': '#FF4500'
                    }
                )
                
                fig_breakdown.update_layout(
                    xaxis_title="ชื่อ Sales ผู้ดูแล",
                    yaxis_title="จำนวนลูกค้า (ราย)",
                    legend_title="สถานะการตลาด"
                )
                
                # ปรับตำแหน่งตัวเลขให้อยู่กึ่งกลางแท่งเพื่อความสวยงาม
                fig_breakdown.update_traces(textposition='inside')
                
                st.plotly_chart(fig_breakdown, use_container_width=True)
            else:
                st.info("💡 ข้อมูลไม่เพียงพอสำหรับการคำนวณ %")

    # --- 1. จัดการเรื่องสิทธิ์ (Role Logic) ---
    tab_list = ["📋 รายชื่อลูกค้า", "➕ ลงทะเบียนลูกค้าใหม่"]
    if role in ['admin', 'sales_admin', 'sales']:
        tab_list.append("📝 แก้ไขข้อมูลลูกค้า")

    all_tabs = st.tabs(tab_list)

    # --- TAB 1: รายชื่อลูกค้า ---
    with all_tabs[0]:
        res = requests.get(f"{url}?select=*", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                # เพิ่ม sales_owner ในหน้าแสดงผลด้วย
                cols = ['cust_code', 'cust_name', 'bu_type', 'sales_owner', 'mkt_status']
                available_cols = [c for c in cols if c in df.columns]
                st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีข้อมูลลูกค้า")

    # --- TAB 2: ลงทะเบียนลูกค้าใหม่ ---
    with all_tabs[1]: # ✅ ต้องระบุ Tab Index ให้ชัดเจน
        with st.form("reg_customer_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                code = st.text_input("รหัสลูกค้า (Customer Code)*")
                name = st.text_input("ชื่อบริษัท/ลูกค้า*")
                bu = st.selectbox("กลุ่มธุรกิจ (BU)", ['MASS', 'MOLD', 'Mass&Mold', 'Special-Part', 'Services'])
                sales_name = st.selectbox("Sales ผู้ดูแล*", SALES_LIST)
            with c2:
                bu_details = st.text_input("รายละเอียดลูกค้า")
                segment = st.selectbox("กลุ่มอุตสาหกรรม", ["Automotive", "Electronics", "Medical", "Other"])
                term = st.text_input("Credit Term")
                contact = st.text_input("ชื่อผู้ติดต่อ / เบอร์โทร")
            
            address = st.text_area("ที่อยู่ (Address)")
            
            # ✅ ใช้ตัวแปรเดียวตรวจสอบการ Submit
            submit_reg = st.form_submit_button("บันทึกข้อมูล", type="primary")
            
            if submit_reg:
                if code and name:
                    payload = {
                        "cust_code": code, "cust_name": name, "bu_type": bu,
                        "bu_details": bu_details, "industry_segment": segment,
                        "credit_term": term, "contact_name": contact, "address": address,
                        "mkt_status": "Potentials", "sales_owner": sales_name
                    }
                    res = requests.post(url, headers=headers, json=payload)
                    if res.status_code in [200, 201]:
                        st.success(f"✅ บันทึก {name} เรียบร้อย")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {res.text}")
                else:
                    st.warning("⚠️ กรุณากรอกรหัสและชื่อลูกค้า")

    # --- TAB 3: แก้ไขข้อมูลลูกค้า ---
    if len(all_tabs) > 2:
        with all_tabs[2]:
            BU_OPTIONS = ['MASS', 'MOLD', 'Mass&Mold', 'Special-Part', 'Services']
            MARKETING_OPTIONS = ['Not Interest', "Potentials", 'RFQ', 'Award']

            res_all = requests.get(f"{url}?select=*", headers=headers)
            if res_all.status_code == 200 and res_all.json():
                full_cust_df = pd.DataFrame(res_all.json())
                
                search_query = st.text_input("🔍 ค้นหาลูกค้าที่ต้องการแก้ไข", placeholder="พิมพ์ชื่อหรือรหัส...")
                
                if search_query:
                    filtered_cust = full_cust_df[
                        full_cust_df['cust_name'].str.contains(search_query, case=False, na=False) |
                        full_cust_df['cust_code'].str.contains(search_query, case=False, na=False)
                    ]
                else:
                    filtered_cust = full_cust_df

                if not filtered_cust.empty:
                    cust_list = (filtered_cust['cust_code'] + " | " + filtered_cust['cust_name']).tolist()
                    selected_cust_item = st.selectbox("เลือกรายชื่อ:", cust_list)
                    
                    sel_code = selected_cust_item.split(" | ")[0]
                    cust_row = filtered_cust[filtered_cust['cust_code'] == sel_code].iloc[0]
                    
                    st.divider()
                    
                    # ✅ Form แก้ไข
                    with st.form("update_customer_form"):
                        st.info(f"📝 กำลังแก้ไข: {cust_row['cust_name']}")
                        uc1, uc2 = st.columns(2)
                        
                        with uc1:
                            u_name = st.text_input("ชื่อบริษัท/ลูกค้า*", value=str(cust_row.get('cust_name', '')))
                            # ✅ ดึงค่า Sales เดิม
                            old_sales = cust_row.get('sales_owner', "K.Rewat")
                            try: s_idx = SALES_LIST.index(old_sales)
                            except: s_idx = 0
                            u_sales = st.selectbox("Sales ผู้ดูแล", SALES_LIST, index=s_idx)
                            
                            # Multiselect BU
                            old_bu = cust_row.get('bu_type', '')
                            default_bu = [b.strip() for b in old_bu.split(',')] if old_bu else []
                            u_bu_list = st.multiselect("กลุ่มธุรกิจ (BU)", BU_OPTIONS, default=default_bu)
                        
                        with uc2:
                            # Marketing Status
                            raw_mkt = cust_row.get('mkt_status', "Potentials")
                            old_mkt = raw_mkt.strip("'") if isinstance(raw_mkt, str) else "Potentials"
                            try: mkt_idx = MARKETING_OPTIONS.index(old_mkt)
                            except: mkt_idx = 1 
                            u_mkt_status = st.selectbox("Marketing Status", MARKETING_OPTIONS, index=mkt_idx)
                            
                            u_term = st.text_input("Credit Term", value=str(cust_row.get('credit_term', '')))
                            u_contact = st.text_input("ผู้ติดต่อ", value=str(cust_row.get('contact_name', '')))

                        u_address = st.text_area("ที่อยู่", value=str(cust_row.get('address', '')))
                        
                        # ✅ ปุ่มกดอัปเดต (ต้องอยู่ใน with st.form)
                        if st.form_submit_button("🔄 อัปเดตข้อมูลลูกค้า", type="primary"):
                            update_payload = {
                                "cust_name": u_name,
                                "bu_type": ", ".join(u_bu_list),
                                "mkt_status": u_mkt_status,
                                "sales_owner": u_sales,
                                "credit_term": u_term,
                                "contact_name": u_contact,
                                "address": u_address
                            }
                            p_url = f"{url}?cust_code=eq.{sel_code}"
                            u_res = requests.patch(p_url, headers=headers, json=update_payload)
                            if u_res.status_code in [200, 204]:
                                st.success("✅ อัปเดตเรียบร้อย!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ อัปเดตไม่สำเร็จ: {u_res.text}")
            else:
                st.info("ไม่มีข้อมูลลูกค้า")
