'''
check available resources
'''
import pyvisa
rm = pyvisa.ResourceManager()
print(rm.list_resources())