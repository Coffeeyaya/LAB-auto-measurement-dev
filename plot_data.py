import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import os
import numpy as np
from pathlib import Path

def select_and_plot_data():
    # 1. Initialize the hidden Tkinter root window
    root = tk.Tk()
    root.withdraw() 

    # 2. Open the file selection dialog
    print("Opening file dialog...")
    file_paths = filedialog.askopenfilenames(
        title="Select Data Files to Plot (You can select multiple!)",
        # --- MODIFIED: Automatically opens in whatever folder you run the script from ---
        initialdir=os.getcwd(), 
        filetypes=[("CSV Data Files", "*.csv"), ("All Files", "*.*")]
    )

    if not file_paths:
        print("No files selected. Exiting.")
        return

    # 3. Set up the Matplotlib figure
    plt.figure(figsize=(10, 6))
    plot_type = None

    # 4. Loop through every file you clicked
    for file_path in file_paths:
        path = Path(file_path)
        
        try:
            df = pd.read_csv(path)
            label = path.stem # Uses the file name (without .csv) as the legend label
            
            # --- SMART ROUTING: Auto-detect measurement type from file name ---
            if "idvg" in path.name.lower():
                plot_type = "Id-Vg"
                # Id-Vg needs the absolute value of current for the Log scale
                plt.plot(df["V_G"], df["I_D"].abs(), marker='.', linestyle='-', label=label)
                plt.yscale('log')
                plt.xlabel("Gate Voltage Vg (V)", fontsize=12)
                plt.ylabel("Drain Current |Id| (A)", fontsize=12)
                
            elif "idvd" in path.name.lower():
                plot_type = "Id-Vd"
                plt.plot(df["V_D"], np.abs(df["I_D"]), marker='.', linestyle='-', label=label)
                plt.yscale('log')
                plt.xlabel("Drain Voltage Vd (V)", fontsize=12)
                plt.ylabel("Drain Current Id (A)", fontsize=12)
                
            elif "time" in path.name.lower():
                plot_type = "Time-Dependent"
                plt.plot(df["Time"], df["I_D"], marker='.', linestyle='-', label=label)
                plt.xlabel("Time (s)", fontsize=12)
                plt.ylabel("Drain Current Id (A)", fontsize=12)
                
            else:
                print(f"Warning: Unknown measurement type for {path.name}. Skipping.")

        except Exception as e:
            print(f"Error reading {path.name}: {e}")

    # 5. Finalize and show the plot
    if plot_type:
        plt.title(f"Overlay Plot: {plot_type} Characteristics", fontsize=14, fontweight='bold')
        plt.grid(True, which="both", ls="--", alpha=0.5)
        plt.legend(loc='best', fontsize=10)
        plt.tight_layout()
        
        print("Rendering plot...")
        plt.show()
    else:
        print("No valid data could be plotted.")

if __name__ == "__main__":
    select_and_plot_data()