import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, date
import io

# PDF Generation imports (ReportLab)
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(page_title="Pulley ERP - Weight, PO & Foundry Tracker", layout="wide")

# File Paths for Local Database Persistence
ITEM_MASTER_FILE = "item_master.csv"
FOUNDRY_MASTER_FILE = "foundry_master.csv"
PO_FILE = "purchase_orders.csv"
CHALLAN_FILE = "challan_entries.csv"

# --- DATA INITIALIZATION ---
def load_data():
    if os.path.exists(ITEM_MASTER_FILE):
        item_df = pd.read_csv(ITEM_MASTER_FILE)
    else:
        item_df = pd.DataFrame(columns=["Item Size", "Pattern Type", "Standard Weight per Pc (kg)"])

    if os.path.exists(FOUNDRY_MASTER_FILE):
        foundry_df = pd.read_csv(FOUNDRY_MASTER_FILE)
    else:
        foundry_df = pd.DataFrame(columns=["Foundry Name", "GST ID", "Address", "Contact Person", "Mobile", "Pig Iron Opening Balance (kg)"])

    if os.path.exists(PO_FILE):
        po_df = pd.read_csv(PO_FILE)
    else:
        po_df = pd.DataFrame(columns=[
            "PO No", "PO Date", "Foundry Name", "Item Size", "Ordered Qty (Pcs)", 
            "Std Weight per Pc (kg)", "Expected Total Weight (kg)", "Rate per Kg (Rs)", 
            "Total Amount (Rs)", "Recd Qty (Pcs)", "Pending Qty (Pcs)", "Status", "Completion Date"
        ])

    if os.path.exists(CHALLAN_FILE):
        challan_df = pd.read_csv(CHALLAN_FILE)
    else:
        challan_df = pd.DataFrame(columns=[
            "Challan Date", "Challan No", "PO No", "Foundry Name", "Item Size", 
            "Qty (Pcs)", "Actual Weight (kg)", "Expected Weight (kg)", 
            "Weight Variation (kg)", "Status"
        ])

    return item_df, foundry_df, po_df, challan_df

item_df, foundry_df, po_df, challan_df = load_data()

# Session State Initializations
if "po_basket" not in st.session_state:
    st.session_state.po_basket = []

if "challan_basket" not in st.session_state:
    st.session_state.challan_basket = []

st.title("🏭 Pulley Foundry & Weight Loss Management ERP")

menu = st.sidebar.radio("Navigation Menu", [
    "📊 Executive Dashboard",
    "📝 Masters (Item & Foundry)",
    "📑 Create Purchase Order",
    "🚚 Challan Entry against PO",
    "📈 Foundry Pending Reports & Timeline",
    "🔍 Item Size Specific Report"
])

# -----------------------------------------------------------------------------
# 1. EXECUTIVE DASHBOARD
# -----------------------------------------------------------------------------
if menu == "📊 Executive Dashboard":
    st.header("Factory Overview Dashboard")
    
    c1, c2, c3, c4 = st.columns(4)
    tot_pos = len(po_df["PO No"].unique()) if not po_df.empty else 0
    tot_foundries = len(foundry_df) if not foundry_df.empty else 0
    tot_items = len(item_df) if not item_df.empty else 0
    tot_weight_loss = challan_df["Weight Variation (kg)"].sum() if not challan_df.empty else 0.0

    c1.metric("Total Active Foundries", tot_foundries)
    c2.metric("Total Master Items", tot_items)
    c3.metric("Total POs Generated", tot_pos)
    c4.metric("Net Excess Weight Purchased (Loss)", f"{tot_weight_loss:+.2f} kg", 
              delta_color="inverse" if tot_weight_loss > 0 else "normal")

    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Overweight Loss by Foundry")
        if not challan_df.empty:
            loss_by_foundry = challan_df.groupby("Foundry Name")["Weight Variation (kg)"].sum().reset_index()
            st.dataframe(loss_by_foundry, use_container_width=True)
        else:
            st.info("No challan data recorded yet.")

    with col_b:
        st.subheader("Pending Orders Summary")
        if not po_df.empty:
            pending_summary = po_df.groupby("Foundry Name")[["Ordered Qty (Pcs)", "Pending Qty (Pcs)"]].sum().reset_index()
            st.dataframe(pending_summary, use_container_width=True)
        else:
            st.info("No PO data recorded yet.")

