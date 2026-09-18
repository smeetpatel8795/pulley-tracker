import pandas as pd
import streamlit as st
import os

st.set_page_config(page_title="Pulley Weight & Loss Tracker", layout="wide")

MASTER_FILE = "master_data.csv"
CHALLAN_FILE = "challan_entries.csv"

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

st.title("Pulley Manufacturing: Weight & Loss Tracker")

menu = st.sidebar.radio("Navigation", ["Enter New Challan", "Master Data Settings", "Challan History & Reports"])

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

elif menu == "Enter New Challan":
    st.header("New Challan Entry")
    if master_df.empty:
        st.warning("Please add Item Sizes in 'Master Data Settings' first.")
    else:
        with st.form("challan_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                date = st.date_input("Challan Date")
                challan_no = st.text_input("Challan No.")
            with col2:
                foundry = st.text_input("Foundry Name")
                item_size = st.selectbox("Item Size", master_df["Item Size"].unique())
            with col3:
                qty_pcs = st.number_input("Qty in Nos (Pcs)", min_value=1, step=1)
                actual_weight = st.number_input("Qty in KGs (Actual Recd. Weight)", min_value=0.01, step=0.01)
            
            submit_challan = st.form_submit_button("Process & Save Challan")
            
            if submit_challan:
                std_w_pc = master_df.loc[master_df["Item Size"] == item_size, "Standard Weight per Pc (kg)"].values[0]
                expected_weight = round(qty_pcs * std_w_pc, 2)
                variation = round(actual_weight - expected_weight, 2)
                status = "OVERWEIGHT (Loss)" if variation > 0 else ("UNDERWEIGHT (Gain)" if variation < 0 else "EXACT MATCH")
                
                new_entry = {
                    "Date": str(date),
                    "Challan No": challan_no,
                    "Foundry Name": foundry,
                    "Item Size": item_size,
                    "Qty (Pcs)": qty_pcs,
                    "Actual Weight (kg)": actual_weight,
                    "Expected Weight (kg)": expected_weight,
                    "Weight Variation (kg)": variation,
                    "Status": status
                }
                
                challan_df = pd.concat([challan_df, pd.DataFrame([new_entry])], ignore_index=True)
                challan_df.to_csv(CHALLAN_FILE, index=False)
                
                st.subheader("Challan Summary")
                res_col1, res_col2, res_col3 = st.columns(3)
                res_col1.metric("Actual Weight Received", f"{actual_weight} kg")
                res_col2.metric("Expected Standard Weight", f"{expected_weight} kg")
                res_col3.metric("Weight Variation", f"{variation:+} kg", delta_color="inverse" if variation > 0 else "normal")

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
        
        st.subheader("All Entered Challans")
        st.dataframe(challan_df, use_container_width=True)
