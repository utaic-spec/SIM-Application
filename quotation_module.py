import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from fpdf import FPDF
import os
#########################################
def get_next_quotation_number(existing_numbers):
    if not existing_numbers:
        return "CSP2026001" # ถ้ายังไม่มีข้อมูลเลย ให้เริ่มที่เลขนี้
    
    # สมมติรูปแบบคือ CSP + ปี (2026) + เลขรัน 3 หลัก (เช่น 001)
    # เราจะเอาเลขที่มากที่สุด
    last_id = sorted(existing_numbers)[-1]
    
    # แยกส่วนที่เป็นตัวอักษร/ปี (เช่น CSP2026) และเลขรัน (เช่น 001)
    # สมมติว่าเลขรันอยู่ 3 หลักสุดท้ายเสมอ
    prefix = last_id[:-3]
    last_number = int(last_id[-3:])
    
    # เพิ่มเลขเข้าไป 1
    new_number = last_number + 1
    
    # คืนค่ากลับเป็นรูปแบบเดิม เช่น CSP2026002
    return f"{prefix}{str(new_number).zfill(3)}"
#########################################################
def generate_pdf(data, items, cust_info):
    pdf = FPDF()
    font_dir = "." 
    
    # โหลดฟอนต์ (ประกาศครั้งเดียว)
    pdf.add_font("THSarabun", "", os.path.join(font_dir, "THSarabunNew.ttf"), uni=True)
    pdf.add_font("THSarabun", "B", os.path.join(font_dir, "THSarabunNew Bold.ttf"), uni=True)
    pdf.add_font("THSarabun", "I", os.path.join(font_dir, "THSarabunNew Italic.ttf"), uni=True)
    pdf.add_font("THSarabun", "BI", os.path.join(font_dir, "THSarabunNew BoldItalic.ttf"), uni=True)

    pdf.add_page()
    
    # --- HEADER & INFO ---
    pdf.image('sim_logo.png', 10, 10, 40)
    pdf.set_xy(50, 10)
    pdf.set_font("THSarabun", 'B', 20)
    pdf.cell(150, 10, "Siam Inter Mold Co.,Ltd", ln=1, align='R')
    pdf.set_x(50)
    pdf.set_font("THSarabun", "", 12)
    pdf.multi_cell(150, 6, "161/64 Moo.1, Suksawat Rd., Samutprakan 10290 | Tel : 02-006-6046", align='R')
    pdf.ln(10)
    
    pdf.set_x(113)
    pdf.set_font("THSarabun", "B", 13)
    pdf.cell(50, 7, "Quotation No:", 0, 0, 'R')
    pdf.set_font("THSarabun", "", 13)
    pdf.cell(50, 7, str(data.get('qt_number', '-')), 0, 1, 'L')
    
    pdf.ln(5)
    pdf.set_x(100)
    pdf.set_font("THSarabun", "B", 13)
    pdf.cell(50, 7, "Date:", 0, 0, 'R')
    pdf.set_font("THSarabun", "", 13)
    pdf.cell(50, 7, str(data.get('date', '')), 0, 1, 'L')
    pdf.ln(10)
    
    pdf.set_font("THSarabun", 'B', 14)
    pdf.cell(0, 7, "Bill To:", ln=True)
    pdf.set_font("THSarabun", "", 13)
    pdf.multi_cell(0, 6, f"Company: {cust_info['name']}\nAddress: {cust_info['address']}\nContact: {cust_info['contact']}")
    pdf.ln(5)

    # --- TABLE ---
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("THSarabun", 'B', 13)
    pdf.cell(90, 10, "Description", border=1, fill=True, align='C')
    pdf.cell(30, 10, "Qty", border=1, fill=True, align='C')
    pdf.cell(30, 10, "Price", border=1, fill=True, align='C')
    pdf.cell(30, 10, "Total", border=1, fill=True, align='C', ln=True)
    
    pdf.set_font("THSarabun", "", 13)
    for it in items:
        qty = float(it['qty'])
        price = float(it['price'])
        total = qty * price
        start_x, start_y = pdf.get_x(), pdf.get_y()
        
        pdf.multi_cell(90, 7, str(it['desc']), border=1, align='L')
        row_height = pdf.get_y() - start_y
        
        pdf.set_xy(start_x + 90, start_y)
        pdf.cell(30, row_height, "", border=1) 
        pdf.cell(30, row_height, "", border=1)
        pdf.cell(30, row_height, "", border=1, ln=True)
        
        pdf.set_xy(start_x + 90, start_y)
        pdf.cell(30, 7, f"{qty:,.0f}", border=0, align='C')
        pdf.cell(30, 7, f"{price:,.2f}", border=0, align='R')
        pdf.cell(30, 7, f"{total:,.2f}", border=0, align='R')
        pdf.set_y(start_y + row_height)

    # --- GRAND TOTAL ---
    pdf.set_font("THSarabun", "B", 14)
    pdf.cell(150, 10, "Grand Total (Excluding VAT)", border=1, align='R')
    pdf.cell(30, 10, f"{data.get('grand_total', 0.0):,.2f}", border=1, align='R', ln=True)

    # --- REMARK & SIGNATURE ---
    pdf.ln(10)
    pdf.set_font("THSarabun", 'I', 12)
    pdf.multi_cell(0, 6, f"Remark: {data.get('remark', '-')}") 
    
    pdf.ln(5)
    pdf.set_font("THSarabun", "I", 12)
    acceptance_text = "I hereby acknowledge and accept the terms, conditions, and prices quoted above, and authorize Siam Inter Mold Co., Ltd. to proceed with the requested work/delivery."
    pdf.multi_cell(0, 5, acceptance_text, align='L')
    
    pdf.ln(10)
    # --- ลายเซ็นต์ 3 ฝ่าย ---
    pdf.ln(13) # เว้นที่สำหรับเซ็น
    
    # 1. หัวข้อลายเซ็นต์
    pdf.set_font("THSarabun", "B", 12)
    pdf.cell(63, 10, "Sales Representative", align='C')
    pdf.cell(63, 10, "Authorized by Company", align='C')
    pdf.cell(63, 10, "Accepted by Customer", align='C', ln=True)
    
    # 2. เส้นขีดสำหรับเซ็น
    pdf.ln(10)
    pdf.cell(63, 5, "____________________", align='C')
    pdf.cell(63, 5, "____________________", align='C')
    pdf.cell(63, 5, "____________________", align='C', ln=True)
    
    # 3. ชื่อตำแหน่ง / ข้อมูลเพิ่มเติม
    pdf.cell(63, 5, "(____________________)", align='C')
    pdf.cell(63, 5, "(____________________)", align='C')
    pdf.cell(63, 5, "(____________________)", align='C', ln=True)
    
    # 4. วันที่
    pdf.ln(5)
    pdf.cell(63, 5, "Date: ____/____/____", align='C')
    pdf.cell(63, 5, "Date: ____/____/____", align='C')
    pdf.cell(63, 5, "Date: ____/____/____", align='C', ln=True)

    raw_pdf = pdf.output(dest='S')
    return bytes(raw_pdf) if isinstance(raw_pdf, (str, bytearray)) else raw_pdf
