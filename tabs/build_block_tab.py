import streamlit as st
import pandas as pd
import json

def render_custom_sequence_tab():
    st.subheader("🧱 Custom Sequence Builder")
    st.markdown("Add arbitrary steps to your measurement block. The script will execute them top-to-bottom.")

    # 1. Define the default starting block
    if "custom_seq" not in st.session_state:
        st.session_state.custom_seq = pd.DataFrame([
            {"Step Name": "Dark Relax", "Duration (s)": 5.0, "Vg (V)": 0.0, "Laser State": "Turn OFF", "Servo State": "Block"},
            {"Step": "Gate & Light ON", "Duration (s)": 1.0, "Vg (V)": 1.0, "Laser State": "Turn ON", "Servo State": "Unblock"}
        ])

    # 2. Define the UI Rules (Dropdown menus for the table)
    column_config = {
        "Duration (s)": st.column_config.NumberColumn("Duration (s)", min_value=0.1, step=0.5, format="%.1f"),
        "Vg (V)": st.column_config.NumberColumn("Vg (V)", step=0.1, format="%.1f"),
        "Laser State": st.column_config.SelectboxColumn(
            "Laser State", 
            options=["Ignore", "Turn ON", "Turn OFF"], 
            help="Ignore means the laser stays in its previous state."
        ),
        "Servo State": st.column_config.SelectboxColumn(
            "Servo State", 
            options=["Ignore", "Block", "Unblock"],
            help="Ignore means the servo doesn't move."
        )
    }

    # 3. Render the interactive table!
    edited_df = st.data_editor(
        st.session_state.custom_seq,
        column_config=column_config,
        num_rows="dynamic", # <--- THIS is the magic that lets you add/delete arbitrary rows
        use_container_width=True,
        key="sequence_editor"
    )

    st.divider()

    # 4. Saving the arbitrary sequence to JSON
    if st.button("Save Custom Sequence"):
        # Convert the Pandas DataFrame to a clean list of dictionaries
        sequence_list = edited_df.to_dict(orient="records")
        
        config_dict = {
            "measurement_mode": "Custom Arbitrary Block",
            "cycle_number": 3, # You can still wrap the whole block in cycles!
            "custom_sequence": sequence_list 
        }
        
        with open("config/FORMAL_custom_sequence.json", "w") as f:
            json.dump(config_dict, f, indent=4)
            
        st.success("Arbitrary sequence saved successfully!")
        st.json(config_dict)