# -----------------------------------------------------------------------------
# 2. MASTERS MANAGEMENT
# -----------------------------------------------------------------------------
elif menu == "📝 Masters (Item & Foundry)":
    st.header("Master Data Management")
    m_tab1, m_tab2 = st.tabs(["📦 Item Master", "🏭 Foundry Master"])

    # ITEM MASTER
    with m_tab1:
        st.subheader("Manage Item Sizes & Reference Weights")
        upload_subtab, single_subtab = st.tabs(["📤 Bulk Upload (500+ Items)", "➕ Add/Edit Single Item"])

        with upload_subtab:
            st.info("Upload an Excel or CSV file containing columns: **Item Size**, **Pattern Type**, and **Standard Weight per Pc (kg)**")
            up_file = st.file_uploader("Choose Excel or CSV File", type=["csv", "xlsx"])
            if up_file:
                try:
                    df_up = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                    req_cols = ["Item Size", "Pattern Type", "Standard Weight per Pc (kg)"]
                    if all(c in df_up.columns for c in req_cols):
                        st.write("Preview of Uploaded Data:")
                        st.dataframe(df_up.head(10), use_container_width=True)
                        if st.button("Save All Items to Item Master"):
                            item_df = pd.concat([item_df, df_up[req_cols]], ignore_index=True)
                            item_df.drop_duplicates(subset=["Item Size"], keep="last", inplace=True)
                            item_df.to_csv(ITEM_MASTER_FILE, index=False)
                            st.success(f"Successfully saved {len(df_up)} items!")
                            st.rerun()
                    else:
                        st.error(f"Missing required columns. Please match: {req_cols}")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

        with single_subtab:
            with st.form("single_item_form"):
                item_size = st.text_input("Item Size (e.g., 6 inch C-Section 3 Groove)")
                pattern_type = st.selectbox("Pattern Type", ["CI Shell", "Aluminum", "Wooden", "Match Plate", "Other"])
                std_weight = st.number_input("Standard Weight per Piece (kg)", min_value=0.01, step=0.01)
                submit_item = st.form_submit_button("Save Item Master")

                if submit_item and item_size:
                    if item_size in item_df["Item Size"].values:
                        item_df.loc[item_df["Item Size"] == item_size, ["Pattern Type", "Standard Weight per Pc (kg)"]] = [pattern_type, std_weight]
                    else:
                        new_row = pd.DataFrame([{"Item Size": item_size, "Pattern Type": pattern_type, "Standard Weight per Pc (kg)": std_weight}])
                        item_df = pd.concat([item_df, new_row], ignore_index=True)
                    item_df.to_csv(ITEM_MASTER_FILE, index=False)
                    st.success(f"Saved: {item_size}")
                    st.rerun()

        st.subheader("Current Item Master Inventory")
        st.dataframe(item_df, use_container_width=True)

    # FOUNDRY MASTER
    with m_tab2:
        st.subheader("Manage Foundry Details & Pig Iron Balance")
        with st.form("foundry_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                f_name = st.text_input("Foundry Name")
                f_gst = st.text_input("GST ID / Number")
                f_address = st.text_area("Foundry Address")
            with fc2:
                f_contact = st.text_input("Contact Person Name")
                f_mobile = st.text_input("Mobile / Phone Number")
                f_pig_iron = st.number_input("Pig Iron Opening Balance Given (kg)", min_value=0.0, step=10.0)

            submit_foundry = st.form_submit_button("Save Foundry Details")

            if submit_foundry and f_name:
                if f_name in foundry_df["Foundry Name"].values:
                    foundry_df.loc[foundry_df["Foundry Name"] == f_name] = [f_name, f_gst, f_address, f_contact, f_mobile, f_pig_iron]
                else:
                    new_f = pd.DataFrame([{
                        "Foundry Name": f_name, "GST ID": f_gst, "Address": f_address,
                        "Contact Person": f_contact, "Mobile": f_mobile, "Pig Iron Opening Balance (kg)": f_pig_iron
                    }])
                    foundry_df = pd.concat([foundry_df, new_f], ignore_index=True)
                foundry_df.to_csv(FOUNDRY_MASTER_FILE, index=False)
                st.success(f"Saved Foundry: {f_name}")
                st.rerun()

        st.subheader("Current Foundry Directory")
        st.dataframe(foundry_df, use_container_width=True)

# -----------------------------------------------------------------------------
# 3. CREATE PURCHASE ORDER & PDF GENERATION
# -----------------------------------------------------------------------------
elif menu == "📑 Create Purchase Order":
    st.header("Generate Purchase Order (PO)")

    if foundry_df.empty or item_df.empty:
        st.warning("Please configure both Foundry Master and Item Master before generating a PO.")
    else:
        # Header Info
        st.subheader("1. PO Header")
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            po_number = st.text_input("Purchase Order No.", f"PO-{datetime.now().strftime('%Y%m%d%H%M')}")
        with p_col2:
            po_date = st.date_input("PO Date", date.today())
        with p_col3:
            selected_foundry = st.selectbox("Select Foundry", foundry_df["Foundry Name"].unique())

        st.markdown("---")
        st.subheader("2. Add Line Items to Purchase Order")

        i_col1, i_col2, i_col3, i_col4 = st.columns([3, 2, 2, 2])
        with i_col1:
            selected_item = st.selectbox("Select Item Size", item_df["Item Size"].unique())
        with i_col2:
            ordered_pcs = st.number_input("Order Qty (Pcs)", min_value=1, step=1)
        with i_col3:
            rate_per_kg = st.number_input("Rate per KG (Rs)", min_value=0.01, step=0.50)
        with i_col4:
            st.write(" ")
            st.write(" ")
            add_po_item = st.button("➕ Add Item to PO")

        # Auto fetch standard weight
        std_w_pc = item_df.loc[item_df["Item Size"] == selected_item, "Standard Weight per Pc (kg)"].values[0]
        expected_total_kg = round(ordered_pcs * std_w_pc, 2)
        item_total_amount = round(expected_total_kg * rate_per_kg, 2)

        if add_po_item:
            st.session_state.po_basket.append({
                "PO No": po_number,
                "PO Date": str(po_date),
                "Foundry Name": selected_foundry,
                "Item Size": selected_item,
                "Ordered Qty (Pcs)": ordered_pcs,
                "Std Weight per Pc (kg)": std_w_pc,
                "Expected Total Weight (kg)": expected_total_kg,
                "Rate per Kg (Rs)": rate_per_kg,
                "Total Amount (Rs)": item_total_amount,
                "Recd Qty (Pcs)": 0,
                "Pending Qty (Pcs)": ordered_pcs,
                "Status": "OPEN",
                "Completion Date": "N/A"
            })
            st.success(f"Added {selected_item} to draft PO!")

        # Basket Display & Finalization
        if st.session_state.po_basket:
            st.subheader("Items in Current Purchase Order")
            basket_df = pd.DataFrame(st.session_state.po_basket)
            st.dataframe(basket_df[["Item Size", "Ordered Qty (Pcs)", "Std Weight per Pc (kg)", 
                                    "Expected Total Weight (kg)", "Rate per Kg (Rs)", "Total Amount (Rs)"]], use_container_width=True)

            tot_po_weight = basket_df["Expected Total Weight (kg)"].sum()
            tot_po_cost = basket_df["Total Amount (Rs)"].sum()

            m1, m2 = st.columns(2)
            m1.metric("Total Estimated Weight", f"{tot_po_weight:.2f} kg")
            m2.metric("Total Estimated Order Value", f"Rs. {tot_po_cost:,.2f}")

            btn_col1, btn_col2 = st.columns([2, 10])
            with btn_col1:
                save_po = st.button("💾 Save & Issue Purchase Order", type="primary")
            with btn_col2:
                clear_po = st.button("❌ Clear Draft")

            if clear_po:
                st.session_state.po_basket = []
                st.rerun()

            if save_po:
                po_df = pd.concat([po_df, pd.DataFrame(st.session_state.po_basket)], ignore_index=True)
                po_df.to_csv(PO_FILE, index=False)
                st.success(f"Purchase Order {po_number} created successfully!")
                
                # Option to Download PDF
                if REPORTLAB_AVAILABLE:
                    pdf_buffer = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                    styles = getSampleStyleSheet()
                    story = []

                    story.append(Paragraph("<b>PURCHASE ORDER</b>", styles['Title']))
                    story.append(Spacer(1, 10))
                    story.append(Paragraph(f"<b>PO Number:</b> {po_number} | <b>Date:</b> {po_date}", styles['Normal']))
                    story.append(Paragraph(f"<b>Foundry Name:</b> {selected_foundry}", styles['Normal']))
                    story.append(Spacer(1, 15))

                    table_data = [["Item Size", "Qty (Pcs)", "Std Wt/Pc", "Exp Total Wt (kg)", "Rate/Kg (Rs)", "Total (Rs)"]]
                    for _, r in basket_df.iterrows():
                        table_data.append([r["Item Size"], str(r["Ordered Qty (Pcs)"]), str(r["Std Weight per Pc (kg)"]), 
                                          str(r["Expected Total Weight (kg)"]), str(r["Rate per Kg (Rs)"]), f"{r['Total Amount (Rs)']:,.2f}"])

                    t = Table(table_data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E88E5")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0,0), (-1,0), 6),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 15))
                    story.append(Paragraph(f"<b>Total Order Amount: Rs. {tot_po_cost:,.2f}</b>", styles['Heading2']))

                    doc.build(story)
                    pdf_data = pdf_buffer.getvalue()

                    st.download_button(
                        label="📄 Download Purchase Order PDF",
                        data=pdf_data,
                        file_name=f"PO_{po_number}.pdf",
                        mime="application/pdf"
                    )

                st.session_state.po_basket = []

# -----------------------------------------------------------------------------
# 4. CHALLAN ENTRY AGAINST PO (AUTOMATIC WEIGHT VARIATION & PENDING DEDUCTION)
# -----------------------------------------------------------------------------
elif menu == "🚚 Challan Entry against PO":
    st.header("Challan Entry & Material Receipt")

    if po_df.empty:
        st.info("No active Purchase Orders available. Please generate a PO first.")
    else:
        open_pos = po_df[po_df["Status"] == "OPEN"]["PO No"].unique()
        if len(open_pos) == 0:
            st.success("All Purchase Orders are fully fulfilled!")
        else:
            st.subheader("1. Select PO & Enter Challan Header")
            ch_col1, ch_col2, ch_col3 = st.columns(3)
            with ch_col1:
                selected_po = st.selectbox("Select Purchase Order No.", open_pos)
            with ch_col2:
                ch_number = st.text_input("Challan No.")
            with ch_col3:
                ch_date = st.date_input("Challan Receipt Date", date.today())

            # Get PO Items
            po_items = po_df[(po_df["PO No"] == selected_po) & (po_df["Pending Qty (Pcs)"] > 0)]
            foundry_for_po = po_items["Foundry Name"].values[0] if not po_items.empty else ""

            st.write(f"**Foundry:** {foundry_for_po}")
            st.markdown("---")

            st.subheader("2. Receive Items against PO")
            rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 2])

            with rc1:
                recv_item = st.selectbox("Select Item in PO", po_items["Item Size"].unique())
            with rc2:
                item_po_data = po_items[po_items["Item Size"] == recv_item].iloc[0]
                max_pending = item_po_data["Pending Qty (Pcs)"]
                recv_pcs = st.number_input(f"Received Qty (Pcs) [Max Pending: {max_pending}]", min_value=1, max_value=int(max_pending), step=1)
            with rc3:
                actual_weight_recd = st.number_input("Actual Received Weight (kg)", min_value=0.01, step=0.1)
            with rc4:
                st.write(" ")
                st.write(" ")
                add_challan_line = st.button("➕ Add Item to Challan")

            std_w = item_po_data["Std Weight per Pc (kg)"]
            exp_wt = round(recv_pcs * std_w, 2)
            wt_var = round(actual_weight_recd - exp_wt, 2)
            status_tag = "OVERWEIGHT (Loss)" if wt_var > 0 else ("UNDERWEIGHT (Gain)" if wt_var < 0 else "EXACT MATCH")

            if add_challan_line:
                st.session_state.challan_basket.append({
                    "Challan Date": str(ch_date),
                    "Challan No": ch_number,
                    "PO No": selected_po,
                    "Foundry Name": foundry_for_po,
                    "Item Size": recv_item,
                    "Qty (Pcs)": recv_pcs,
                    "Actual Weight (kg)": actual_weight_recd,
                    "Expected Weight (kg)": exp_wt,
                    "Weight Variation (kg)": wt_var,
                    "Status": status_tag
                })
                st.success(f"Added {recv_item} ({recv_pcs} pcs) to Challan!")

            if st.session_state.challan_basket:
                st.subheader("Items in Current Challan Entry")
                c_basket_df = pd.DataFrame(st.session_state.challan_basket)
                st.dataframe(c_basket_df, use_container_width=True)

                c_tot_act = c_basket_df["Actual Weight (kg)"].sum()
                c_tot_exp = c_basket_df["Expected Weight (kg)"].sum()
                c_tot_var = c_basket_df["Weight Variation (kg)"].sum()

                x1, x2, x3 = st.columns(3)
                x1.metric("Actual Weight Received", f"{c_tot_act:.2f} kg")
                x2.metric("Expected Standard Weight", f"{c_tot_exp:.2f} kg")
                x3.metric("Weight Loss / Gain Variance", f"{c_tot_var:+.2f} kg", 
                          delta_color="inverse" if c_tot_var > 0 else "normal")

                if st.button("💾 Submit Challan & Update PO Balances", type="primary"):
                    if not ch_number:
                        st.error("Please provide a Challan Number.")
                    else:
                        # Append to Challan File
                        challan_df = pd.concat([challan_df, pd.DataFrame(st.session_state.challan_basket)], ignore_index=True)
                        challan_df.to_csv(CHALLAN_FILE, index=False)

                        # Auto-Deduct from PO Pending Balances
                        for entry in st.session_state.challan_basket:
                            po_mask = (po_df["PO No"] == entry["PO No"]) & (po_df["Item Size"] == entry["Item Size"])
                            po_df.loc[po_mask, "Recd Qty (Pcs)"] += entry["Qty (Pcs)"]
                            po_df.loc[po_mask, "Pending Qty (Pcs)"] -= entry["Qty (Pcs)"]

                            # Check if line item complete
                            if po_df.loc[po_mask, "Pending Qty (Pcs)"].values[0] <= 0:
                                po_df.loc[po_mask, "Completion Date"] = str(ch_date)

                        # Check if entire PO closed
                        po_sub = po_df[po_df["PO No"] == selected_po]
                        if (po_sub["Pending Qty (Pcs)"] <= 0).all():
                            po_df.loc[po_df["PO No"] == selected_po, "Status"] = "CLOSED"

                        po_df.to_csv(PO_FILE, index=False)
                        st.session_state.challan_basket = []
                        st.success("Challan submitted successfully! PO balances updated.")
                        st.rerun()

