
import streamlit as st
import pandas as pd
import requests
import time

def show_customer_module(headers, url, role):
    st.subheader("👥 Customer Database Management")

    # --- 1. จัดการเรื่องสิทธิ์ (Role Logic) ---
    # ตั้งค่า Tab พื้นฐานที่ทุกคนเห็น (Sales เห็นแค่ 2 อันนี้)
    tab_list = ["📋 รายชื่อลูกค้า", "➕ ลงทะเบียนลูกค้าใหม่"]
    
    # ถ้าเป็น admin หรือ sales_admin ให้เพิ่ม Tab ที่ 3 (แก้ไข) เข้าไป
    # (หมายเหตุ: ใน USER_DB ของคุณ director มี role = 'admin')
    if role in ['admin', 'sales_admin', 'sales']:
        tab_list.append("📝 แก้ไขข้อมูลลูกค้า")

    # สร้าง Tabs ตามรายการที่เราเตรียมไว้
    all_tabs = st.tabs(tab_list)

    # --- TAB 1: รายชื่อลูกค้า (ทุกคนเห็น) ---
    with all_tabs[0]:
        res = requests.get(f"{url}?select=*", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                cols = ['cust_code', 'cust_name', 'bu_type', 'bu_details', 'address', 'credit_term']
                available_cols = [c for c in cols if c in df.columns]
                st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
            else:
                st.info("ยังไม่มีข้อมูลลูกค้า")
        else:
            st.error("ไม่สามารถดึงข้อมูลได้")

    # --- TAB 2: ลงทะเบียนลูกค้าใหม่ (ทุกคนเห็น) ---
    with all_tabs[1]:
        with st.form("reg_customer_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                code = st.text_input("รหัสลูกค้า (Customer Code)*")
                name = st.text_input("ชื่อบริษัท/ลูกค้า*")
                bu = st.selectbox("กลุ่มธุรกิจ (BU)", ['MASS', 'MOLD', 'Mass&Mold', 'Special-Part', 'Services'])
                bu_details = st.text_input("รายละเอียดลูกค้า (Customer Details)")
            with c2:
                segment = st.selectbox("กลุ่มอุตสาหกรรม", ["Automotive", "Electronics", "Medical", "Other"])
                term = st.text_input("Credit Term (เช่น 30 Days)")
                contact = st.text_input("ชื่อผู้ติดต่อ / เบอร์โทร")
                address = st.text_area("ที่อยู่ (Address)")
            
            if st.form_submit_button("บันทึกข้อมูล", type="primary"):
                if code and name:
                    payload = {
                        "cust_code": code, "cust_name": name, "bu_type": bu,
                        "bu_details": bu_details, "industry_segment": segment,
                        "credit_term": term, "contact_name": contact, "address": address
                    }
                    res = requests.post(url, headers=headers, json=payload)
                    if res.status_code in [200, 201]:
                        st.success(f"✅ บันทึก {name} เรียบร้อยแล้ว")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ บันทึกไม่สำเร็จ: {res.text}")
                else:
                    st.warning("⚠️ กรุณากรอกรหัสและชื่อลูกค้า")

    # --- TAB 3: แก้ไขข้อมูลลูกค้า (เฉพาะ Admin/Director เห็น) ---
    if len(all_tabs) > 2:
        with all_tabs[2]:
            # ตัวเลือกพื้นฐาน
            BU_OPTIONS = ['MASS', 'MOLD', 'Mass&Mold', 'Special-Part', 'Services']
            MARKETING_OPTIONS = ['Not Interest', 'Potentials', 'RFQ', 'Award']

            # ดึงข้อมูลมาแสดงเพื่อเลือกแก้ไข
            res_all = requests.get(f"{url}?select=*", headers=headers)
            if res_all.status_code == 200 and res_all.json():
                full_cust_df = pd.DataFrame(res_all.json())
                
                search_query = st.text_input("🔍 ค้นหาลูกค้าเพื่อแก้ไข (ชื่อหรือรหัส)", placeholder="พิมพ์เพื่อค้นหา...")
                
                if search_query:
                    filtered_cust = full_cust_df[
                        full_cust_df['cust_name'].str.contains(search_query, case=False, na=False) |
                        full_cust_df['cust_code'].str.contains(search_query, case=False, na=False)
                    ]
                else:
                    filtered_cust = full_cust_df

                if not filtered_cust.empty:
                    cust_list = (filtered_cust['cust_code'] + " | " + filtered_cust['cust_name']).tolist()
                    selected_cust_item = st.selectbox("เลือกรายชื่อที่ต้องการแก้ไข:", cust_list)
                    
                    sel_code = selected_cust_item.split(" | ")[0]
                    cust_row = filtered_cust[filtered_cust['cust_code'] == sel_code].iloc[0]
                    
                    st.divider()
                    
                    with st.form("update_customer_form"):
                        st.info(f"📝 แก้ไขข้อมูลของ: {cust_row['cust_name']} ({sel_code})")
                        uc1, uc2 = st.columns(2)
                        with uc1:
                            u_name = st.text_input("ชื่อบริษัท/ลูกค้า*", value=cust_row.get('cust_name', ''))
                            
                            # --- อัปเกรดเป็น Multiselect เฉพาะหน้าแก้ไข ---
                            old_bu = cust_row.get('bu_type', '')
                            # แยก string "MASS, MOLD" กลับมาเป็น list เพื่อโชว์ในช่องเลือก
                            default_bu = [b.strip() for b in old_bu.split(',')] if old_bu else []
                            u_bu_list = st.multiselect("กลุ่มธุรกิจ (BU) - เลือกได้หลายข้อ", BU_OPTIONS, default=default_bu)
                            
                            u_bu_details = st.text_input("รายละเอียดลูกค้า", value=cust_row.get('bu_details', ''))
                        
                        with uc2:
                            # --- เพิ่มช่อง Marketing Status ---
                            old_mkt = cust_row.get('mkt_status', 'Potentials')
                            try: mkt_idx = MARKETING_OPTIONS.index(old_mkt)
                            except: mkt_idx = 1 # ถ้าหาไม่เจอให้เริ่มที่ Potentials
                            u_mkt_status = st.selectbox("Marketing Status", MARKETING_OPTIONS, index=mkt_idx)
                            
                            segments = ["Automotive", "Electronics", "Medical", "Other"]
                            try: seg_idx = segments.index(cust_row.get('industry_segment', 'Other'))
                            except: seg_idx = 3
                            u_segment = st.selectbox("กลุ่มอุตสาหกรรม", segments, index=seg_idx)
                            u_term = st.text_input("Credit Term", value=cust_row.get('credit_term', ''))
                            u_contact = st.text_input("ชื่อผู้ติดต่อ / เบอร์โทร", value=cust_row.get('contact_name', ''))
                        
                        u_address = st.text_area("ที่อยู่ (Address)", value=cust_row.get('address', ''))
                        
                        if st.form_submit_button("🔄 อัปเดตข้อมูลลูกค้า", type="primary"):
                            # รวม List กลับเป็น String เพื่อส่งเข้า Supabase
                            u_bu_string = ", ".join(u_bu_list) if u_bu_list else ""
                            
                            update_payload = {
                                "cust_name": u_name, 
                                "bu_type": u_bu_string, 
                                "bu_details": u_bu_details,
                                "mkt_status": u_mkt_status, # ส่งสถานะการตลาด
                                "industry_segment": u_segment, 
                                "credit_term": u_term,
                                "contact_name": u_contact, 
                                "address": u_address
                            }
                            patch_url = f"{url}?cust_code=eq.{sel_code}"
                            u_res = requests.patch(patch_url, headers=headers, json=update_payload)
                            
                            if u_res.status_code in [200, 204]:
                                st.success("✅ อัปเดตข้อมูลเรียบร้อย!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ อัปเดตไม่สำเร็จ: {u_res.text}")
            else:
                st.info("ไม่มีข้อมูลลูกค้าให้แก้ไข")