def get_next_quotation_number(existing_numbers, group):
    # กำหนด Prefix ตามกลุ่มสินค้า (ปรับตัวย่อให้ตรงกับที่บริษัทใช้จริงนะครับ)
    prefix_map = {"Mold": "MLD", "Mass": "MSS", "Mass&Mold": "MSM", "Job Shop": "JOB"}
    prefix_code = prefix_map.get(group, "QT")
    
    # กรองรายการที่มีเฉพาะ Prefix นี้
    filtered = [n for n in existing_numbers if n.startswith(prefix_code)]
    
    if not filtered:
        return f"{prefix_code}2026001"
    
    # หาค่าที่มากที่สุด
    last_id = sorted(filtered)[-1]
    
    # ดึงตัวเลข 3 หลักสุดท้ายมาบวกเพิ่ม
    try:
        last_number = int(last_id[-3:])
        return f"{prefix_code}2026{str(last_number + 1).zfill(3)}"
    except:
        return f"{prefix_code}2026001"

def show_quotation_module(headers, url_qt, url_cust):
    st.title("📄 Create / Update Quotation")

    # 1. ดึงข้อมูลพื้นฐาน (ลูกค้า + รายการ Quotation ทั้งหมด)
    res_cust = requests.get(f"{url_cust}?select=cust_code,cust_name,address,contact_name", headers=headers)
    cust_df = pd.DataFrame(res_cust.json())
    cust_options = cust_df.apply(lambda x: f"{x['cust_code']} | {x['cust_name']}", axis=1).tolist()

    try:
        # ดึง Quotation ทั้งหมดมาเพื่อทำ List ให้เลือก
        res_all = requests.get(f"{url_qt}?select=*", headers=headers)
        all_qt_data = res_all.json()
        qt_list = ["-- สร้างใบใหม่ (New) --"] + [item['qt_number'] for item in all_qt_data]
    except:
        all_qt_data = []
        qt_list = ["-- สร้างใบใหม่ (New) --"]

    # 2. ส่วนเลือกใบเดิมเพื่อทำ Revision
    selected_old_qt = st.selectbox("เลือก Quotation เดิมเพื่อทำ Rev ใหม่ (ถ้ามี):", qt_list)

    # 3. เตรียม Logic สำหรับโหลดข้อมูลเก่าลงตารางสินค้า (Session State)
    if "qt_items_fixed" not in st.session_state:
        st.session_state.qt_items_fixed = [{"desc": "", "qty": 1, "unit": "Pcs", "price": 0.0} for _ in range(5)]

    # --- เมื่อมีการเลือกใบเก่า ---
    if selected_old_qt != "-- สร้างใบใหม่ (New) --" and st.button("🔄 โหลดข้อมูลใบเดิม"):
        old_record = next(item for item in all_qt_data if item['qt_number'] == selected_old_qt)
        
        # โหลดรายการสินค้ากลับเข้า Session State (สมมติ Column ชื่อ 'items_json')
        # หมายเหตุ: ถ้าคุณเก็บเป็น String ต้อง json.loads() ก่อนนะครับ
        if 'items_json' in old_record and old_record['items_json']:
            loaded_items = old_record['items_json']
            # เติมให้ครบ 5 แถวเสมอ
            while len(loaded_items) < 5:
                loaded_items.append({"desc": "", "qty": 1, "unit": "Pcs", "price": 0.0})
            st.session_state.qt_items_fixed = loaded_items[:5]
            st.success("โหลดรายการสินค้าเดิมเรียบร้อยแล้ว!")
            st.rerun()

    # 4. ส่วนกรอกข้อมูลหลัก
    with st.container(border=True):
        group = st.radio("กลุ่มสินค้า", ["Mold", "Mass", "Mass&Mold", "Job Shop"], horizontal=True)
        
        # Logic การตั้งเลข ID และ Rev
        if selected_old_qt == "-- สร้างใบใหม่ (New) --":
            existing_qt_nos = [item['qt_number'] for item in all_qt_data]
            next_id = get_next_quotation_number(existing_qt_nos, group)
            current_rev = "0"
        else:
            # ดึงเลข ID เดิมออกมา (ตัดคำว่า Rev. ออก)
            next_id = selected_old_qt.split(" Rev.")[0]
            # ดึงเลข Rev เดิมมา +1
            try:
                old_rev = int(selected_old_qt.split(" Rev.")[-1])
                current_rev = str(old_rev + 1)
            except:
                current_rev = "1"

        col1, col2 = st.columns(2)
        qt_no = col1.text_input("Quotation ID", value=next_id)
        rev = col2.text_input("Revision (Rev)", value=current_rev)
        
        full_qt_id = f"{qt_no} Rev.{rev}"
        qt_date = st.date_input("วันที่", datetime.now())
        selected_cust = st.selectbox("เลือกลูกค้า", cust_options)
        remark = st.text_area("หมายเหตุ", value="VAT is not included, Price Validity 30 Days")

