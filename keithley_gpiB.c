#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <visa.h>
#include <time.h>

#define GPIB_ADDR "GPIB0::26::INSTR"

#define DRAIN_V 1.0
#define GATE_HIGH 1.0
#define GATE_LOW -1.0
#define PULSE_WIDTH 1.0
#define TOTAL_CYCLES 5
#define DT 0.01

int main() {
    ViSession rm, vi;
    ViStatus status;
    char buffer[256];
    FILE *csv;
    double t_now;
    clock_t start_time;

    // ---------- Open VISA session ----------
    status = viOpenDefaultRM(&rm);
    if (status != VI_SUCCESS) { printf("Failed to open VISA RM\n"); return -1; }

    status = viOpen(rm, GPIB_ADDR, VI_NULL, VI_NULL, &vi);
    if (status != VI_SUCCESS) { printf("Failed to open GPIB\n"); return -1; }

    // Set termination characters
    viSetAttribute(vi, VI_ATTR_WR_TERMCHAR_EN, VI_TRUE);
    viSetAttribute(vi, VI_ATTR_RD_TERMCHAR, '\n');

    // ---------- Reset SMUs ----------
    viPrintf(vi, "smua.reset()\n");
    viPrintf(vi, "smub.reset()\n");

    // Configure SMUA (Drain)
    viPrintf(vi, "smua.source.func = smua.OUTPUT_DCVOLTS\n");
    viPrintf(vi, "smua.source.levelv = %f\n", DRAIN_V);
    viPrintf(vi, "smua.source.output = smua.OUTPUT_ON\n");

    // Configure SMUB (Gate)
    viPrintf(vi, "smub.source.func = smub.OUTPUT_DCVOLTS\n");
    viPrintf(vi, "smub.source.levelv = %f\n", GATE_LOW);
    viPrintf(vi, "smub.source.output = smub.OUTPUT_ON\n");

    // ---------- Open CSV ----------
    csv = fopen("keithley_gpiB.csv", "w");
    if (!csv) { printf("Failed to open CSV\n"); return -1; }
    fprintf(csv, "Time_s,V_Gate,I_Drain_A,I_Gate_A\n");

    start_time = clock();

    // ---------- Pulsed measurement ----------
    for (int cycle = 0; cycle < TOTAL_CYCLES; cycle++) {
        for (int gv = 0; gv < 2; gv++) {
            double gate_voltage = (gv == 0) ? GATE_HIGH : GATE_LOW;
            viPrintf(vi, "smub.source.levelv = %f\n", gate_voltage);

            int npts = (int)(PULSE_WIDTH / DT);
            for (int i = 0; i < npts; i++) {
                // Measure currents
                viPrintf(vi, "print(smua.measure.i(), smub.measure.i())\n");
                viScanf(vi, "%s", buffer);

                // Timestamp
                t_now = ((double)(clock() - start_time)) / CLOCKS_PER_SEC;

                // Save CSV
                fprintf(csv, "%f,%f,%s\n", t_now, gate_voltage, buffer);

                // Delay DT
                struct timespec ts;
                ts.tv_sec = 0;
                ts.tv_nsec = (long)(DT * 1e9);
                nanosleep(&ts, NULL);
            }
        }
    }

    // ---------- Turn off outputs ----------
    viPrintf(vi, "smua.source.output = smua.OUTPUT_OFF\n");
    viPrintf(vi, "smub.source.output = smub.OUTPUT_OFF\n");

    fclose(csv);
    viClose(vi);
    viClose(rm);

    printf("Measurement complete. CSV saved.\n");
    return 0;
}
