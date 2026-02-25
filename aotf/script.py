import os

def generate_aotf_sequence(filename, sequence_steps, loop_line=1):
    """
    Generates a text file formatted for the Fianium AOTF Playback mode.
    """
    filepath = os.path.join(os.getcwd(), filename)
    
    with open(filepath, 'w') as f:
        for step in sequence_steps:
            f.write(step + "\n")
        f.write(f"loop({loop_line})\n") # Optional: Loop the sequence

    print(f"Sequence saved to: {filepath}")
    print("Press (Control + F2) in the AOTF GUI and move this file there.")

# --- Define your experiment here ---
# Let's say you want to alternate between 480nm and 650nm
my_experiment = [
    "channel(1,480,30)",  # Channel 1, 480nm, 30% power
    "wait(2)",            # Dwell for 2 seconds
    "channel(1,650,30)",  # Change to 650nm, 30% power
    "wait(2)",            # Dwell for 2 seconds
    "active(00000000)",   # Turn all channels off 
    "wait(1)"
]

# Generate the file
generate_aotf_sequence("experiment_1.txt", my_experiment)