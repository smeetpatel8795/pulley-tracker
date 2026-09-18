import pandas as pd
import streamlit as st
import os
import io
from datetime import date, datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Pulley Manufacturing ERP", layout="wide")

# ----------------------------------------------------
# COMPANY LOGO CONFIGURATION
# ----------------------------------------------------
# Replace 'logo.png' with the actual path or filename of your company logo (PNG/JPG format)
COMPANY_LOGO_PATH = "logo.png"

def render_sidebar_logo():
    if os.path.exists(COMPANY_LOGO_PATH):
        st.sidebar.image(COMPANY_LOGO_PATH, use_column_width=True)

def get_logo_image(width=120, height=50):
    """Returns a ReportLab Image object if the logo exists, otherwise None."""
    if os.path.exists(COMPANY_LOGO_PATH):
        try:
            return RLImage(COMPANY_LOGO_PATH, width=width, height=height)
        except Exception:
            return None
    return None

# File Paths for CSV Persistence
MASTER_ITEM_FILE = "master_items.csv"
FOUNDRY_FILE = "master_foundries.csv"
PO_FILE = "purchase_orders.csv"
CHALLAN_FILE = "challan_entries.csv"
PIG_IRON_FILE = "pig_iron_entries.csv"

# ----------------------------------------------------
# DATA INITIALIZATION
# ----------------------------------------------------
def load_data():
    if os.path.exists(MASTER_ITEM_FILE):
        item_df = pd.read_csv(MASTER_ITEM_FILE)
    else:
        item_df = pd.DataFrame(columns=["Item Size", "Pattern Type", "Standard Weight per Pc (kg)"])

    if os.path.exists(FOUNDRY_FILE):
        foundry_df = pd.read_csv(FOUNDRY_FILE)
    else:
        foundry_df = pd.DataFrame(columns=[
            "Foundry Name", "GST ID", "Address", "Contact Person", "Mobile Number", "Opening Pig Iron Balance (kg)"
        ])

    if os.path.exists(PO_FILE):
        po_df = pd.read_csv(PO_FILE)
    else:
        po_df = pd.DataFrame(columns=[
            "PO Date", "PO No", "Foundry Name", "Item Size", "Ordered Qty (Pcs)",
            "Expected Total Weight (kg)", "Rate per kg (INR)", "GST Rate (%)", "Total Cost (INR)",
            "Received Qty (Pcs)", "Pending Qty (Pcs)", "Status", "Completion Date"
        ])

    if os.path.exists(CHALLAN_FILE):
        challan_df = pd.read_csv(CHALLAN_FILE)
    else:
        challan_df = pd.DataFrame(columns=[
            "Date", "Challan No", "PO No", "Foundry Name", "Item Size", 
            "Qty (Pcs)", "Actual Weight (kg)", "Expected Weight (kg)", 
            "Weight Variation (kg)", "Status"
        ])

    if os.path.exists(PIG_IRON_FILE):
        pig_iron_df = pd.read_csv(PIG_IRON_FILE)
    else:
        pig_iron_df = pd.DataFrame(columns=[
            "Date", "Vendor Name", "Bill/Invoice No", "Vehicle No", 
            "Pig Iron Weight (kg)", "Qty", "Unloaded Foundry", 
            "SGST (%)", "CGST (%)", "IGST (%)", "Round Off", "Total Amount (INR)"
        ])

    return item_df, foundry_df, po_df, challan_df, pig_iron_df

item_df, foundry_df, po_df, challan_df, pig_iron_df = load_data()

if "current_po_items" not in st.session_state:
    st.session_state.current_po_items = []
if "current_challan_items" not in st.session_state:
    st.session_state.current_challan_items = []

# ----------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------
def get_foundry_pig_iron_balance(foundry_name):
    f_row = foundry_df[foundry_df["Foundry Name"] == foundry_name]
    opening = f_row["Opening Pig Iron Balance (kg)"].values[0] if not f_row.empty else 0.0
    
    inward = pig_iron_df[pig_iron_df["Unloaded Foundry"] == foundry_name]["Pig Iron Weight (kg)"].sum()
    consumed = challan_df[challan_df["Foundry Name"] == foundry_name]["Actual Weight (kg)"].sum()
    
    return float(opening + inward - consumed)

