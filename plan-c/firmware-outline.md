# Plan C — Arduino Mega Firmware Outline (Rev 2)

*Revised 2026-09-12. Updated for shared MCLK, 5-stratum test matrix, variable capture duration, IM3 automation.*

## AD9833 Technical Reference

### Frequency Resolution
- Clock: 25 MHz (shared external oscillator), frequency register: 28 bits
- Resolution: 25,000,000 / 2²⁸ = **0.0931 Hz** (~0.1 Hz)
- Frequency word = (f_out × 2²⁸) / 25,000,000
- Both DDS derive from the same clock → ratios are **exact** to 28-bit precision

### Phase Resolution
- Phase register: 12 bits → 4096 steps → **0.088° per step**
- Phase randomisation: 8 discrete values = steps of 512 in the phase register

### Key Difference from Rev 1
With shared MCLK, both DDS are **frequency-coherent**. A programmed 3:2 ratio is exactly 3:2, not approximately. Phase relationship is deterministic (set by phase register), not drifting. This is essential for the experiment.

### SPI Interface
- Mode: SPI Mode 2 (CPOL=1, CPHA=0)
- Max clock: 40 MHz
- 16-bit words, MSB first, CS (FSYNC) active LOW

## Pin Assignments

```cpp
#define CS_A    48    // DDS A chip select
#define CS_B    46    // DDS B chip select
#define TRIG    44    // Scope trigger output
// SPI: SCK=52, MOSI=51 (hardware SPI on Mega)
```

## Module Structure

### 1. `ad9833.h` — DDS Driver

```cpp
void ad9833_init(int cs_pin);
  // Reset AD9833, set sine output mode, clear RESET

void ad9833_set_freq(int cs_pin, uint32_t freq_hz_x10);
  // freq_hz_x10: frequency in 0.1 Hz units (e.g., 61237 = 6123.7 Hz)
  // Calculate 28-bit freq word, write FREQ0 register (two 14-bit writes)

void ad9833_set_phase(int cs_pin, uint16_t phase_12bit);
  // Write 12-bit value to PHASE0 (0–4095 → 0°–360°)

void ad9833_set_mode(int cs_pin, enum {SINE, TRIANGLE, SQUARE});
  // Control register bits OPBITEN, MODE, DIV2
```

### 2. `test_matrix.h` — 5-Stratum Frequency Pairs

