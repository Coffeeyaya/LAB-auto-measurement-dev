-- File: gate_sweep.tsp

loadscript gate_sweep

smua.reset()
smua.source.func = smua.OUTPUT_DCVOLTS
smua.source.rangev = 5
smua.source.limiti = 1e-3
smua.measure.autorangei = smua.AUTORANGE_ON
smua.source.output = smua.OUTPUT_ON

function set_gate(v)
    smua.source.levelv = v
    delay(0.1)
    print(smua.measure.i())
end

set_gate(1)
set_gate(-1)

smua.source.output = smua.OUTPUT_OFF

endscript
