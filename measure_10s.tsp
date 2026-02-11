-- measure_10s.tsp
-- Measures SMUA and SMUB current for 10 seconds at 0.1 s intervals

function measure_10s()
    local meas = {}        -- table to store measurements

    -- Reset channels
    smua.reset()
    smub.reset()

    -- Configure outputs
    smua.source.func = smua.OUTPUT_DCVOLTS
    smua.source.levelv = 1
    smua.source.output = smua.OUTPUT_ON

    smub.source.func = smub.OUTPUT_DCVOLTS
    smub.source.levelv = 1
    smub.source.output = smub.OUTPUT_ON

    local dt = 0.1        -- sampling interval in seconds
    local t_end = 10      -- total measurement time
    local t = 0

    while t < t_end do
        local i_a = smua.measure.i()
        local i_b = smub.measure.i()
        table.insert(meas, {t, i_a, i_b})
        t = t + dt
        wait(dt)
    end

    -- Turn off outputs
    smua.source.output = smua.OUTPUT_OFF
    smub.source.output = smub.OUTPUT_OFF

    return meas
end
