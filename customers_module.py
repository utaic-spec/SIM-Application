import streamlit as st
import pandas as pd
import requests

def show_customer_module(headers, url):
    st.subheader("👥 Customer Database Management")

    t_list, t_reg = st.tabs(["📋 รายชื่อลูกค้า", "➕ ลงทะเบียนลูกค้าใหม่"])

    with t_reg:
        with st.form("reg_customer_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                code = st.text_input("รหัสลูกค้า (Customer Code)*")
                name = st.text_input("ชื่อบริษัท/ลูกค้า*")
                bu = st.selectbox("กลุ่มธุรกิจ (BU)", ['MASS', 'MOLD', 'Mass&Mold', 'Special-Part', 'Services'])
                bu_details = st.text_input("รายละเอียดลูกค้า (Customer Details)") # เก็บค่านี้
            with c2:
                segment = st.selectbox("กลุ่มอุตสาหกรรม", ["Automotive", "Electronics", "Medical", "Other"])
                term = st.text_input("Credit Term (เช่น 30 Days)")
                contact = st.text_input("ชื่อผู้ติดต่อ / เบอร์โทร")
                address = st.text_area("ที่อยู่ (Address)") # เก็บค่านี้
            
            if st.form_submit_button("บันทึกข้อมูล", type="primary"):
                if code and name:
                    # ปรับปรุง Payload ให้ครอบคลุมทุกช่องข้อมูล
                    payload = {
                        "cust_code": code,
                        "cust_name": name,
                        "bu_type": bu,
                        "bu_details": bu_details, # เพิ่มตรงนี้
                        "industry_segment": segment,
                        "credit_term": term,
                        "contact_name": contact,
                        "address": address        # เพิ่มตรงนี้
                    }
                    
                    res = requests.post(url, headers=headers, json=payload)
                    if res.status_code in [200, 201]:
                        st.success(f"✅ บันทึก {name} เรียบร้อยแล้ว")
                    else:
                        st.error(f"❌ บันทึกไม่สำเร็จ: {res.text}")
                else:
                    st.warning("⚠️ กรุณากรอกรหัสและชื่อลูกค้า")

    with t_list:
        res = requests.get(f"{url}?select=*", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                # เพิ่ม address และ bu_details เข้าไปในคอลัมน์ที่แสดงผล
                cols = ['cust_code', 'cust_name', 'bu_type', 'bu_details', 'address', 'credit_term']
                # เช็คว่ามีคอลัมน์ใน DataFrame หรือไม่ก่อนแสดงผล
                available_cols = [c for c in cols if c in df.columns]
                st.dataframe(df[available_cols], use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลลูกค้า")
        else:
            st.error("ไม่สามารถดึงข้อมูลได้")