# -----------------------------------------------------------------------------
# 5. FOUNDRY REPORTS, PENDING ORDERS & TIMELINE TRACKING
# -----------------------------------------------------------------------------
elif menu == "📈 Foundry Pending Reports & Timeline":
    st.header("Foundry Ledger, Pending Orders & Timeline Analytics")

    r_tab1, r_tab2, r_tab3 = st.tabs(["📦 Pending PO Status", "⏱️ Order Timeline & Fulfillment", "⚖️ Weight Variation Audit"])

    # TAB 1: PENDING POs
    with r_tab1:
        st.subheader("Live Pending Quantities per Foundry")
        if po_df.empty:
            st.info("No PO data available.")
        else:
            f_filter = st.selectbox("Filter by Foundry", ["ALL"] + list(foundry_df["Foundry Name"].unique()))
            view_po = po_df if f_filter == "ALL" else po_df[po_df["Foundry Name"] == f_filter]

            st.dataframe(view_po[[
                "PO No", "PO Date", "Foundry Name", "Item Size", 
                "Ordered Qty (Pcs)", "Recd Qty (Pcs)", "Pending Qty (Pcs)", "Status"
            ]], use_container_width=True)

    # TAB 2: TIMELINE & SPEED
    with r_tab2:
        st.subheader("Foundry Execution & Completion Timeline")
        if po_df.empty:
            st.info("No order timeline data available.")
        else:
            po_timeline = po_df.copy()
            po_timeline["PO Date"] = pd.to_datetime(po_timeline["PO Date"])
            
            # Calculate Fulfillment Percentage
            po_timeline["Fulfillment %"] = round((po_timeline["Recd Qty (Pcs)"] / po_timeline["Ordered Qty (Pcs)"]) * 100, 1)
            
            st.dataframe(po_timeline[[
                "PO No", "Foundry Name", "PO Date", "Item Size", 
                "Ordered Qty (Pcs)", "Recd Qty (Pcs)", "Fulfillment %", "Status", "Completion Date"
            ]], use_container_width=True)

    # TAB 3: WEIGHT LOSS AUDIT
    with r_tab3:
        st.subheader("Mould Weight Variance Audit Report")
        if challan_df.empty:
            st.info("No challan entries available.")
        else:
            st.dataframe(challan_df, use_container_width=True)

            total_excess = challan_df["Weight Variation (kg)"].sum()
            st.warning(f"⚠️ Total Financial Extra Material Purchased across all Challans: **{total_excess:+.2f} kg**")

