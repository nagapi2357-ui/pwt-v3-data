# Arbiter — Dual AD9833 DDS Firmware

Teensy 4.1 firmware for Plan C analog experiment: tests whether prime frequency ratios produce different interference patterns than composite ratios using clean analog sine waves.

## Pin Assignments

| Pin | Function |
|-----|----------|
| 10  | CS — DDS A (Board A) |
| 9   | CS — DDS B (Board B) |
| 13  | SCK (SPI0) |
| 11  | MOSI (SPI0) |
| 8   | Trigger output → scope CH4 |

Both AD9833s share a 25 MHz MCLK from Board A's oscillator.

## Serial

- **Baud:** 115200
- **Line ending:** newline (`\n`)

## Modes

### CHAR Mode (default)

Interactive characterisation. Send commands via serial monitor:

```
FA 5000.0        Set DDS A to 5 kHz
FB 3000.0        Set DDS B to 3 kHz
PA 90            Set DDS A phase to 90°
PB 45            Set DDS B phase to 45°
OFF A|B|BOTH     Sleep DDS
ON A|B|BOTH      Wake DDS (sine)
SWEEP A 1000 10000 100 50    Sweep A from 1-10 kHz, 100 Hz steps, 50 ms dwell
IM3 4950 5050    Two-tone IM3 test
STATUS           Print state
HELP             Command list
```

### RUN Mode

Type `RUN` to start the automated test sequence:

- 5 blocks × 30 pairs × 8 phase steps = **1200 trials**
- Each trial: 500 ms settle → 200 ms capture (trigger HIGH) → 300 ms gap
- ~20 minutes total
- Pairs randomised per block (Fisher-Yates, analog noise seed)
- Output: CSV on serial for Python capture script
- Type `STOP` to abort

**CSV format:**
```
block, pair_id, stratum, compClass, f1, f2, phase_step, millis
```

## Building

1. Install [Teensyduino](https://www.pjrc.com/teensy/teensyduino.html)
2. Open `arbiter.ino` in Arduino IDE
3. Board: Teensy 4.1 | USB Type: Serial | CPU: 600 MHz
4. Upload

## Test Matrix

30 pairs across 5 strata — see `test_matrix.h` and `../../test-matrix.md` for details.
