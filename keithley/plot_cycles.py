import matplotlib.pyplot as plt
import pandas as pd

FILENAME = "final_cycles.csv"

try:
    df = pd.read_csv(FILENAME)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Plot Drain Current
    ax1.plot(df['Time'], df['I_Drain'], 'b.-', label='Drain Current')
    ax1.set_ylabel('Drain Current (A)')
    ax1.set_title('Cyclic Voltammetry Test')
    ax1.legend()
    ax1.grid(True)
    
    # Plot Gate Current (and show the switching)
    ax2.plot(df['Time'], df['I_Gate'], 'r.-', label='Gate Current')
    ax2.set_ylabel('Gate Current (A)')
    ax2.set_xlabel('Time (s)')
    ax2.legend()
    ax2.grid(True)
    
    # Show the Gate Voltage states as background
    ax3 = ax2.twinx()
    ax3.plot(df['Time'], df['V_Gate'], 'g--', alpha=0.3, label='Gate Voltage')
    ax3.set_ylabel('Gate Voltage (V)')
    
    plt.show()

except Exception as e:
    print(f"Could not plot: {e}")