```cpp
enum Stratum {
  PRIME_PRIME = 0,       // Both prime, coprime
  COMP_COMP = 1,         // Both composite, coprime (KILLER CONTROL)
  PRIME_COMP = 2,        // One prime one composite, coprime
  NON_COPRIME = 3,       // GCD > 1 (sanity check)
  IRRATIONAL = 4         // No closed beat period
};

struct TestPair {
  uint32_t f1_x10;       // freq in 0.1 Hz units
  uint32_t f2_x10;
  char     label[6];     // "PP1", "CC3", etc.
  uint8_t  stratum;      // Stratum enum
  uint16_t capture_ms;   // Per-pair capture duration (short window)
  uint16_t capture_long; // Long capture for spectral analysis
  uint8_t  comp_class;   // Comparison class (A=0, B=1, C=2, D=3)
};

const TestPair pairs[] = {
  // Stratum 1: Prime:Prime coprime
  {61237, 40825, "PP1", 0, 200, 2000, 1},   // 3:2
  {64549, 38729, "PP2", 0, 200, 2000, 1},   // 5:3
  {59161, 42265, "PP3", 0, 200, 2000, 1},   // 7:5
  {62678, 39895, "PP4", 0, 200, 2000, 1},   // 11:7
  {54355, 45983, "PP5", 0, 200, 2000, 0},   // 13:11
  {76376, 32733, "PP6", 0, 200, 2000, 2},   // 7:3
  {79057, 31623, "PP7", 0, 200, 2000, 2},   // 5:2
  {95743, 26135, "PP8", 0, 200, 2000, 3},   // 11:3

  // Stratum 2: Composite:Composite coprime (KILLER CONTROL)
  {53033, 47140, "CC1", 1, 200, 2000, 0},   // 9:8
  {62500, 40000, "CC2", 1, 200, 2000, 1},   // 25:16
  {75000, 33333, "CC3", 1, 200, 2000, 2},   // 9:4
  {68465, 36515, "CC4", 1, 200, 2000, 2},   // 15:8
  {83333, 30000, "CC5", 1, 200, 2000, 2},   // 25:9
  {70000, 35714, "CC6", 1, 200, 2000, 2},   // 49:25
  {60000, 41667, "CC7", 1, 200, 2000, 1},   // 36:25
  {61872, 40406, "CC8", 1, 200, 2000, 1},   // 49:32
  {64952, 38490, "CC9", 1, 200, 2000, 1},   // 27:16

  // Stratum 3: Prime:Composite coprime
  {55902, 44721, "PC1", 2, 200, 2000, 0},   // 5:4
  {58631, 42640, "PC2", 2, 200, 2000, 1},   // 11:8
  {60093, 41603, "PC3", 2, 200, 2000, 1},   // 13:9
  {66144, 37796, "PC4", 2, 200, 2000, 1},   // 7:4
  {82916, 30151, "PC5", 2, 200, 2000, 2},   // 11:4
  {90139, 27735, "PC6", 2, 200, 2000, 3},   // 13:4

  // Stratum 4: Non-coprime (sanity check)
  {70711, 35355, "NC1", 3, 200, 2000, 255}, // 4:2 = 2:1
  {61237, 40825, "NC2", 3, 200, 2000, 255}, // 9:6 = 3:2
  {61237, 40825, "NC3", 3, 200, 2000, 255}, // 15:10 = 3:2

  // Stratum 5: Irrational
  {59460, 42045, "IR1", 4, 200, 2000, 0},   // √2:1
  {63657, 39265, "IR2", 4, 200, 2000, 1},   // φ:1
  {58358, 42835, "IR3", 4, 200, 2000, 0},   // e/2:1
  {62680, 39894, "IR4", 4, 200, 2000, 1},   // π/2:1
};
const int NUM_PAIRS = 30;
```

### 3. `main.ino` — Main Firmware

```
Setup:
  SPI.begin()
  SPI.setClockDivider(SPI_CLOCK_DIV2)  // 8 MHz
  SPI.setDataMode(SPI_MODE2)
  pinMode(CS_A, OUTPUT); pinMode(CS_B, OUTPUT); pinMode(TRIG, OUTPUT)
  ad9833_init(CS_A); ad9833_init(CS_B)
  Serial.begin(115200)
  Print menu + version

Loop (three modes):

  MODE 1: Manual / Characterisation
    Serial commands:
      "FA 5000.0"    → set DDS A to 5000.0 Hz
      "FB 3000.0"    → set DDS B to 3000.0 Hz
      "PA 2048"      → set DDS A phase register
      "PB 0"         → set DDS B phase register
      "SWEEP A 1000 10000 100"  → sweep DDS A
      "IM3 5000 6000" → set up IM3 test pair (both channels)
      "RUN"          → start automated test sequence
      "STOP"         → abort

  MODE 2: Automated Test Sequence
    for block = 1 to NUM_BLOCKS:
      generate_permutation(pair_order, NUM_PAIRS)  // Fisher-Yates
      for each pair in pair_order:
        phase_b = random(8) * 512   // random from 8 discrete values
        ad9833_set_freq(CS_A, pair.f1_x10)
        ad9833_set_freq(CS_B, pair.f2_x10)
        ad9833_set_phase(CS_B, phase_b)
        delay(SETTLE_MS)
        // Short capture
        digitalWrite(TRIG, HIGH)
        Serial.print("CAPTURE_SHORT")  // signal Python to grab scope data
        delay(pair.capture_ms)
        digitalWrite(TRIG, LOW)
        delay(50)
        // Long capture (for spectral analysis)
        digitalWrite(TRIG, HIGH)
        Serial.print("CAPTURE_LONG")
        delay(pair.capture_long)
        digitalWrite(TRIG, LOW)
        // Log CSV
        Serial.println(CSV: block, pair.label, pair.stratum,
                        f1, f2, phase_b, pair.comp_class, timestamp)
        delay(GAP_MS)

  MODE 3: IM3 Characterisation
    "IM3_SWEEP" command:
      Test pairs: (5000,6000), (5000,5100), (5000,5500), (4000,6000)
      For each:
        Set DDS A and B to test freqs
        Wait settle
        Signal Python: "CAPTURE_IM3"
        Python sends SCPI to scope, captures FFT,
        measures carrier and IM product levels
        Reports IM3 in dBc
```

