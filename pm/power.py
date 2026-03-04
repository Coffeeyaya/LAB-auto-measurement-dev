# Import & initialize the PyVISA library
import visa
rm = visa.ResourceManager()

# Find the power meter: we know it's a USB device from vendor 0x1313 (Thorlabs),
# and with model 0x8078 (PM100D).
res_found = rm.list_resources('USB?*::0x1313::0x8078::?*::INSTR')
if not res_found:
    raise Exception('Could not find the PM100D power meter. Is it connected and powered on?')

# Connect to the power meter, make it beep, and ask it for its ID
print('Connecting to PM100D...')
meter = rm.open_resource(res_found[0])
meter.read_termination = '\n'
meter.write_termination = '\n'
meter.timeout = 2000  # ms

meter.write('system:beeper')

print('*idn?')
print('--> ' + meter.query('*idn?'))

# Configure the power meter for laser power measurements
wavelength = 1064  # nm
beam_diameter = 20  # mm

meter.write('sense:power:unit W')
meter.write('sense:power:range:auto 1')
meter.write('sense:average:count 50')
meter.write('configure:power')

meter.write('sense:correction:wavelength %.1f' % wavelength)
meter.write('sense:correction:beamdiameter %1f' % beam_diameter)

# Read the current power reading
# ... this could go into a loop, where you first set the output power of the
#     laser, then read the power meter, etc.

cur_power = meter.query_ascii_values('read?')[0]
print('Current power: %.2g W' % cur_power)