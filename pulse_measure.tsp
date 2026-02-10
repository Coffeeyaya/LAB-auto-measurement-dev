-- pulse_measure.tsp
-- Keithley 2636B buffered pulsed measurement

function run_pulse(
    vds, vgh, vgl,
    dt, pulse_width, cycles)

    abort
    errorqueue.clear()

    smua.reset()
    smub.reset()

    smua.source.func = smua.OUTPUT_DCVOLTS
    smub.source.func = smub.OUTPUT_DCVOLTS

    smua.source.limiti = 0.01
    smub.source.limiti = 0.001

    smua.measure.nplc = 0.01
    smub.measure.nplc = 0.01

    smua.source.levelv = vds
    smua.source.output = smua.OUTPUT_ON
    smub.source.output = smub.OUTPUT_ON

    smua.nvbuffer1.clear()
    smub.nvbuffer1.clear()

    smua.nvbuffer1.timestamps = 1
    smub.nvbuffer1.timestamps = 1

    npts = math.floor(pulse_width / dt)

    for c = 1, cycles do

        smub.source.levelv = vgh
        for i = 1, npts do
            smua.measure.i(smua.nvbuffer1)
            smub.measure.i(smub.nvbuffer1)
            delay(dt)
        end

        smub.source.levelv = vgl
        for i = 1, npts do
            smua.measure.i(smua.nvbuffer1)
            smub.measure.i(smub.nvbuffer1)
            delay(dt)
        end

    end

    smua.source.levelv = 0
    smub.source.levelv = 0
end