#########################
    # 1. จัดการ Session State สำหรับเก็บรายการสินค้า (เริ่มที่ 1 แถวว่าง)
    if "qt_items" not in st.session_state:
        st.session_state.qt_items = [{"desc": "", "qty": 1, "unit": "Pcs", "price": 0.0}]

    st.subheader("รายการสินค้า")
    
    # 2. ส่วนหัวตาราง
    header_cols = st.columns([4, 1, 1, 2, 0.5]) # เพิ่ม column สุดท้ายสำหรับปุ่มลบ
    header_cols[0].write("**Description**")
    header_cols[1].write("**Qty**")
    header_cols[2].write("**Unit**")
    header_cols[3].write("**Price**")
    header_cols[4].write("") # พื้นที่ว่างเหนือปุ่มลบ

    # 3. ลูปวาดแถวตามจำนวนที่มีใน session_state
    for i, row in enumerate(st.session_state.qt_items):
        cols = st.columns([4, 1, 1, 2, 0.5])
        
        # เก็บค่าลงใน session_state โดยตรง
        st.session_state.qt_items[i]['desc'] = cols[0].text_input(f"d_{i}", value=row['desc'], label_visibility="collapsed")
        st.session_state.qt_items[i]['qty'] = cols[1].number_input(f"q_{i}", value=row['qty'], min_value=0, label_visibility="collapsed")
        st.session_state.qt_items[i]['unit'] = cols[2].text_input(f"u_{i}", value=row['unit'], label_visibility="collapsed")
        st.session_state.qt_items[i]['price'] = cols[3].number_input(f"p_{i}", value=row['price'], min_value=0.0, format="%.2f", label_visibility="collapsed")
        
        # ปุ่มลบรายแถว (ถังขยะ)
        if cols[4].button("🗑️", key=f"del_{i}"):
            st.session_state.qt_items.pop(i)
            st.rerun()

    # 4. ปุ่มเพิ่มรายการ (+)
    if st.button("➕ เพิ่มรายการสินค้า", use_container_width=True):
        st.session_state.qt_items.append({"desc": "", "qty": 1, "unit": "Pcs", "price": 0.0})
        st.rerun()

    # 5. คำนวณยอดรวม (กรองเฉพาะแถวที่มี Description)
    final_items = [it for it in st.session_state.qt_items if it['desc'].strip() != ""]
    sub_total = sum(float(it['qty']) * float(it['price']) for it in final_items)
    
    st.markdown(f"### ยอดรวมสุทธิ: :blue[{sub_total:,.2f}] บาท")