def generate_po_pdf(po_number, po_items_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1)
    
    # Add Company Logo if available
    logo_img = get_logo_image(width=100, height=45)
    if logo_img:
        header_table_data = [[logo_img, Paragraph("<b>PURCHASE ORDER</b>", header_style)]]
        header_table = Table(header_table_data, colWidths=[120, 410])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(header_table)
    else:
        story.append(Paragraph("PURCHASE ORDER", header_style))

    story.append(Spacer(1, 15))
    
    first_row = po_items_df.iloc[0]
    info_text = f"<b>PO Date:</b> {first_row['PO Date']} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>PO Number:</b> {po_number}<br/><b>To Foundry:</b> {first_row['Foundry Name']}"
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 15))

    table_data = [["Item Size", "Ordered Qty (Pcs)", "Expected Wt (kg)", "Rate/kg (₹)", "GST %", "Total Cost (₹)"]]
    for _, row in po_items_df.iterrows():
        table_data.append([
            str(row["Item Size"]),
            str(int(row["Ordered Qty (Pcs)"])),
            f"{row['Expected Total Weight (kg)']:.2f}",
            f"{row['Rate per kg (INR)']:.2f}",
            f"{row['GST Rate (%)']:.1f}%",
            f"{row['Total Cost (INR)']:.2f}"
        ])

    grand_total = po_items_df["Total Cost (INR)"].sum()
    table_data.append(["Grand Total", "", "", "", "", f"₹ {grand_total:,.2f}"])

    po_table = Table(table_data, colWidths=[150, 75, 80, 65, 50, 90])
    po_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F3F4F6')),
    ]))
    
    story.append(po_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_pig_iron_statement_pdf(foundry_name, start_d, end_d, ledger_df, opening_bal, total_in, total_out, final_bal):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, leading=14, alignment=1)

    logo_img = get_logo_image(width=100, height=45)
    if logo_img:
        title_p = Paragraph(f"<b>PIG IRON STATEMENT: {foundry_name.upper()}</b><br/><font size=9>Period: {start_d} to {end_d}</font>", title_style)
        header_table = Table([[logo_img, title_p]], colWidths=[120, 410])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        story.append(header_table)
    else:
        story.append(Paragraph(f"PIG IRON STATEMENT: {foundry_name.upper()}", title_style))
        story.append(Paragraph(f"Period: {start_d} to {end_d}", sub_style))

    story.append(Spacer(1, 15))

    summary_data = [
        ["Opening Balance (kg)", "Total Inward (kg)", "Total Consumed (kg)", "Closing Balance (kg)"],
        [f"{opening_bal:.2f}", f"{total_in:.2f}", f"{total_out:.2f}", f"{final_bal:.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[120, 120, 120, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F2937')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F9FAFB')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Detailed Transaction Ledger:</b>", styles['Normal']))
    story.append(Spacer(1, 8))

    ledger_table_data = [["Date", "Type", "Reference / Bill", "Inward (+kg)", "Outward (-kg)", "Balance (kg)"]]
    for _, row in ledger_df.iterrows():
        ledger_table_data.append([
            str(row["Date"]),
            str(row["Type"]),
            str(row["Reference"]),
            f"{row['Inward (kg)']:.2f}" if row['Inward (kg)'] > 0 else "-",
            f"{row['Outward (kg)']:.2f}" if row['Outward (kg)'] > 0 else "-",
            f"{row['Balance (kg)']:.2f}"
        ])

    ledger_table = Table(ledger_table_data, colWidths=[70, 90, 110, 75, 75, 80])
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#374151')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(ledger_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------------------------------------------------
# APPLICATION INTERFACE & NAVIGATION
# ----------------------------------------------------
render_sidebar_logo()

st.title("Pulley Manufacturing & Foundry Management System")

st.sidebar.title("Navigation")
menu = st.sidebar.radio("Go to Section:", [
    "📊 Executive Dashboard & Reports",
    "📦 Item Master Data",
    "🏭 Foundry Master Data",
    "🐷 Pig Iron Raw Material Inward",
    "📝 Purchase Order Generator",
    "🚚 Challan Entry (Incoming Castings)",
    "📄 Pig Iron Foundry Statement & PDF",
    "🔍 Item Size Reports & History"
])

