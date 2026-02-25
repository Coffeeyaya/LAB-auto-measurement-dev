import pyvisa

# 1. Initialize the Resource Manager
rm = pyvisa.ResourceManager()

# 2. Print available connections so you can find the AOTF's ID
print("Available instruments on this computer:")
resources = rm.list_resources()
for res in resources:
    print(f" - {res}")

# 3. Paste the correct ID from the list above here:
AOTF_RESOURCE_ID = 'USB0::0xXXXX::0xXXXX::XXXXXX::INSTR' 

try:
    print(f"\nAttempting to connect to: {AOTF_RESOURCE_ID}")
    
    # 4. Open the connection
    aotf = rm.open_resource(AOTF_RESOURCE_ID)
    
    # Configure basic communication settings
    aotf.timeout = 5000
    aotf.write_termination = '\n'
    aotf.read_termination = '\n'
    
    print("Success! The USB connection is open.")
    
    # 5. Send a safe command to verify it's listening
    # 'DAU DIS' disables the external daughter card, returning control to the standard GUI 
    aotf.write("DAU DIS")
    print("Test command 'DAU DIS' sent successfully.")

except Exception as e:
    print(f"\nConnection failed! Error details:")
    print(e)

finally:
    # 6. Always close the connection when done so it doesn't get locked
    if 'aotf' in locals():
        aotf.close()
        print("\nConnection safely closed.")