# Measurement Steps

- turn on the Laser, warm up for 30 minutes.
- check the output port of AOTF controller, make sure the physical shutter is open.
- check the optical fiber is connected.
- check the attenuator is rotated to a proper angle.


- in electrical measurement computer, go to the folder: `lab-auto-measurement-dev-review`.
- click `run_app.bat`.
- you can see `servo control`, `time dependent`, `idvg`, `idvd`, `power calibration`, `data plotter`, `batch generator` tabs appear

### power calibration
- connect the arduino nano to the usb-A port (direct connection, not hub)
  - in case that before measuring the power, the laser beam is blocked by servo motor.
  - you can manually open and close the shutter by clicking `open servo GUI` in `servo motor control` tab.
- connect the power meter to the usb-A port in the hub
- connect RJ-45 to usb-A from laser computer to electrical computer
- launch `AOTF` controller GUI on laser computer.
- click `run_laser_control.bat` on laser computer.
  - it will grab AOTF controller GUI to the top left corner. click on it multiple times.

- in `power calibration` tab, set: wavelength, channel, power
- `save power config`
- run power.py, it will repeat the measuring loop until it finds suitable power percentage values.
- the resulting power percentage values are recorded in `pp_df.csv`
- the measured target powers are recorded in `measured_power_df.csv`
- run verify_power.py, it will asks the laser computer to set the corresponding wavelength and power, and measure it again. The verified results are recorded in `verified_power_df.csv`
- These results are used for later measurements like id-vg, id-vd, and time-dependent.
- If you find that the communication is sometimes delayed, try turn off the wifi of the laser computer since it might interrupt the connection.

### Now we can set parameters for the following 3 measurements

- parameters are stored in json files, which are located in subfolders of the `config` folder
- After these measurements, the data will be stored in `data` folder, along with the backup config files with the same names.
- Therefore, given the old config file, we can `upload` it so that we don't need to manually type them again.

## Before doing the electrical measurement, please make sure the Keithley cable is connected to usb-A port 

### Time dependent measurement

**Hardware Setup**
- `Dark Current`: only measures the dark current, you can set `vg_on, vg_off, vd` ...
- `Laser Only`: If the servo motor is broken, then we can fall back to this mode, which directly use the AOTF controller GUI to toggle light on off.
- `Laser + Servo`: This mode contains complete functionalities, including all the electrical and laser control. Different from `Laser Only` mode, it uses servo motor to switch light on off.
- `Baseline Reset`: The baseline drain current might accumulate after 1 measurement, so we can insert a reset measurement with Vg = 0 V under dark condition. It will stop only when Id drops to a sepcific `Target Baseline`. Note that it uses auto-range to ensure reliable measured value.

**Electrical Mode**
- `Continuous DC Vg`: it applies a target Vg and stays there.
- `Pulsed Vg Train`: it periodically applies Vg pulses with a specific `pulse width`, adjacent pulses are separated by `rest time`.

**General Information**
- `Description`: You can take notes here, the text won't affect measurement.
- `Device number`: device number of the target device
- `run number`: we might perform multiple experiments on 1 device, the resulting file name would be something like: `"time_pulse_{Device number}_{run number}.csv"`. If 1 device has duplicated run number, the program will detect this harzard and stop the measurment immediately to prevent overwrite.
- `Label`: We can queue multiple measurements and run them with one click, this label is the name of the particular curve.


**Keithley SMU Settings**
- (A) means `drain`; (B) means `gate`
- `current limit`: physical current limit, if the measured current is higher then this value, it will be `physically clamped` at this value to protect hardware and device 
- `current range`: Time dependent measurement requires high resolution, so we can not use auto-range. therefore, you need to manually set the range slightly higher than the measured value. If measured value > range, it is `virtually clamped` at range.
The actual value is in between range and limit. (limit > range)
  - ex: The dark current is ~ $10^{-12}$ A, so range can be set to $1e-8$
  - Timing to set it higher: the measured value hit the range.
  - Timing to set it lower: the measured value is not low enough or it becomes negative.
- `NPLC`: number of power line cycles
  - NPLC = 1 means the highest resolution in theory is 16 ms / point, while the actual resolution depends on (NPLC, pulse width, rest time and program delay)

**Voltage and Timing Settings**
- `Vd constant`: in time dependent measurement, Vd is always a constant, regardless of DC or pulsed mode.
- `Vg on`: the Vg value when light is on.
- `Vg off`: the Vg value when light is off.
- `Wait time`: wait this amount of time before this measurement.