# ----------------------------------------------------
# 1. EXECUTIVE DASHBOARD & REPORTS
# ----------------------------------------------------
if menu == "📊 Executive Dashboard & Reports":
    st.header("Executive Operational Dashboard")

    now = datetime.now()
    current_year = now.year
    current_month = now.month
    current_month_str = now.strftime('%B %Y')

    # Calculate Total Pig Iron Stock On Hand (All Foundries)
    total_opening_pig = foundry_df["Opening Pig Iron Balance (kg)"].sum() if not foundry_df.empty else 0.0
    total_inward_pig = pig_iron_df["Pig Iron Weight (kg)"].sum() if not pig_iron_df.empty else 0.0
    total_consumed_pig = challan_df["Actual Weight (kg)"].sum() if not challan_df.empty else 0.0
    total_pig_on_hand = total_opening_pig + total_inward_pig - total_consumed_pig

    # Calculate Current Month Casting Inward Purchase
    if not challan_df.empty:
        temp_ch = challan_df.copy()
        temp_ch["Date_dt"] = pd.to_datetime(temp_ch["Date"], errors='coerce')
        cur_m_challan = temp_ch[(temp_ch["Date_dt"].dt.year == current_year) & (temp_ch["Date_dt"].dt.month == current_month)]
        cur_m_casting_weight = cur_m_challan["Actual Weight (kg)"].sum()
    else:
        cur_m_casting_weight = 0.0

    # KPI Top Cards Row 1
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Pig Iron On Hand", f"{total_pig_on_hand:,.2f} kg")
    with kpi2:
        st.metric(f"Casting Inward ({current_month_str})", f"{cur_m_casting_weight:,.2f} kg")
    with kpi3:
        active_pos = po_df[po_df["Status"] == "OPEN"]["PO No"].nunique() if not po_df.empty else 0
        st.metric("Active Open POs", active_pos)
    with kpi4:
        total_var = challan_df["Weight Variation (kg)"].sum() if not challan_df.empty else 0.0
        st.metric("Total Weight Variance Loss", f"{total_var:+.2f} kg", delta_color="inverse" if total_var > 0 else "normal")

    st.markdown("---")

    # DASHBOARD VISUAL ANALYTICS & CHARTS
    st.subheader("📈 Real-Time Material & Casting Analytics")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown(f"**Foundry-wise Casting Inward — {current_month_str} (in KGs)**")
        if not challan_df.empty:
            temp_ch = challan_df.copy()
            temp_ch["Date_dt"] = pd.to_datetime(temp_ch["Date"], errors='coerce')
            cur_month_df = temp_ch[(temp_ch["Date_dt"].dt.year == current_year) & (temp_ch["Date_dt"].dt.month == current_month)]
            
            if not cur_month_df.empty:
                f_cur_m = cur_month_df.groupby("Foundry Name")["Actual Weight (kg)"].sum().reset_index()
                f_cur_m.columns = ["Foundry Name", "Inward Weight (kg)"]
                st.bar_chart(f_cur_m.set_index("Foundry Name"))
            else:
                st.info(f"No casting arrivals recorded in {current_month_str} yet.")
        else:
            st.info("No casting challans entered yet.")

    with col_chart2:
        st.markdown(f"**Current Year Pig Iron Purchases Month-wise ({current_year}) (in KGs)**")
        if not pig_iron_df.empty:
            temp_pig = pig_iron_df.copy()
            temp_pig["Date_dt"] = pd.to_datetime(temp_pig["Date"], errors='coerce')
            cur_yr_pig = temp_pig[temp_pig["Date_dt"].dt.year == current_year]
            
            if not cur_yr_pig.empty:
                cur_yr_pig["Month_Num"] = cur_yr_pig["Date_dt"].dt.month
                cur_yr_pig["Month_Name"] = cur_yr_pig["Date_dt"].dt.strftime('%b')
                pig_m_group = cur_yr_pig.groupby(["Month_Num", "Month_Name"])["Pig Iron Weight (kg)"].sum().reset_index()
                pig_m_group = pig_m_group.sort_values("Month_Num")
                st.bar_chart(pig_m_group.set_index("Month_Name")["Pig Iron Weight (kg)"])
            else:
                st.info(f"No Pig Iron purchases recorded in {current_year} yet.")
        else:
            st.info("No Pig Iron inward records entered yet.")

    st.markdown("---")

    # Full Width Chart: Current Year Total Casting Inward Monthly Trend
    st.markdown(f"**Current Year Total Casting Inward Monthly Trend ({current_year}) (in KGs)**")
    if not challan_df.empty:
        temp_ch = challan_df.copy()
        temp_ch["Date_dt"] = pd.to_datetime(temp_ch["Date"], errors='coerce')
        cur_yr_ch = temp_ch[temp_ch["Date_dt"].dt.year == current_year]

        if not cur_yr_ch.empty:
            cur_yr_ch["Month_Num"] = cur_yr_ch["Date_dt"].dt.month
            cur_yr_ch["Month_Name"] = cur_yr_ch["Date_dt"].dt.strftime('%b')
            ch_m_group = cur_yr_ch.groupby(["Month_Num", "Month_Name"])["Actual Weight (kg)"].sum().reset_index()
            ch_m_group = ch_m_group.sort_values("Month_Num")
            st.line_chart(ch_m_group.set_index("Month_Name")["Actual Weight (kg)"])
        else:
            st.info(f"No casting receipts recorded in {current_year} yet.")
    else:
        st.info("No casting challans entered yet.")

    st.markdown("---")

    # Tables Tab View
    tab_d1, tab_d2, tab_d3 = st.tabs(["🐷 Foundry Pig Iron Stocks", "📋 Pending Orders by Foundry", "📐 Size-Wise Pending Orders"])

    with tab_d1:
        st.subheader("Foundry Pig Iron Stock Balances")
        if foundry_df.empty:
            st.info("No foundries registered yet.")
        else:
            pig_summary = []
            for _, f_row in foundry_df.iterrows():
                fname = f_row["Foundry Name"]
                bal = get_foundry_pig_iron_balance(fname)
                pig_summary.append({
                    "Foundry Name": fname,
                    "Opening Balance (kg)": f_row["Opening Pig Iron Balance (kg)"],
                    "Inward Received (kg)": pig_iron_df[pig_iron_df["Unloaded Foundry"] == fname]["Pig Iron Weight (kg)"].sum(),
                    "Castings Consumed (kg)": challan_df[challan_df["Foundry Name"] == fname]["Actual Weight (kg)"].sum(),
                    "Current Pig Iron Balance (kg)": bal
                })
            st.dataframe(pd.DataFrame(pig_summary), use_container_width=True)

    with tab_d2:
        st.subheader("Pending Orders Summary by Foundry")
        if po_df.empty:
            st.info("No Purchase Orders created yet.")
        else:
            f_group = po_df.groupby("Foundry Name").agg({
                "Ordered Qty (Pcs)": "sum",
                "Received Qty (Pcs)": "sum",
                "Pending Qty (Pcs)": "sum"
            }).reset_index()
            st.dataframe(f_group, use_container_width=True)

    with tab_d3:
        st.subheader("Pending Orders Summary by Item Size")
        if po_df.empty:
            st.info("No Purchase Orders created yet.")
        else:
            s_group = po_df.groupby("Item Size").agg({
                "Ordered Qty (Pcs)": "sum",
                "Received Qty (Pcs)": "sum",
                "Pending Qty (Pcs)": "sum"
            }).reset_index()
            st.dataframe(s_group, use_container_width=True)

