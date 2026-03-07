import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

def show_sales_performance_report():
    st.subheader("📊 Sales Performance & Analysis (Multi-Year)")

    # --- 1. Filter UI ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 1])
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        with c1: 
            sel_year = st.selectbox("📅 Select Year", [2026, 2025], index=0, key="sr_year")
        with c2: 
            start_m = st.selectbox("📅 Start", months, index=0, key="sr_start")
        with c3: 
            default_end = min(date.today().month - 1, 11)
            end_m = st.selectbox("📅 End", months, index=default_end, key="sr_end")

    # --- 2. Load Data ---
    @st.cache_data(ttl=3600)
    def load_sales_data(year):
        links = {
            2025: "https://docs.google.com/spreadsheets/d/1BG7w4vkBCCN6LTpl6gtUJAfye-8emUL8R-W5oPky_Js/export?format=xlsx",
            2026: "https://docs.google.com/spreadsheets/d/1FgvIZue-HAcqx5AvZ_-H4Rq8U_mcCdOzNdWPt9g5Ufo/export?format=xlsx"
        }
        url = links.get(year)
        df = pd.read_excel(url, header=4)
        df['วันที่'] = pd.to_datetime(df['วันที่'], errors='coerce')
        df['ลูกค้า'] = df['ลูกค้า'].astype(str).str.strip()
        df['รหัสสินค้า'] = df['รหัสสินค้า'].astype(str).str.strip()
        return df

    try:
        invoices = load_sales_data(sel_year)
    except Exception as e:
        st.error(f"❌ Load Error: {e}")
        return

    # --- 3. Date Filter ---
    start_date = pd.to_datetime(f"{sel_year}-{months.index(start_m)+1}-01")
    end_date = (pd.to_datetime(f"{sel_year}-{months.index(end_m)+1}-01") + pd.offsets.MonthEnd(0))
    df_filtered = invoices[(invoices['วันที่'] >= start_date) & (invoices['วันที่'] <= end_date)].copy()

    # --- 4. Mold-DP Mapping & Calculation ---
    dp_mapping = {
        '5612603000A': 0, '5612603100A': 0,
        'T907055A': 0, 'Z0011377A': 16.67, 'Z0011378A': 16.38
    }
    
    df_filtered['Mold_DP_Value'] = df_filtered.apply(
        lambda x: (x['จำนวน'] if pd.notnull(x['จำนวน']) else 0) * dp_mapping.get(str(x['รหัสสินค้า']), 0), axis=1
    )

    # --- 5. Data Segmentation ---
    onesim_only_cust = ['วิพัด โนนแสง', 'ธนะพงษ์ แก้วมา', 'ที.จี.เวนดิ้ง แอนด์ โชว์เคส อินดัสทรีส์ จำกัด', 'ณัฐฐา ยาชูชีพ', 'ชนะชัย อิเลคทรอนิค รีไซเคิล จำกัด', 'บริษัท ศรจินดา สหกิจ จำกัด', 'บริษัท ผลาชีวะทรานสปอร์ต จำกัด', 'ผลาชีวะทรานสปอร์ต จำกัด']
    mold_specific_cust = ['จอยสัน-ทีโอเอ เซฟตี้ ซิสเต็มส์ จำกัด', 'มิโน่ (ไทยแลนด์) จำกัด', 'ยามาฮ่ามอเตอร์พาร์ทแมนูแฟคเจอริ่ง(ประเทศไทย) จำกัด', 'ไพโอเนียร์ มอเตอร์ จำกัด(มหาชน)']

    mask_mold = (
        (df_filtered['รหัสสินค้า'].str.startswith('M', na=False)) | 
        (df_filtered['รหัสสินค้า'].str.startswith('SIM', na=False)) |
        (df_filtered['ลูกค้า'].isin(mold_specific_cust))
    ) & (~df_filtered['ลูกค้า'].isin(onesim_only_cust))
    
    df_mold = df_filtered[mask_mold].copy()
    df_mass = df_filtered[(~mask_mold) & (~df_filtered['ลูกค้า'].isin(onesim_only_cust))].copy()
    
    # คำนวณยอดโอนค่า DP
    total_dp_transfer = df_mass['Mold_DP_Value'].sum()
    df_mass['Net_Sales'] = df_mass['มูลค่าสินค้า'] - df_mass['Mold_DP_Value']

    # --- 6. Render Tabs ---
    t_mass, t_mold, t_onesim = st.tabs(["🏭 MASS BU", "🏗️ Mold BU", "🎯 One-SIM Overall"])

    with t_mass:
        if sel_year == 2026:
            render_bu_comparison(df_mass, "MASS", start_m, end_m, sales_col='Net_Sales')
        
        st.markdown("### 📦 MASS BU Analysis (Net of Mold-DP)")
        st.warning(f"📉 ยอดหัก Mold-DP ออกจาก Mass: **{total_dp_transfer:,.2f} บาท**")
        
        # คืนค่าส่วน Metrics แยกกลุ่ม Valeo / Steel Bush / Other
        render_mass_dashboard(df_mass)

    with t_mold:
        if sel_year == 2026:
            render_bu_comparison(df_mold, "MOLD", start_m, end_m, extra_val=total_dp_transfer)
        
        st.markdown("### 🛠️ Mold BU Analysis")
        st.success(f"📈 ยอดรายได้เพิ่มจาก Mold-DP: **{total_dp_transfer:,.2f} บาท**")
        render_generic_content(df_mold, "Mold", "#E74C3C", extra_val=total_dp_transfer)

    with t_onesim:
        render_overall_onesim(df_filtered, sel_year, start_m, end_m)