# -----------------------------------------------------------------------------
# 6. ITEM SIZE SPECIFIC REPORT & TIMELINE
# -----------------------------------------------------------------------------
elif menu == "🔍 Item Size Specific Report":
    st.header("Item Size Inspection & Casting History")

    if item_df.empty:
        st.warning("No items found in Item Master.")
    else:
        selected_size = st.selectbox("Select Item Size to Inspect", item_df["Item Size"].unique())

        std_weight_info = item_df.loc[item_df["Item Size"] == selected_size, "Standard Weight per Pc (kg)"].values[0]
        pattern_info = item_df.loc[item_df["Item Size"] == selected_size, "Pattern Type"].values[0]

        m1, m2 = st.columns(2)
        m1.info(f"**Pattern Type:** {pattern_info}")
        m2.info(f"**Standard Weight per Pc:** {std_weight_info} kg")

        st.markdown("---")
        st.subheader(f"1. Casting Receipt History for '{selected_size}'")

        if challan_df.empty or selected_size not in challan_df["Item Size"].values:
            st.info(f"No castings received yet for item size: {selected_size}")
        else:
            size_challans = challan_df[challan_df["Item Size"] == selected_size].copy()

            tot_recd_pcs = size_challans["Qty (Pcs)"].sum()
            tot_recd_wt = size_challans["Actual Weight (kg)"].sum()
            tot_wt_var = size_challans["Weight Variation (kg)"].sum()

            s_col1, s_col2, s_col3 = st.columns(3)
            s_col1.metric("Total Received Quantity", f"{tot_recd_pcs} Pcs")
            s_col2.metric("Total Actual Weight Received", f"{tot_recd_wt:.2f} kg")
            s_col3.metric("Net Weight Variance", f"{tot_wt_var:+.2f} kg", delta_color="inverse" if tot_wt_var > 0 else "normal")

            st.dataframe(size_challans[[
                "Challan Date", "Challan No", "Foundry Name", "PO No",
                "Qty (Pcs)", "Actual Weight (kg)", "Expected Weight (kg)", 
                "Weight Variation (kg)", "Status"
            ]], use_container_width=True)

        st.markdown("---")
        st.subheader(f"2. Purchase Order Timeline for '{selected_size}'")

        if po_df.empty or selected_size not in po_df["Item Size"].values:
            st.info(f"No Purchase Orders generated for item size: {selected_size}")
        else:
            size_pos = po_df[po_df["Item Size"] == selected_size].copy()
            size_pos["Fulfillment %"] = round((size_pos["Recd Qty (Pcs)"] / size_pos["Ordered Qty (Pcs)"]) * 100, 1)

            st.dataframe(size_pos[[
                "PO No", "PO Date", "Foundry Name", "Ordered Qty (Pcs)",
                "Recd Qty (Pcs)", "Pending Qty (Pcs)", "Fulfillment %",
                "Status", "Completion Date"
            ]], use_container_width=True)