# ----------------------------------------------------
# 2. ITEM MASTER DATA
# ----------------------------------------------------
elif menu == "📦 Item Master Data":
    st.header("Item Master Data Management")
    tab1, tab2 = st.tabs(["📤 Bulk Upload (Excel/CSV)", "➕ Add Single Item"])

    with tab1:
        st.subheader("Bulk Import Pulley Master Data")
        uploaded_file = st.file_uploader("Upload CSV or XLSX file", type=["csv", "xlsx"])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    new_items = pd.read_csv(uploaded_file)
                else:
                    new_items = pd.read_excel(uploaded_file)
                
                req_cols = ["Item Size", "Pattern Type", "Standard Weight per Pc (kg)"]
                if all(c in new_items.columns for c in req_cols):
                    st.dataframe(new_items.head(), use_container_width=True)
                    if st.button("Save Uploaded Items"):
                        item_df = pd.concat([item_df, new_items[req_cols]], ignore_index=True)
                        item_df = item_df.drop_duplicates(subset=["Item Size"], keep="last")
                        item_df.to_csv(MASTER_ITEM_FILE, index=False)
                        st.success("Item Master successfully updated!")
                        st.experimental_rerun()
                else:
                    st.error(f"File must contain columns: {req_cols}")
            except Exception as e:
                st.error(f"Error loading file: {e}")

    with tab2:
        st.subheader("Add / Update Item")
        with st.form("single_item_form"):
            i_size = st.text_input("Item Size (e.g. 10 inch C-Section 3 Groove)")
            i_pattern = st.text_input("Pattern Type / Mould Ref")
            i_weight = st.number_input("Standard Weight per Piece (kg)", min_value=0.01, step=0.01)
            submit_item = st.form_submit_button("Save Item Master")

            if submit_item:
                if i_size.strip() != "":
                    if i_size in item_df["Item Size"].values:
                        item_df.loc[item_df["Item Size"] == i_size, ["Pattern Type", "Standard Weight per Pc (kg)"]] = [i_pattern, i_weight]
                    else:
                        new_row = pd.DataFrame([{"Item Size": i_size, "Pattern Type": i_pattern, "Standard Weight per Pc (kg)": i_weight}])
                        item_df = pd.concat([item_df, new_row], ignore_index=True)
                    item_df.to_csv(MASTER_ITEM_FILE, index=False)
                    st.success(f"Saved {i_size} successfully!")
                    st.experimental_rerun()

    st.markdown("---")
    st.subheader("Current Master Inventory List")
    st.dataframe(item_df, use_container_width=True)