### 4. Constants & Timing

```cpp
#define SETTLE_MS     500    // Filter settling (>>100τ where τ=3.3µs)
#define GAP_MS        500    // Inter-trial gap
#define NUM_BLOCKS    5      // 5 blocks × 8 phase offsets = 40 per pair
#define NUM_PHASES    8      // Phase randomisation levels
```

### 5. Python Companion Script (`capture.py`)

The Arduino firmware signals the Python script over serial. Python handles:
1. SCPI commands to DS1054Z over LAN (IP: 169.254.201.110, port 5555)
2. Waveform data acquisition (`:WAV:DATA?`)
3. FFT computation and RSP metric calculation
4. CSV logging with all metrics
5. IM3 product measurement during characterisation

```
Serial protocol:
  Arduino → Python:
    "CAPTURE_SHORT,PP1,0,61237,40825,1024,200"
    "CAPTURE_LONG,PP1,0,61237,40825,1024,2000"
    "CAPTURE_IM3,5000,6000"
  Python → Arduino:
    "ACK" (ready for next trial)
    "FAIL,reason" (abort)
```

### 6. SCPI Automation Snippets

```python
# Scope setup for waveform capture
def setup_scope(duration_ms):
    scpi(":TIM:MAIN:SCAL", duration_ms / 12000)  # 12 divisions
    scpi(":TRIG:EDG:SOUR CHAN4")
    scpi(":TRIG:EDG:SLOP POS")
    scpi(":TRIG:MODE NORM")
    scpi(":SING")  # single-shot

# Waveform acquisition
def capture_waveform(channel):
    scpi(f":WAV:SOUR CHAN{channel}")
    scpi(":WAV:MODE RAW")
    scpi(":WAV:FORM BYTE")
    return scpi_read(":WAV:DATA?")

# IM3 measurement
def measure_im3(f1, f2):
    # Capture long waveform of summed output (CH3)
    data = capture_waveform(3)
    spectrum = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1/sample_rate)
    # Measure carrier and IM product levels
    carrier_power = max(power_at(spectrum, f1), power_at(spectrum, f2))
    im3_minus = power_at(spectrum, 2*f1 - f2)
    im3_plus = power_at(spectrum, 2*f2 - f1)
    return 10*np.log10(max(im3_minus, im3_plus) / carrier_power)
```

## Practical Notes

1. **Shared clock means exact ratios**: With both DDS on the same 25 MHz, a 3:2 frequency ratio is 3:2 to 28-bit precision. No crystal mismatch.

2. **Variable capture duration**: Each pair gets `capture_ms` (short, for time-domain metrics) and `capture_long` (2000 ms, for spectral analysis / RSP metric). Currently all pairs use 200 ms / 2000 ms — the repetition periods are short enough that this is adequate for all.

3. **Phase protocol**: In each block, cycle through all 8 phase offsets for each pair (not random selection with replacement). This ensures uniform phase coverage. Total: 5 blocks × 8 phases × 30 pairs = 1200 trials.

4. **IM3 automation**: Run `IM3_SWEEP` before main experiment. Python logs results to `characterisation-results.md`. If any IM3 > −50 dBc, stop and address before proceeding.

5. **Frequency accuracy**: At f = 2614 Hz (lowest), accuracy is ±0.093 Hz → ratio error ±0.004%. At f = 9574 Hz (highest), ±0.001%. Both negligible.
