loadscript gate_sweep

function run()
    smua.reset()
    smua.source.func = smua.OUTPUT_DCVOLTS
    smua.source.rangev = 5
    smua.source.limiti = 1e-3
    smua.measure.autorangei = smua.AUTORANGE_ON

    smua.nvbuffer1.clear()
    
    smua.source.levelv = 1
    delay(0.1)
    smua.measure.i(smua.nvbuffer1)
    
    smua.source.levelv = -1
    delay(0.1)
    smua.measure.i(smua.nvbuffer1)
    
    returnbuffer(1, smua.nvbuffer1)
end

endscript