##########################
    # 6. ปุ่มบันทึก (Supabase + PDF)
    if st.button("💾 บันทึกและดาวน์โหลด PDF", type="primary"):
        # เตรียมข้อมูลลูกค้า
        cust_code = selected_cust.split(" | ")[0]
        cust_row = cust_df[cust_df['cust_code'] == cust_code].iloc[0]
        cust_info = {
            "name": cust_row['cust_name'],
            "address": cust_row['address'],
            "contact": cust_row.get('contact_name', 'N/A')
        }
        
        # เตรียม Payload สำหรับ Supabase (รวมรายการสินค้า items_json เข้าไปด้วย)
        db_payload = {
            "qt_number": full_qt_id, 
            "cust_code": cust_code, 
            "date": str(qt_date), 
            "grand_total": float(sub_total), 
            "remark": remark, 
            "group": group,
            "items_json": final_items  # บันทึกรายการสินค้าเพื่อดึงมาทำ Rev ใหม่ได้
        }
        
        # --- ส่วนบันทึกข้อมูลเข้า Supabase ---
        try:
            response = requests.post(url_qt, json=db_payload, headers=headers)
            if response.status_code in [200, 201]:
                st.success(f"✅ บันทึกข้อมูล {full_qt_id} ลงระบบเรียบร้อยแล้ว!")
            else:
                st.error(f"❌ บันทึกไม่สำเร็จ! Error {response.status_code}: {response.text}")
        except Exception as e:
            st.error(f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ Database: {e}")
        
        # --- ส่วนการสร้างและดาวน์โหลด PDF ---
        try:
            # เตรียมข้อมูลสำหรับส่งเข้าฟังก์ชัน generate_pdf
            pdf_payload = {
                "qt_number": full_qt_id, 
                "date": str(qt_date), 
                "grand_total": sub_total, 
                "remark": remark
            }
            
            # เรียกใช้ฟังก์ชัน generate_pdf เดิมที่คุณมี
            pdf_bytes = generate_pdf(pdf_payload, final_items, cust_info)
            
            # แสดงปุ่มดาวน์โหลด
            st.download_button(
                label=f"📥 ดาวน์โหลดเอกสาร {full_qt_id}.pdf",
                data=pdf_bytes, 
                file_name=f"{full_qt_id}.pdf",
                mime="application/pdf"
            )
            st.balloons() # ฉลองความสำเร็จหน่อย!
        except Exception as e:
            st.error(f"⚠️ เกิดข้อผิดพลาดในการสร้างไฟล์ PDF: {e}")