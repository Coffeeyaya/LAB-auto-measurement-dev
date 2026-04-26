import json
from pathlib import Path

def update_device_number_in_folder(folder_path, new_device_number, target_keys):
    """
    Scans a folder for JSON files and updates the device number.
    """
    folder = Path(folder_path)
    
    # 1. Check if folder exists
    if not folder.exists() or not folder.is_dir():
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    # 2. Find all JSON files in the directory
    json_files = list(folder.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in '{folder_path}'.")
        return

    updated_count = 0

    # 3. Process each file
    for file_path in json_files:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            modified = False
            
            # Check for the keys and update them
            for key in target_keys:
                if key in data:
                    data[key] = str(new_device_number)  # Ensure it stays a string!
                    modified = True
            
            # 4. Save the file back if changes were made
            if modified:
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"Updated: {file_path.name}")
                updated_count += 1
                
        except json.JSONDecodeError:
            print(f"Skipped {file_path.name}: Invalid JSON format.")
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

    print(f"\n Done! Updated {updated_count} out of {len(json_files)} files.")

if __name__ == "__main__":
    # ==========================================
    # USER CONFIGURATION
    # ==========================================
    
    # Change this to the folder containing your queue (e.g., "config/idvg_queue")
    TARGET_FOLDER = "config/time_queue" 
    
    # Change this to your new device number
    NEW_DEVICE_NUMBER = "8-7" 
    
    update_device_number_in_folder(TARGET_FOLDER, NEW_DEVICE_NUMBER, target_keys='device_number')