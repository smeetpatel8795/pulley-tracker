import pandas as pd
import streamlit as st
import os

st.set_page_config(page_title="Pulley Weight & Loss Tracker", layout="wide")

MASTER_FILE = "master_data.csv"
CHALLAN_FILE = "challan_entries.csv"

# Initialize DataFrames
if os.path.exists(MASTER_FILE):
    master_df = pd.read_csv(MASTER_FILE)
else:
    master_df = pd.DataFrame(columns=["Item Size", "Standard Weight per Pc (kg)"])

if os.path.exists(CHALLAN_FILE):
    challan_df = pd.read_csv(CHALLAN_FILE)
else:
    challan_df = pd.DataFrame(columns=[
        "Date", "Challan No", "Foundry Name", "Item Size", 
        "Qty (Pcs)", "Actual Weight (kg)", "Expected Weight (kg)", 
        "Weight Variation (kg)", "Status"
    ])

# Session state for temporary multi-item storage inside a single challan
if "current_challan_items" not in st.session_state:
    st.session_state.current_challan_items = []

st.title("Pulley Manufacturing: Weight & Loss Tracker")

menu = st.sidebar.radio("Navigation", ["Enter New Challan", "Master Data Settings", "Challan History & Reports"])

# ----------------------------------------------------
# 1. MASTER DATA MANAGEMENT
# ----------------------------------------------------
if menu == "Master Data Settings":
    st.header("Master Data Management")
    with st.form("master_form"):
        size = st.text_input("Item Size (e.g., 4 inch B-Section)")
        std_weight = st.number_input("Standard Weight per Piece (in kg)", min_value=0.00, step=0.01)
        submit_master = st.form_submit_button("Save Item Size")
        
        if submit_master:
            if size.strip() != "" and std_weight > 0:
                if size in master_df["Item Size"].values:
                    master_df.loc[master_df["Item Size"] == size, "Standard Weight per Pc (kg)"] = std_weight
                else:
                    new_row = pd.DataFrame([{"Item Size": size, "Standard Weight per Pc (kg)": std_weight}])
                    master_df = pd.concat([master_df, new_row], ignore_index=True)
                
                master_df.to_csv(MASTER_FILE, index=False)
                st.success(f"Saved: {size} with {std_weight} kg/pc")
            else:
                st.error("Please provide valid Size and Weight values.")

    st.subheader("Current Master Data")
    st.dataframe(master_df, use_container_width=True)

# ----------------------------------------------------
# 2. CHALLAN ENTRY FORM (MULTI-ITEM SUPPORT)
# ----------------------------------------------------
elif menu == "Enter New Challan":
    st.header("New Challan Entry (Multiple Items)")
    if master_df.empty:
        st.warning("Please add Item Sizes in 'Master Data Settings' first.")
    else:
        # Step A: Challan Header Information
        st.subheader("1. Challan Details")
        c1, c2, c3 = st.columns(3)
        with c1:
            date = st.date_input("Challan Date")
        with c2:
            challan_no = st.text_input("Challan No.")
        with c3:
            foundry = st.text_input("Foundry Name")

        st.markdown("---")

        # Step B: Adding Items to the Current Challan
        st.subheader("2. Add Item Sizes to this Challan")
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        with col1:
            item_size = st.selectbox("Select Item Size", master_df["Item Size"].unique())
        with col2:
            qty_pcs = st.number_input("Qty in Pcs", min_value=1, step=1)
        with col3:
            actual_weight = st.number_input("Actual Weight Received (kg)", min_value=0.01, step=0.01)
        with col4:
            st.write(" ")
            st.write(" ")
            add_item = st.button("➕ Add Item to List")

        if add_item:
            std_w_pc = master_df.loc[master_df["Item Size"] == item_size, "Standard Weight per Pc (kg)"].values[0]
            expected_weight = round(qty_pcs * std_w_pc, 2)
            variation = round(actual_weight - expected_weight, 2)
            status = "OVERWEIGHT (Loss)" if variation > 0 else ("UNDERWEIGHT (Gain)" if variation < 0 else "EXACT MATCH")

            item_data = {
                "Item Size": item_size,
                "Qty (Pcs)": qty_pcs,
                "Actual Weight (kg)": actual_weight,
                "Expected Weight (kg)": expected_weight,
                "Weight Variation (kg)": variation,
                "Status": status
            }
            st.session_state.current_challan_items.append(item_data)
            st.success(f"Added {item_size} to current challan list!")

        # Step C: Review Items & Submit Complete Challan
        if st.session_state.current_challan_items:
            st.subheader("Items in Current Challan")
            temp_items_df = pd.DataFrame(st.session_state.current_challan_items)
            st.dataframe(temp_items_df, use_container_width=True)

            tot_actual = temp_items_df["Actual Weight (kg)"].sum()
            tot_expected = temp_items_df["Expected Weight (kg)"].sum()
            tot_variation = temp_items_df["Weight Variation (kg)"].sum()

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Challan Total Actual Weight", f"{tot_actual:.2f} kg")
            mc2.metric("Challan Total Expected Weight", f"{tot_expected:.2f} kg")
            mc3.metric("Challan Total Variation", f"{tot_variation:+.2f} kg", delta_color="inverse" if tot_variation > 0 else "normal")

            btn1, btn2 = st.columns([2, 10])
            with btn1:
                save_final_challan = st.button("💾 Submit Complete Challan", type="primary")
            with btn2:
                clear_items = st.button("❌ Clear Items")

            if clear_items:
                st.session_state.current_challan_items = []
                st.experimental_rerun()

            if save_final_challan:
                if not challan_no or not foundry:
                    st.error("Please enter both Challan No. and Foundry Name before submitting.")
                else:
                    new_rows = []
                    for item in st.session_state.current_challan_items:
                        full_entry = {
                            "Date": str(date),
                            "Challan No": challan_no,
                            "Foundry Name": foundry,
                            **item
                        }
                        new_rows.append(full_entry)

                    challan_df = pd.concat([challan_df, pd.DataFrame(new_rows)], ignore_index=True)
                    challan_df.to_csv(CHALLAN_FILE, index=False)

                    st.session_state.current_challan_items = []
                    st.success(f"Challan No. {challan_no} successfully saved with all items!")

# ----------------------------------------------------
# 3. HISTORY & REPORTS
# ----------------------------------------------------
elif menu == "Challan History & Reports":
    st.header("Challan History & Weight Loss Analysis")
    if challan_df.empty:
        st.info("No challan records available yet.")
    else:
        total_actual = challan_df["Actual Weight (kg)"].sum()
        total_expected = challan_df["Expected Weight (kg)"].sum()
        total_variation = challan_df["Weight Variation (kg)"].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Actual Weight Purchased", f"{total_actual:.2f} kg")
        col2.metric("Total Master Standard Weight", f"{total_expected:.2f} kg")
        col3.metric("Net Total Weight Variation", f"{total_variation:+.2f} kg", delta_color="inverse" if total_variation > 0 else "normal")
        
        st.subheader("All Entered Items Across Challans")
        st.dataframe(challan_df, use_container_width=True)
