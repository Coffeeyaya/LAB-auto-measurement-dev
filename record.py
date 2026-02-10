import pyvisa

rm = pyvisa.ResourceManager()
k = rm.open_resource("GPIB0::26::INSTR")
k.write_termination = "\n"
k.read_termination = "\n"

# Step 2a: Verify basic TSP commands work
print("1+1 =", k.query("print(1+1)"))  # Should output 2

# Step 2b: Check what scripts exist currently
scripts = k.query("print(script.list())")
print("Existing scripts:", scripts)

# Optional: delete all scripts for a completely clean slate
k.write("script.delete(script.list())")
scripts_after_delete = k.query("print(script.list())")
print("Scripts after delete:", scripts_after_delete)

k.close()
