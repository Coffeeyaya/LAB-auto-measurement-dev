-- pulse_logic.tsp
-- This is a pure Lua/TSP file. No Python syntax here!

function RunPulseSequence(drain_v, gate_high, gate_low, width, cycles)
    
    -- Setup Buffers
    smua.nvbuffer1.clear()
    smub.nvbuffer1.clear()
    smua.nvbuffer1.appendmode = 1
    smub.nvbuffer1.appendmode = 1
    
    -- Setup Source
    smua.source.levelv = drain_v
    smua.source.output = smua.OUTPUT_ON
    smub.source.output = smub.OUTPUT_ON
    
    -- The Loop
    for i = 1, cycles do
        -- High Pulse
        smub.source.levelv = gate_high
        timer.reset()
        t_start = timer.measure.t()
        while (timer.measure.t() - t_start) < width do
            smua.measure.i(smua.nvbuffer1)
            smub.measure.i(smub.nvbuffer1)
        end
        
        -- Low Pulse
        smub.source.levelv = gate_low
        timer.reset()
        t_start = timer.measure.t()
        while (timer.measure.t() - t_start) < width do
            smua.measure.i(smua.nvbuffer1)
            smub.measure.i(smub.nvbuffer1)
        end
    end
    
    -- Turn Off
    smua.source.output = smua.OUTPUT_OFF
    smub.source.output = smub.OUTPUT_OFF
    
    -- Return Data
    printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1)
    printbuffer(1, smub.nvbuffer1.n, smub.nvbuffer1)
end