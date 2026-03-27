def encode_binary_sequence(binary_string, vg_on, vg_off, bit_duration, channel_idx=None):
    """
    Translates a string of 1s and 0s into a hardware measurement sequence.
    1 = Vg ON + Light ON
    0 = Vg ON + Light OFF
    """
    sequence = []
    
    # 1. Start with a baseline rest period to stabilize the device
    sequence.append({"Vg": vg_off, "duration": 2.0}) 
    
    # 2. Loop through every character in your string
    for bit in binary_string:
        
        # --- THE BIT PULSE ---
        if bit == '1':
            # Bit 1: Apply Vg AND turn on the Light
            step = {
                "Vg": vg_on, 
                "duration": bit_duration, 
                "laser_cmd3": {"channel": channel_idx, "on": 1} 
            }
        elif bit == '0':
            # Bit 0: Apply Vg, but keep the Light OFF
            step = {
                "Vg": vg_on, 
                "duration": bit_duration,
                "laser_cmd3": {"channel": channel_idx, "on": 0} 
            }
        else:
            # Ignore any accidental spaces or invalid characters
            continue 
            
        sequence.append(step)
        
        # --- THE RETURN-TO-ZERO (REST) STATE ---
        # Turn everything off for half a bit-duration so consecutive 
        # 11s or 00s don't visually merge together in your data.
        rest_step = {
            "Vg": vg_off,
            "duration": bit_duration / 2.0,
            "laser_cmd3": {"channel": channel_idx, "on": 0}
        }
        sequence.append(rest_step)
        
    return sequence

seq = encode_binary_sequence("1011", 1, -1, 2, channel_idx=None)
for s in seq:
    print(s)