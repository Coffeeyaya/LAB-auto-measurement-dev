import json
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import sys
import os

plt.rcParams['font.size'] = 15
plt.rcParams['font.weight'] = 'bold'

def plot_settings():
    plt.rc('axes', labelweight='bold', labelsize=15)
    plt.tick_params(axis='y', which="both", direction='in')
    plt.tick_params(axis='x', direction='in')
    plt.grid(True, which='major', linestyle='--', linewidth=0.5, alpha=0.7)

def convert_label(col):
    col_label = col
    col_split = col.split('_')
    if len(col_split) == 2:
        col_label = col_split[0] + col_split[1].lower()
    return col_label

def main():
    try:
        with open("plot_config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Config file not found. Run from Streamlit first.")
        sys.exit(1)

    # 1. Create the Main Data Figure
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.canvas.manager.set_window_title('Main Plot') # Names the window
    
    file_colors = config.get("file_colors", {})
    file_styles = config.get("file_styles", {})
    
    # Plot the requested data file by file
    # Plot the requested data file by file
    for file in config["files"]:
        try:
            df = pd.read_csv(file)
            
            plot_color = file_colors.get(file, None)
            plot_style = file_styles.get(file, ".-") 
            base_name = os.path.basename(file)
            
            # Use the new singular y_col from the config
            y_col = config["y_col"]
            
            if config["x_col"] in df.columns and y_col in df.columns:
                y_data = df[y_col].abs() if config["log_y"] else df[y_col]
                
                # Apply the file-specific style and color
                ax.plot(df[config["x_col"]], y_data, plot_style, 
                        label=f"{base_name} ({y_col})", 
                        color=plot_color)
        except Exception as e:
            print(f"Failed to plot {file}: {e}")

    # Formatting for Main Plot
    x_label = convert_label(config["x_col"])
    y_label = convert_label(config["y_col"])
    ax.set_xlabel(xlabel=x_label)
    ax.set_ylabel(f"| {y_label} |" if config["log_y"] else y_label)
    if config["log_y"]:
        ax.set_yscale('log')
    
    plot_settings()

    # 2. Create the Separate Legend Figure
    handles, labels = ax.get_legend_handles_labels()
    
    if handles: # Only open the window if there is actually data to label
        # Create a smaller figure just for the legend
        fig_legend = plt.figure(figsize=(4, 3))
        fig_legend.canvas.manager.set_window_title('Legend')
        
        # Place the legend in the center of this new empty figure
        fig_legend.legend(handles, labels, loc='center')
        
        # Hide the axes on the legend figure so it looks clean
        plt.gca().set_axis_off() 

    # Show both windows simultaneously
    plt.show()

if __name__ == "__main__":
    main()