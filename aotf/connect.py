import pyvisa

rm = pyvisa.ResourceManager()
# Add the exact ASRL strings your computer printed out
test_ports = ['ASRL3::INSTR', 'ASRL4::INSTR', 'ASRL5::INSTR']

for port in test_ports:
    try:
        print(f"Testing {port}...")
        aotf = rm.open_resource(port)
        
        # Set a short timeout so it doesn't hang long on the wrong ports
        aotf.timeout = 2000 
        aotf.write_termination = '\n'
        aotf.read_termination = '\n'
        
        # Send the safe test command
        aotf.write("DAU DIS")
        
        print(f"--> SUCCESS! {port} is your AOTF controller.")
        aotf.close()
        break  # We found it, stop testing the others
        
    except Exception as e:
        print(f"--> Failed on {port}. Moving to next...")
        if 'aotf' in locals():
            aotf.close()

print("\nFinished testing.")