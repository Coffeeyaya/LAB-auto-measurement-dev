## for `time_dependent` tab

### Phase 1: The Initial Boot (Run #1)
1. You launch the app from your terminal (`streamlit run app.py`).
2. Streamlit reads your script from top to bottom.
3. **The Defaults:** It hits the `if k not in st.session_state:` block. Because memory is completely empty on the first boot, it injects all your default values (e.g., `"2-2"`, `100`, etc.) into `st.session_state`.
4. **The Uploader:** It draws the file uploader with the key `td_uploader_0`. It is empty, so it skips the file-processing block.
5. **The UI Binding:** It draws the UI boxes (`st.text_input(..., key="device_number")`). Because of the `key`, the box reaches into `st.session_state["device_number"]`, grabs the default `"2-2"`, and displays it.
6. The script hits the bottom and **goes to sleep**, waiting for you to do something.

---

### Phase 2: The File Upload (Run #2)
1. You drag your `config.json` file into the uploader box.
2. **The Wake-up:** Streamlit detects an interaction. It instantly kills the current state and **restarts the script from Line 1.**
3. **The Skip:** It hits the defaults block again. But this time, `"device_number"` is *already* in `st.session_state`. It skips the defaults, perfectly preserving memory.
4. **The Injection:** It hits the uploader block. `uploaded_file is not None` is now **True**. It reads the JSON file and forcefully overwrites the data inside `st.session_state` with the new file's data.
5. **The Magic Trick:** It adds `1` to the uploader key and hits `st.rerun()`. 
6. **The Interruption:** `st.rerun()` tells Streamlit: *"Stop everything immediately, do not pass go, do not draw the rest of the UI, just restart from Line 1 right now!"*

---

### Phase 3: The UI Refresh (Run #3)
1. The script is running from top to bottom again (a split-second after Phase 2).
2. **The Wipe:** It reaches the uploader box. The code asks for `td_uploader_1`. Streamlit looks at the screen and says, *"Wait, the box on the screen is `td_uploader_0`. I don't know what `td_uploader_1` is. I'd better draw a brand-new, empty box!"* (This is how the file disappears from the UI).
3. **The Visual Update:** It reaches your text boxes and number spinners. They look into `st.session_state`, see the brand-new JSON data we injected during Phase 2, and render those new values on the screen.
4. The script hits the bottom and goes to sleep again.

---

### Phase 4: Typing in a Box (Run #4)
1. You click the "Wait Time" box and change it from `5` to `10`. You hit Enter.
2. **The Auto-Save:** Before Streamlit even restarts your script, it secretly updates `st.session_state["wait_time"] = 10` behind the scenes.
3. **The Restart:** Streamlit runs from top to bottom. The uploader is empty, so it skips the file reading. It draws the UI, pulling the fresh `10` from memory.
4. Goes to sleep.

---

### Phase 5: Clicking "Save" (Run #5)
1. You click the "Update JSON Config" button.
2. **The Restart:** Streamlit restarts from top to bottom. 
3. **The Trigger:** It reaches `if st.button(...):`. Because you *just* clicked it, this evaluates to **True** for this specific run.
4. **The Assembly:** It builds `config_dict`. Notice how we don't read from the UI boxes—we read directly from `st.session_state`. We are grabbing the live memory.
5. **The Disk Write:** It saves the JSON file to your hard drive.
6. **The Preview:** It draws the `st.success` green box and the `st.expander` with the `st.json()` preview.
7. Goes to sleep.