# ----------------------------------------------------
# 3. FOUNDRY MASTER DATA
# ----------------------------------------------------
elif menu == "🏭 Foundry Master Data":
    st.header("Foundry Master Register")
    with st.form("foundry_form"):
        f_name = st.text_input("Foundry Name")
        f_gst = st.text_input("GST ID")
        f_address = st.text_area("Address")
        col1, col2 = st.columns(2)
        with col1:
            f_contact = st.text_input("Contact Person")
        with col2:
            f_mobile = st.text_input("Mobile Number")
        f_opening_pig = st.number_input("Opening Pig Iron Balance (kg)", min_value=0.0, step=1.0)

        submit_f = st.form_submit_button("Save Foundry Master")
        if submit_f:
            if f_name.strip() != "":
                if f_name in foundry_df["Foundry Name"].values:
                    foundry_df.loc[foundry_df["Foundry Name"] == f_name, :] = [f_name, f_gst, f_address, f_contact, f_mobile, f_opening_pig]
                else:
                    new_f = pd.DataFrame([{"Foundry Name": f_name, "GST ID": f_gst, "Address": f_address, "Contact Person": f_contact, "Mobile Number": f_mobile, "Opening Pig Iron Balance (kg)": f_opening_pig}])
                    foundry_df = pd.concat([foundry_df, new_f], ignore_index=True)
                foundry_df.to_csv(FOUNDRY_FILE, index=False)
                st.success(f"Foundry {f_name} saved successfully!")
                st.experimental_rerun()

    st.markdown("---")
    st.subheader("Registered Foundries")
    st.dataframe(foundry_df, use_container_width=True)

