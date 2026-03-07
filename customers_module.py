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
                bu_details = st.text_input("รายละเอียดลูกค้า (Customer Details)*")
                cust_status = st.selectbox("สถาณะ ( Status)", ['Awarded', 'RFQ', 'On-Duce'])
            with c2:
                segment = st.selectbox("กลุ่มอุตสาหกรรม", ["Automotive", "Electronics", "Medical", "Other"])
                term = st.text_input("Credit Term (เช่น 30 Days)")
                contact = st.text_input("ชื่อผู้ติดต่อ / เบอร์โทร")
                address = st.text_area("ที่อยู่ (Address)") # เพิ่มฟิลด์ Address
            
            if st.form_submit_button("บันทึกข้อมูล", type="primary"):
                if code and name:
                    payload = {
                        "cust_code": code,
                        "cust_name": name,
                        "bu_type": bu,
                        "industry_segment": segment,
                        "credit_term": term,
                        "contact_name": contact
                    }
                    # ใช้ requests.post เหมือนที่ระบบเดิมคุณทำ
                    res = requests.post(url, headers=headers, json=payload)
                    if res.status_code in [200, 201]:
                        st.success(f"✅ บันทึก {name} เรียบร้อยแล้ว")
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ บันทึกไม่สำเร็จ: {res.text}")
                else:
                    st.warning("⚠️ กรุณากรอกรหัสและชื่อลูกค้า")

    with t_list:
        # ดึงข้อมูลมาโชว์ด้วย requests.get
        res = requests.get(f"{url}?select=*", headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data:
                df = pd.DataFrame(data)
                # จัดเรียงคอลัมน์ให้ดูง่าย
                cols = ['cust_code', 'cust_name', 'bu_type', 'industry_segment', 'credit_term']
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลลูกค้า")
        else:

            st.error("ไม่สามารถดึงข้อมูลได้")
