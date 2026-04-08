import streamlit as st
import pandas as pd
import subprocess
import json
import os

def render_plotter_tab():
    st.header("📈 Matplotlib Plotter & Data Merger")
    
    # 1. Upload files
    uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)
    
    if not uploaded_files:
        st.info("Upload CSV files to begin.")
        return

    # Save uploaded files to a temporary directory
    os.makedirs("temp_data", exist_ok=True)
    saved_files = []
    
    for f in uploaded_files:
        file_path = os.path.join("temp_data", f.name)
        with open(file_path, "wb") as out:
            out.write(f.getbuffer())
        saved_files.append(file_path)

    default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", 
                      "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

    style_options = {
        "Line with dots": ".-",
        "Solid line": "-",
        "Dashed line": "--",
        "Scatter (dots)": "o",
        "Scatter (x)": "x",
        "Scatter (*)": "*"
    }

    # 2. Select files, colors, AND styles
    st.subheader("1. Select Files, Colors & Styles")
    selected_files = []
    file_colors = {}
    file_styles = {}
    
    for i, file in enumerate(saved_files):
        # 3 columns: Filename (wider), Color (narrow), Style (medium)
        col1, col2, col3 = st.columns([2, 1, 1.5]) 
        
        with col1:
            is_selected = st.checkbox(os.path.basename(file), value=True, key=f"file_{file}")
            
        with col2:
            default_hex = default_colors[i % len(default_colors)]
            chosen_color = st.color_picker("Color", value=default_hex, key=f"color_{file}", label_visibility="collapsed")
            
        with col3:
            # Style dropdown per file
            selected_style_name = st.selectbox("Style", options=list(style_options.keys()), key=f"style_{file}", label_visibility="collapsed")
            chosen_style = style_options[selected_style_name]
            
        if is_selected:
            selected_files.append(file)
            file_colors[file] = chosen_color
            file_styles[file] = chosen_style
    
    if not selected_files:
        st.warning("Please check at least one file to proceed.")
        return

    # Extract columns from the first selected file
    try:
        sample_df = pd.read_csv(selected_files[0])
        all_cols = sample_df.columns.tolist()
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return

    # 3. Select columns
    st.subheader("2. Select Columns")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Select X-Axis (Choose One)**")
        x_col = st.radio("X-Axis", options=all_cols, label_visibility="collapsed")
        
    with col2:
        st.write("**Select Y-Axis (Choose One)**")
        y_col = st.radio("Y-Axis", options=all_cols, label_visibility="collapsed")
    
    st.write("---")
    log_y = st.checkbox("Logarithmic Y-Axis", value=True)
    st.write("---")

    # 4. Actions
    st.subheader("3. Actions")
    col_run, col_down = st.columns([1, 1])
    
    with col_run:
        if st.button("Run External Plotter", type="primary"):
            if not y_col:
                st.warning("Select at least one Y-axis checkbox.")
            else:
                config = {
                    "files": selected_files,
                    "file_colors": file_colors,
                    "file_styles": file_styles, # Pass the file-specific styles to Matplotlib
                    "x_col": x_col,
                    "y_col": y_col,
                    "log_y": log_y
                }
                with open("plot_config.json", "w") as f:
                    json.dump(config, f, indent=4)
                
                st.toast("Launching Matplotlib window...")
                subprocess.Popen(["python", "standalone_plotter.py"]) 

    with col_down:
        if y_col:
            try:
                dfs_to_concat = []
                cols_to_keep = [x_col, y_col]
                
                for file in selected_files:
                    df = pd.read_csv(file)
                    available_cols = [c for c in cols_to_keep if c in df.columns]
                    sub_df = df[available_cols].copy()
                    
                    base_name = os.path.basename(file)
                    rename_dict = {c: f"{base_name}_{c}" for c in available_cols}
                    sub_df.rename(columns=rename_dict, inplace=True)
                    
                    dfs_to_concat.append(sub_df)
                
                merged_df = pd.concat(dfs_to_concat, axis=1)
                csv_buffer = merged_df.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Download Horizontally Merged CSV",
                    data=csv_buffer,
                    file_name="merged_horizontal_data.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"Could not generate concatenated CSV: {e}")