# ----------------------------------------------------
# 4. PIG IRON RAW MATERIAL INWARD
# ----------------------------------------------------
elif menu == "🐷 Pig Iron Raw Material Inward":
    st.header("Pig Iron Vendor Delivery Inward")
    
    if foundry_df.empty:
        st.warning("Please register at least one Foundry in 'Foundry Master Data' first.")
    else:
        with st.form("pig_iron_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                p_date = st.date_input("Inward Date")
                p_vendor = st.text_input("Vendor Name")
            with c2:
                p_bill = st.text_input("Bill / Invoice No.")
                p_vehicle = st.text_input("Vehicle No.")
            with c3:
                p_foundry = st.selectbox("Unloaded at Foundry", foundry_df["Foundry Name"].unique())
                p_weight = st.number_input("Pig Iron Weight (kg)", min_value=0.01, step=0.1)

            st.subheader("Taxation & Cost Details")
            tc1, tc2, tc3, tc4 = st.columns(4)
            with tc1:
                p_qty = st.number_input("Qty (Bags/Bundles)", min_value=1, step=1)
                p_sgst = st.number_input("SGST (%)", min_value=0.0, step=0.5)
            with tc2:
                p_cgst = st.number_input("CGST (%)", min_value=0.0, step=0.5)
            with tc3:
                p_igst = st.number_input("IGST (%)", min_value=0.0, step=0.5)
            with tc4:
                p_ro = st.number_input("Round Off (R/O)", step=0.01)
                p_total = st.number_input("Total Amount (INR)", min_value=0.0, step=1.0)

            submit_pig = st.form_submit_button("Save Pig Iron Entry")
            if submit_pig:
                new_pig = {
                    "Date": str(p_date), "Vendor Name": p_vendor, "Bill/Invoice No": p_bill,
                    "Vehicle No": p_vehicle, "Pig Iron Weight (kg)": p_weight, "Qty": p_qty,
                    "Unloaded Foundry": p_foundry, "SGST (%)": p_sgst, "CGST (%)": p_cgst,
                    "IGST (%)": p_igst, "Round Off": p_ro, "Total Amount (INR)": p_total
                }
                pig_iron_df = pd.concat([pig_iron_df, pd.DataFrame([new_pig])], ignore_index=True)
                pig_iron_df.to_csv(PIG_IRON_FILE, index=False)
                st.success(f"Pig Iron entry recorded! Added {p_weight} kg to {p_foundry}'s stock balance.")
                st.experimental_rerun()

        st.markdown("---")
        st.subheader("Recent Pig Iron Inward Entries")
        st.dataframe(pig_iron_df, use_container_width=True)

# ----------------------------------------------------
# 5. PURCHASE ORDER GENERATOR
# ----------------------------------------------------
elif menu == "📝 Purchase Order Generator":
    st.header("Generate Purchase Order")
    if item_df.empty or foundry_df.empty:
        st.warning("Ensure both Item Master and Foundry Master have entries.")
    else:
        st.subheader("1. Header Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            po_date = st.date_input("PO Date")
        with col2:
            po_no = st.text_input("PO Number")
        with col3:
            po_foundry = st.selectbox("Select Foundry", foundry_df["Foundry Name"].unique())

        st.markdown("---")
        st.subheader("2. Add Order Items")
        ic1, ic2, ic3, ic4 = st.columns([3, 2, 2, 2])
        with ic1:
            po_item = st.selectbox("Select Item Size", item_df["Item Size"].unique())
        with ic2:
            po_qty = st.number_input("Order Qty (Pcs)", min_value=1, step=1)
        with ic3:
            po_rate = st.number_input("Rate per kg (INR)", min_value=0.0, step=0.5)
        with ic4:
            po_gst = st.number_input("GST Rate (%)", value=18.0, step=1.0)

        if st.button("➕ Add Item to PO"):
            std_w = item_df.loc[item_df["Item Size"] == po_item, "Standard Weight per Pc (kg)"].values[0]
            exp_w = round(po_qty * std_w, 2)
            base_cost = exp_w * po_rate
            total_cost = base_cost * (1 + (po_gst / 100.0))

            po_entry = {
                "Item Size": po_item, "Ordered Qty (Pcs)": po_qty,
                "Expected Total Weight (kg)": exp_w, "Rate per kg (INR)": po_rate,
                "GST Rate (%)": po_gst, "Total Cost (INR)": round(total_cost, 2)
            }
            st.session_state.current_po_items.append(po_entry)
            st.success(f"Added {po_item} to order list.")

        if st.session_state.current_po_items:
            st.subheader("Items in Current Purchase Order")
            temp_po_df = pd.DataFrame(st.session_state.current_po_items)
            st.dataframe(temp_po_df, use_container_width=True)

            if st.button("💾 Save Purchase Order", type="primary"):
                if not po_no:
                    st.error("Please enter a valid PO Number.")
                else:
                    new_pos = []
                    for itm in st.session_state.current_po_items:
                        full_po = {
                            "PO Date": str(po_date), "PO No": po_no, "Foundry Name": po_foundry,
                            **itm, "Received Qty (Pcs)": 0, "Pending Qty (Pcs)": itm["Ordered Qty (Pcs)"],
                            "Status": "OPEN", "Completion Date": "-"
                        }
                        new_pos.append(full_po)
                    po_df = pd.concat([po_df, pd.DataFrame(new_pos)], ignore_index=True)
                    po_df.to_csv(PO_FILE, index=False)
                    st.session_state.current_po_items = []
                    st.success(f"Purchase Order {po_no} saved successfully!")
                    st.experimental_rerun()

        st.markdown("---")
        st.subheader("Purchase Order History & Print PDF")
        if not po_df.empty:
            sel_po = st.selectbox("Select PO to Print PDF", po_df["PO No"].unique())
            single_po_df = po_df[po_df["PO No"] == sel_po]
            st.dataframe(single_po_df, use_container_width=True)

            pdf_file = generate_po_pdf(sel_po, single_po_df)
            st.download_button(
                label="📄 Download Purchase Order PDF",
                data=pdf_file,
                file_name=f"PO_{sel_po}.pdf",
                mime="application/pdf"
            )

# ----------------------------------------------------
# 6. CHALLAN ENTRY (INCOMING CASTINGS)
# ----------------------------------------------------
elif menu == "🚚 Challan Entry (Incoming Castings)":
    st.header("Incoming Castings Challan Receipt")
    open_pos = po_df[po_df["Status"] == "OPEN"]
    
    if open_pos.empty:
        st.info("No Open Purchase Orders available.")
    else:
        st.subheader("1. Challan & Foundry Info")
        c1, c2, c3 = st.columns(3)
        with c1:
            ch_date = st.date_input("Challan Date")
            ch_no = st.text_input("Challan No.")
        with c2:
            ch_po = st.selectbox("Select Active PO No.", open_pos["PO No"].unique())
            f_from_po = open_pos[open_pos["PO No"] == ch_po]["Foundry Name"].iloc[0]
            st.text_input("Foundry Name", value=f_from_po, disabled=True)
        with c3:
            curr_pig_bal = get_foundry_pig_iron_balance(f_from_po)
            st.metric("Foundry Pig Iron Balance", f"{curr_pig_bal:.2f} kg")

        st.markdown("---")
        st.subheader("2. Receive Items Against PO")
        po_items_avail = open_pos[open_pos["PO No"] == ch_po]["Item Size"].unique()
        
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        with col1:
            ch_item = st.selectbox("Item Size", po_items_avail)
        with col2:
            ch_qty = st.number_input("Qty Received (Pcs)", min_value=1, step=1)
        with col3:
            ch_actual_w = st.number_input("Actual Received Weight (kg)", min_value=0.01, step=0.1)
        with col4:
            st.write(" ")
            st.write(" ")
            add_ch_item = st.button("➕ Add to Challan")

        if add_ch_item:
            std_w = item_df.loc[item_df["Item Size"] == ch_item, "Standard Weight per Pc (kg)"].values[0]
            exp_w = round(ch_qty * std_w, 2)
            var_w = round(ch_actual_w - exp_w, 2)
            status_w = "OVERWEIGHT (Loss)" if var_w > 0 else ("UNDERWEIGHT (Gain)" if var_w < 0 else "EXACT MATCH")

            ch_entry = {
                "Item Size": ch_item, "Qty (Pcs)": ch_qty, "Actual Weight (kg)": ch_actual_w,
                "Expected Weight (kg)": exp_w, "Weight Variation (kg)": var_w, "Status": status_w
            }
            st.session_state.current_challan_items.append(ch_entry)
            st.success(f"Added {ch_item} to receipt list.")

        if st.session_state.current_challan_items:
            st.subheader("Current Receipt Items")
            temp_ch_df = pd.DataFrame(st.session_state.current_challan_items)
            st.dataframe(temp_ch_df, use_container_width=True)

            if st.button("💾 Process & Save Challan", type="primary"):
                if not ch_no:
                    st.error("Please enter a valid Challan Number.")
                else:
                    new_ch_rows = []
                    for row in st.session_state.current_challan_items:
                        full_ch = {
                            "Date": str(ch_date), "Challan No": ch_no, "PO No": ch_po,
                            "Foundry Name": f_from_po, **row
                        }
                        new_ch_rows.append(full_ch)

                        match = (po_df["PO No"] == ch_po) & (po_df["Item Size"] == row["Item Size"])
                        if match.any():
                            curr_rec = po_df.loc[match, "Received Qty (Pcs)"].values[0]
                            curr_ord = po_df.loc[match, "Ordered Qty (Pcs)"].values[0]
                            new_rec = curr_rec + row["Qty (Pcs)"]
                            new_pend = max(0, curr_ord - new_rec)

                            po_df.loc[match, "Received Qty (Pcs)"] = new_rec
                            po_df.loc[match, "Pending Qty (Pcs)"] = new_pend

                            if new_pend == 0:
                                po_df.loc[match, "Status"] = "COMPLETED"
                                po_df.loc[match, "Completion Date"] = str(ch_date)

                    challan_df = pd.concat([challan_df, pd.DataFrame(new_ch_rows)], ignore_index=True)
                    challan_df.to_csv(CHALLAN_FILE, index=False)
                    po_df.to_csv(PO_FILE, index=False)

                    st.session_state.current_challan_items = []
                    st.success(f"Challan {ch_no} processed. PO balances updated successfully!")
                    st.experimental_rerun()

# ----------------------------------------------------
# 7. PIG IRON FOUNDRY STATEMENT & PDF
# ----------------------------------------------------
elif menu == "📄 Pig Iron Foundry Statement & PDF":
    st.header("Foundry Pig Iron Statement & Running Ledger")

    if foundry_df.empty:
        st.info("No foundries registered.")
    else:
        sel_f = st.selectbox("Select Foundry", foundry_df["Foundry Name"].unique())
        date_opt = st.radio("Date Filter", ["All Time (Start to Date)", "Custom Date Range"])

        if date_opt == "Custom Date Range":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", date(2025, 1, 1))
            with col2:
                end_date = st.date_input("End Date", date.today())
        else:
            start_date = date(2020, 1, 1)
            end_date = date.today()

        opening = foundry_df[foundry_df["Foundry Name"] == sel_f]["Opening Pig Iron Balance (kg)"].values[0]
        
        ledger_entries = []
        f_pigs = pig_iron_df[pig_iron_df["Unloaded Foundry"] == sel_f]
        for _, r in f_pigs.iterrows():
            ledger_entries.append({
                "Date": r["Date"], "Type": "Pig Iron Inward", "Reference": f"Bill: {r['Bill/Invoice No']}",
                "Inward (kg)": r["Pig Iron Weight (kg)"], "Outward (kg)": 0.0
            })
        f_casts = challan_df[challan_df["Foundry Name"] == sel_f]
        for _, r in f_casts.iterrows():
            ledger_entries.append({
                "Date": r["Date"], "Type": "Casting Consumed", "Reference": f"Challan: {r['Challan No']}",
                "Inward (kg)": 0.0, "Outward (kg)": r["Actual Weight (kg)"]
            })

        ledger_df = pd.DataFrame(ledger_entries)
        if not ledger_df.empty:
            ledger_df["Date"] = pd.to_datetime(ledger_df["Date"])
            ledger_df = ledger_df.sort_values("Date").reset_index(drop=True)

            bal = opening
            running_bals = []
            for _, r in ledger_df.iterrows():
                bal += r["Inward (kg)"] - r["Outward (kg)"]
                running_bals.append(bal)
            ledger_df["Balance (kg)"] = running_bals
            ledger_df["Date"] = ledger_df["Date"].dt.strftime('%Y-%m-%d')

            mask = (pd.to_datetime(ledger_df["Date"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(ledger_df["Date"]) <= pd.to_datetime(end_date))
            filtered_ledger = ledger_df[mask]

            st.dataframe(filtered_ledger, use_container_width=True)

            tot_in = filtered_ledger["Inward (kg)"].sum()
            tot_out = filtered_ledger["Outward (kg)"].sum()
            final_b = filtered_ledger["Balance (kg)"].iloc[-1] if not filtered_ledger.empty else opening

            pdf_statement = generate_pig_iron_statement_pdf(sel_f, str(start_date), str(end_date), filtered_ledger, opening, tot_in, tot_out, final_b)
            st.download_button(
                label="📄 Download Statement PDF",
                data=pdf_statement,
                file_name=f"PigIron_Statement_{sel_f}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("No transaction history available for this foundry.")

# ----------------------------------------------------
# 8. ITEM SIZE REPORTS & HISTORY
# ----------------------------------------------------
elif menu == "🔍 Item Size Reports & History":
    st.header("Item Size Inspection & History")
    
    if item_df.empty:
        st.info("No items in master data.")
    else:
        sel_size = st.selectbox("Select Pulley Size to Inspect", item_df["Item Size"].unique())

        tab_s1, tab_s2 = st.tabs(["🚚 Casting Receipt History", "📝 Purchase Order Timeline"])

        with tab_s1:
            st.subheader(f"Casting Arrivals for {sel_size}")
            size_challans = challan_df[challan_df["Item Size"] == sel_size]
            if size_challans.empty:
                st.info("No casting receipts recorded for this size.")
            else:
                st.dataframe(size_challans, use_container_width=True)
                
                tot_p = size_challans["Qty (Pcs)"].sum()
                tot_w = size_challans["Actual Weight (kg)"].sum()
                net_v = size_challans["Weight Variation (kg)"].sum()

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Received Quantity", f"{tot_p} Pcs")
                c2.metric("Total Weight Received", f"{tot_w:.2f} kg")
                c3.metric("Net Weight Variation", f"{net_v:+.2f} kg", delta_color="inverse" if net_v > 0 else "normal")

        with tab_s2:
            st.subheader(f"PO Fulfillment Timeline for {sel_size}")
            size_pos = po_df[po_df["Item Size"] == sel_size]
            if size_pos.empty:
                st.info("No POs issued for this size.")
            else:
                st.dataframe(size_pos, use_container_width=True)