# ==============================================================================
# UI COMPONENTS
# ==============================================================================

def render_bu_comparison(df_actual, bu_type, start_m, end_m, sales_col='มูลค่าสินค้า', extra_val=0):
    targets_2026 = {
        "MASS": {"Jan": 17520279, "Feb": 18718123, "Mar": 20303414, "Apr": 10623297, "May": 16241804, "Jun": 14252736, "Jul": 12732911, "Aug": 12155887, "Sep": 15147204, "Oct": 15909196, "Nov": 14742736, "Dec": 12283633},
        "MOLD": {"Jan": 5250000, "Feb": 1350000, "Mar": 1400000, "Apr": 1800000, "May": 4800000, "Jun": 5100000, "Jul": 6100000, "Aug": 7100000, "Sep": 7100000, "Oct": 7100000, "Nov": 7100000, "Dec": 5800000}
    }
    months_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    selected_months = months_list[months_list.index(start_m) : months_list.index(end_m) + 1]
    
    total_target = sum(targets_2026[bu_type][m] for m in selected_months)
    total_actual = df_actual[sales_col].sum() + extra_val
    achieved = (total_actual / total_target * 100) if total_target > 0 else 0
    
    with st.container(border=True):
        st.markdown(f"**🎯 {bu_type} Target Tracking (2026)**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Actual (Net)", f"{total_actual:,.0f}")
        c2.metric("Target", f"{total_target:,.0f}")
        c3.metric("% Achieved", f"{achieved:.1f}%", delta=f"{achieved-100:.1f}%")

def render_mass_dashboard(df):
    if df.empty:
        st.info("ไม่มีข้อมูล MASS")
        return

    # --- ส่วนการแบ่งกลุ่ม ---
    def categorize_mass(row):
        cust = str(row['ลูกค้า']).upper()
        sku = str(row['รหัสสินค้า']).upper()
        if 'VALEO' in cust: return 'Valeo Sales'
        elif 'SB-MECL' in sku: return 'Steel Bush'
        else: return 'Other Mass'
    
    df['Mass_Group'] = df.apply(categorize_mass, axis=1)

    # --- ส่วนการโชว์ Metrics รายกลุ่ม (Net Sales) ---
    m1, m2, m3 = st.columns(3)
    valeo_net = df[df['Mass_Group'] == 'Valeo Sales']['Net_Sales'].sum()
    sb_net = df[df['Mass_Group'] == 'Steel Bush']['Net_Sales'].sum()
    other_net = df[df['Mass_Group'] == 'Other Mass']['Net_Sales'].sum()

    m1.metric("Valeo Sales (Net)", f"{valeo_net:,.0f}")
    m2.metric("Steel Bush (Net)", f"{sb_net:,.0f}")
    m3.metric("Other Mass (Net)", f"{other_net:,.0f}")

    # --- กราฟและตาราง ---
    fig = px.pie(df, values='Net_Sales', names='Mass_Group', hole=0.4,
                 color_discrete_map={'Valeo Sales':'#1F618D', 'Steel Bush':'#2ECC71', 'Other Mass':'#F1C40F'})
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df[['วันที่', 'ลูกค้า', 'รหัสสินค้า', 'มูลค่าสินค้า', 'Mold_DP_Value', 'Net_Sales', 'Mass_Group']], 
                 use_container_width=True, hide_index=True)

def render_generic_content(df, title, color, extra_val=0):
    total_direct = df['มูลค่าสินค้า'].sum()
    total_combined = total_direct + extra_val
    c1, c2 = st.columns(2)
    c1.metric(f"Direct {title} Sales", f"{total_direct:,.0f}")
    c2.metric(f"Total {title} (+DP Income)", f"{total_combined:,.0f}")
    st.dataframe(df[['วันที่', 'ลูกค้า', 'รหัสสินค้า', 'มูลค่าสินค้า']], use_container_width=True, hide_index=True)

def render_overall_onesim(df, year, start_m, end_m):
    total_sales = df['มูลค่าสินค้า'].sum()
    
    if year == 2026:
        targets_2026 = {
            "MASS": {"Jan": 17520279, "Feb": 18718123, "Mar": 20303414, "Apr": 10623297, "May": 16241804, "Jun": 14252736, "Jul": 12732911, "Aug": 12155887, "Sep": 15147204, "Oct": 15909196, "Nov": 14742736, "Dec": 12283633},
            "MOLD": {"Jan": 5250000, "Feb": 1350000, "Mar": 1400000, "Apr": 1800000, "May": 4800000, "Jun": 5100000, "Jul": 6100000, "Aug": 7100000, "Sep": 7100000, "Oct": 7100000, "Nov": 7100000, "Dec": 5800000}
        }
        months_list = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        selected_months = months_list[months_list.index(start_m) : months_list.index(end_m) + 1]
        comb_target = sum(targets_2026["MASS"][m] + targets_2026["MOLD"][m] for m in selected_months)
        
        with st.container(border=True):
            st.markdown("**🎯 One-SIM Combined Target Tracking (2026)**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Actual", f"{total_sales:,.0f}")
            c2.metric("Total Target", f"{comb_target:,.0f}")
            c3.metric("% Achieved", f"{(total_sales/comb_target*100):.1f}%")

    st.info(f"💰 One-SIM Grand Total: **{total_sales:,.2f} บาท**")

    st.dataframe(df[['วันที่', 'ลูกค้า', 'รหัสสินค้า', 'มูลค่าสินค้า']], use_container_width=True, hide_index=True)

