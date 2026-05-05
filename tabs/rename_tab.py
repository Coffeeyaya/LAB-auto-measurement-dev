import streamlit as st
import json
from pathlib import Path

# ==========================================
# 1. THE LOGIC (No UI code here)
# ==========================================
def bulk_update_json_keys(folder_path: str, updates: dict) -> tuple[int, list]:
    """
    Scans a folder and updates specific keys in all JSON files based on the updates dictionary.
    Returns the number of files updated and a list of log messages.
    """
    folder = Path(folder_path)
    logs = []
    
    if not folder.exists() or not folder.is_dir():
        return 0, [f"❌ Error: The folder '{folder_path}' does not exist."]

    json_files = list(folder.glob("*.json"))
    if not json_files:
        return 0, [f"⚠️ No JSON files found in '{folder_path}'."]

    updated_count = 0

    for file_path in json_files:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            modified = False
            
            # Apply updates if the key exists in the file AND the user provided a new value
            for key, new_value in updates.items():
                if key in data and new_value: 
                    data[key] = str(new_value)
                    modified = True
            
            if modified:
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=4)
                logs.append(f"✅ Updated: {file_path.name}")
                updated_count += 1
                
        except json.JSONDecodeError:
            logs.append(f"⚠️ Skipped {file_path.name}: Invalid JSON format.")
        except Exception as e:
            logs.append(f"❌ Error processing {file_path.name}: {e}")

    logs.append(f"\n🎉 Done! Updated {updated_count} out of {len(json_files)} files.")
    return updated_count, logs


# ==========================================
# 2. THE UI (Streamlit Rendering)
# ==========================================
def render_rename_tab():
    st.header("🗂️ Bulk Config Updater")
    st.markdown("Use this tool to quickly update the **Device Number** across an entire folder of queued measurements.")

    # --- 1. User Inputs ---
    st.subheader("1. Select Target Folder")
    
    # Dropdown for common folders, plus manual entry
    common_folders = ["config/time_pulse_queue", "config/time_queue", "config/idvg_queue", "Custom..."]
    selected_preset = st.selectbox("Target Queue", common_folders, key="rn_folder_preset")
    
    if selected_preset == "Custom...":
        folder_path = st.text_input("Enter custom folder path:", key="rn_custom_path")
    else:
        folder_path = selected_preset

    st.divider()

    # --- 2. Update Parameters ---
    st.subheader("2. Define Updates")
    
    new_device = st.text_input("New Device Number", placeholder="e.g., 8-7", key="rn_new_dev")

    st.divider()

    # --- 3. Preview & Execution ---
    st.subheader("3. Execute")
    
    # Show how many files are in the folder before running
    if folder_path:
        target_dir = Path(folder_path)
        if target_dir.exists() and target_dir.is_dir():
            file_count = len(list(target_dir.glob("*.json")))
            st.caption(f"Found **{file_count}** JSON file(s) in `{folder_path}`")
        else:
            st.caption(f"Folder `{folder_path}` not found.")

    # Execution Button
    if st.button("🚀 Run Bulk Update", type="primary", use_container_width=True, key="rn_execute_btn"):
        if not folder_path:
            st.error("Please specify a folder path.")
        elif not new_device:
            st.warning("Please provide a new Device Number to update.")
        else:
            # Package the updates into a dictionary
            updates_to_apply = {}
            if new_device: updates_to_apply["device_number"] = new_device

            with st.spinner("Updating files..."):
                # Call the pure logic function
                count, logs = bulk_update_json_keys(folder_path, updates_to_apply)

            # Display the results
            if count > 0:
                st.success(logs[-1]) # Print the final "Done" message
                with st.expander("Show detailed logs"):
                    for log in logs[:-1]:
                        st.text(log)
            else:
                st.error(logs[-1])