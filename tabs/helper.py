import os
import subprocess 
import sys
import platform

def launch_in_terminal(script_name):
    """Launches a given Python script in a new OS-level terminal window."""
    if not os.path.exists(script_name):
        return False, f"Could not find script: {script_name}"
    
    current_dir = os.getcwd()
    try:
        if platform.system() == "Windows":
            command = f'start cmd /K "{sys.executable} {script_name}"'
            subprocess.Popen(command, shell=True)
            return True, f"🚀 Opened {script_name} in a new Command Prompt!"
            
        elif platform.system() == "Darwin":
            apple_script = f'''
            tell application "Terminal"
                do script "cd '{current_dir}' && '{sys.executable}' '{script_name}'"
                activate
            end tell
            '''
            subprocess.Popen(['osascript', '-e', apple_script])
            return True, f"🚀 Opened {script_name} in a new Mac Terminal!"
            
        else:
            return False, "Opening a new terminal is currently only supported on Windows and Mac."
    except Exception as e:
        return False, f"Failed to launch script: {e}"
