loadscript gate_sweep

function run()
    smua.reset()
    smua.source.func = smua.OUTPUT_DCVOLTS
    smua.source.rangev = 5
    smua.source.limiti = 1e-3
    smua.measure.autorangei = smua.AUTORANGE_ON
    smua.source.output = smua.OUTPUT_ON

    smua.source.levelv = 1
    delay(0.1)
    print(smua.measure.i())

    smua.source.levelv = -1
    delay(0.1)
    print(smua.measure.i())

    smua.source.output = smua.OUTPUT_OFF
end

endscript