**Optics & Arrays**
- For `Laser Only` and `Laser + Servo`
- Set wavelength, Channel and Power
- Currently in each box, it only accepts 1 value, not multiple


**Timing & Sequence Durations**
- `Duration 1`: duration for `Vg on`
- `Duration 2`: duration for `Vg off`
- `Cycle number`: cycles repeated.

$\Rightarrow$ For `Laser Only`
- `Duration 3`: duration for toggle laser on
- `Duration 4`: duration for toggle laser off
- `On/Off number`: number of laser on/off in 1 period
- Note that there are transmission and GUI delay, so the timing is not accurate

$\Rightarrow$ For `Laser + Servo`
- `Servo on time`: duration for switching laser on by servo motor
- `Servo off time`: duration for switching laser off by servo motor
- `Servo on/off #`: number of servo motor switches in 1 period

$\Rightarrow$ For `Pulsed` mode
- `pulse width`: initially it's at `base Vg`, then it will suddenly rise to `target Vg`, stays for `pulse width` seconds, measure drain and gate current, finally falls back to `base Vg`
- `rest time between pulses`: time delay inserted between two adjacent pulses, note that the actual time between 2 pusles is not exactly this number, it's `rest time` + python program delay + usb port transmission delay.


**Queue Preview and Management**

`1. Add to Queue`
- After finish setting all the parameters, we can add the config file to queue. 
- its file location is in the subfolder of `config`
  - ex: if you choose the pulsed mode, then it will be saved in `config/time_pulse_queue`
  - ex: if you choose the DC mode, then it will be saved in `config/time_queue`

`2. Run Queue`
- Click the `run script in terminal` button, all the config files inside this queue will be run in the order you save them
- After all the measurements, you need to clear those config files in queue by clicking `clear queue` 

`3. Run servo motor GUI`
- here's also a servo motor GUI to control it manually.

### Batch Generator
- manually editing these parameters is tedious and error-prone.
- this batch generator functionality allow us to generate multiple copies from 1 base config file, and changing simply 1 parameters (and of course, the `run number`).
- `select input directory`
  - inside `config` folder, choose a subfolder your base config file resides in
  - choose the base config file, you can preview it
  
- `select output directory`
  - the generated config files will be saved here

- `Define parameter sweep`
  - choose the parameter that you want to sweep
  - enter the sweep values
  - enter the starting run number, so that it won't collide with existing files in the output directory

- `Baseline reset injection`
  - as mentioned earlier, the baseline might accumulate after 1 measurement
  - we might want to perform baseline reset between measurements
  - ex: baseline reset $\rightarrow$ measurement 1 $\rightarrow$ baseline reset $\rightarrow$ measurement 2 $\rightarrow$ baseline reset $\rightarrow$ ...
  - simply click the checkbox if you want this functionality
- `Generate Batch Queue`
  - it automatically generates the sweep config files and optionally, interleaved baseline reset config files


## **Note that both Id-Vg and Id-Vd directly use AOTF controller GUI to toggler laser, there's no servo motor involved, so you must check that the servo motor is not blocking the laser beam**

### Id-Vg measurement

**Measurement Mode**
- Use Vg = -5 V to 5 V as example to explain the difference between the following 2 modes
- `Steady state`: set Vg = -5 V, wait `source to measure delay`, measure drain and gate current, set Vg = -4.9 V, ...

- `Pulsed`: base Vg = 0 V. set Vg = -5 V, wait `pulse width`, measure drain and gate current, fall back to base Vg = 0 V, wait `rest time between pulses`, set Vg = -4.9 V ...

**Other settings**

basically the same as in time dependent measurement.
- if you select `Steady state`, it is in auto-range mode, you don't need to set range manually.
- if you seelct `pulsed mode`, you need to set range.
- range too high: dark current is not accurate
- range too low: it might hit the range when the transistor turns on

### Id-Vd measurement

basically the same as in Id-Vg measurement.
- The only difference is that both Vg and Vd are pulses now.
- so we need to set `base Vd` and `base Vg`


### Data plotter
- After measurement, you might want to plot it immediately.
- upload multiple csv files
- select those files you want to plot
- select x, y columns, colors and linestyles
- optionally use log scale
- click `Run external plotter` to plot it, main figure and legend will pop up
- click `Download Horizontally Merged CSV`, it will concatenate those selected files and columns in horizontal direction.
  - This feature is convenient for latter plotting using other softwares such as Origin or Excel