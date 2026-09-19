# Plan C — Characterisation Protocol (Rev 2)

*Revised 2026-09-12. Added Step 3b (IM3 measurement) and updated for shared MCLK.*

Complete these steps BEFORE running the experiment. Each step validates a component of the signal chain. Document results in `characterisation-results.md`.

**Equipment**: Rigol DS1054Z (4ch, 50 MHz, FFT mode), DMM, Arduino Mega, breadboard circuit as built.

---

## Step 1: Clock Verification (NEW)

**Goal**: Confirm shared 25 MHz clock is reaching both AD9833 modules and producing correct frequencies.

### Procedure
1. Probe MCLK input of DDS A with scope CH1 (use 10× probe for bandwidth)
2. Probe MCLK input of DDS B with scope CH2
3. Verify both show 25 MHz square wave, same amplitude, zero phase difference
4. Set both DDS to 5000.0 Hz
5. Probe VOUT of DDS A (CH1) and VOUT of DDS B (CH2)
6. With shared clock, both outputs at identical frequency should show **zero beat** (no drift)
7. Monitor for 5 minutes. Phase difference should remain constant (not drifting)

### Pass/Fail
- ❌ FAIL if MCLK amplitude differs >20% between modules (impedance/loading issue)
- ❌ FAIL if any phase drift observed at same programmed frequency (clock not shared — check wiring)
- ✅ PASS if zero beat confirmed and phase stable for 5 minutes

---

## Step 2: Single-Tone Sweep (per DDS)

**Goal**: Verify each DDS produces clean, consistent-amplitude sine waves across all test frequencies.

### Procedure
1. Disconnect the summing network (lift one leg of each 10 kΩ summing resistor)
2. Connect scope CH1 directly to DDS A filter output, CH2 to DDS B filter output
3. For each frequency in the test matrix:
   - Set DDS to frequency, wait 500 ms
   - Measure: **Vpp**, **Vrms**, **Frequency** (verify match to commanded)
   - FFT screenshot: span 0–50 kHz, note any spurs

### Frequencies to test
Subset spanning full range: 2614, 3000, 3536, 3873, 4083, 4472, 5000, 5916, 6124, 6455, 7072, 7500, 7906, 8333, 9574 Hz

### Pass/Fail
- ❌ FAIL if Vpp varies >10% across range
- ❌ FAIL if any spur > −30 dBc in FFT
- ❌ FAIL if frequency error > 1 Hz
- ✅ PASS if Vpp consistent ±5%, spurs < −40 dBc, frequency within ±0.2 Hz

---

## Step 3: Filter Characterisation

**Goal**: Verify LP filter cutoff and 25 MHz suppression.

### Procedure
1. Keep summing network disconnected
2. Set DDS A to 1 kHz. Record Vpp at filter output = V_ref
3. Sweep: 1k, 2k, 5k, 10k, 20k, 50k, 100k, 200k, 500k, 1M Hz
4. Record Vpp, calculate attenuation = 20·log₁₀(V/V_ref)

### 25 MHz Feedthrough Check
1. Set DDS A to 1 kHz
2. Scope CH1 before filter, CH2 after filter, timebase 20 ns/div
3. Compare clock feedthrough amplitude

### Pass/Fail
- ❌ FAIL if −3 dB point below 30 kHz
- ❌ FAIL if 25 MHz feedthrough visible at 1 mV/div after filter
- ✅ PASS if −3 dB at ~48 kHz, <0.5 dB loss at 10 kHz

---

## Step 3b: Summing Linearity / IM3 Measurement (NEW)

**Goal**: Verify that the resistive summer introduces no intermodulation products that could masquerade as "coherence."

### Why This Matters

A nonlinear summing junction generates intermodulation products:
- 2f1 − f2, 2f2 − f1 (IM3 — third-order, closest to carriers)
- f1 + f2, f1 − f2 (IM2 — second-order)
- Higher orders

These products depend on |f1 − f2| (frequency spacing). If the summer has even slight nonlinearity, pairs with different beat frequencies will show different amounts of spurious "coherence." This is a frequency-spacing artefact, not a ratio-physics effect — and it exactly mimics what we're trying to measure.

### Procedure

1. Reconnect summing network
2. Choose a well-separated test pair: f1 = 5000 Hz, f2 = 6000 Hz (|Δf| = 1000 Hz)
3. Set both DDS to operating level, verify amplitude matching
4. Capture 2000 ms of summed output
5. Compute FFT with resolution ≤ 1 Hz
6. Measure power at:
   - **Carriers**: 5000 Hz, 6000 Hz (reference level, 0 dBc)
   - **IM2**: 1000 Hz (f2−f1), 11000 Hz (f1+f2)
   - **IM3**: 4000 Hz (2f1−f2), 7000 Hz (2f2−f1)
   - **IM5**: 3000 Hz (3f1−2f2), 8000 Hz (3f2−2f1)
7. Record all levels relative to carrier (dBc)
8. Repeat with a close-spaced pair: f1 = 5000 Hz, f2 = 5100 Hz (|Δf| = 100 Hz)
   - IM3 products at 4900 Hz and 5200 Hz — very close to carriers
   - This tests whether IM products could contaminate RSP measurement for small-ratio pairs
9. Repeat with DDS amplitude set to 2× normal (if possible via external gain) to check nonlinearity scaling
   - True IM3 grows as cube of input level (+3 dB IM3 per +1 dB input)
   - If IM3 doesn't change with level, it's not intermodulation — it's DDS spur

### Expected Results
- Passive resistor summer is inherently linear
- IM products should be at or below the noise floor (< −60 dBc)
- If IM3 > −50 dBc, the nonlinearity is in the DDS output stage, not the summer

### If IM3 Fails
If IM3 products exceed −50 dBc:
1. **Identify source**: Disconnect summer, measure single DDS into scope. If IM-like spurs present, it's DDS nonlinearity.
2. **Mitigation A**: Reduce DDS output level (attenuator pad) — IM products fall faster than signal
3. **Mitigation B**: Replace resistive summer with a precision instrumentation amplifier (e.g., AD620 or INA128) configured as a unity-gain summing amplifier
4. **Mitigation C**: Accept and measure — include IM3 level as a covariate in statistical analysis

### Pass/Fail
- ✅ PASS if all IM products < −50 dBc at both frequency spacings
- ⚠️ WARNING if IM3 between −50 and −40 dBc (include as covariate)
- ❌ FAIL if IM3 > −40 dBc (replace summer or add attenuation)

---

## Step 4: Crosstalk

**Goal**: Verify minimal coupling between channels through the summing network.

### Procedure
1. Set DDS A to 5000 Hz, DDS B OFF
2. Measure:
   - CH1: DDS A filter output (should show 5 kHz)
   - CH2: DDS B filter output (should show nothing)
   - CH3: Summed output (5 kHz at ~half amplitude)
3. Record signal on CH2 = crosstalk
4. Repeat with B on, A off

### Pass/Fail
- ❌ FAIL if crosstalk > −30 dB
- ✅ PASS if crosstalk < −40 dB

---

## Step 5: Phase Stability (Revised for Shared Clock)

**Goal**: Confirm that shared clock eliminates inter-channel drift.

### Procedure
1. Set both DDS to 5000.0 Hz, DDS B phase = 0
2. Scope: CH1 = DDS A, CH2 = DDS B, trigger on CH1
3. Measure phase (CH1→CH2) every 60 seconds for 30 minutes
4. Repeat at 3000 Hz and 8000 Hz

### Expected Results (Shared Clock)
- Phase difference should be **constant** (no drift)
- Small fixed offset possible due to SPI write timing (both channels programmed sequentially)
- No beat observed at identical frequency — this is THE validation of the shared clock

### Pass/Fail
- ✅ PASS if phase drift < 1° over 30 minutes
- ❌ FAIL if any drift observed (clock not properly shared — recheck wiring)
- ❌ FAIL if sudden phase jumps > 5° (SPI or power issue)

---

## Step 6: Amplitude Matching

**Goal**: Trim both channels to equal RMS output.

### Procedure

#### Method A: Component Selection (Preferred)
1. Set both DDS to 5000 Hz
2. Measure Vpp on each channel after filter (before summing R)
3. Swap/select resistors for closest match
4. Target: matched within 1%

#### Method B: Trimpot
If Method A insufficient: 10 kΩ trimpot in series with 4.7 kΩ fixed resistor replacing one summing R.

#### Verification
Verify at 3000, 5000, 8000 Hz. Record mismatch percentage.

### Pass/Fail
- ❌ FAIL if mismatch > 5% after trimming
- ⚠️ WARNING if 2–5%
- ✅ PASS if < 2% across frequency range

---

## Characterisation Summary Template

```markdown
# Characterisation Results — [DATE]

## Step 1: Clock Verification
MCLK amplitude DDS A: _____ Vpp    DDS B: _____ Vpp
Phase drift at 5000 Hz over 5 min: _____ degrees
Zero beat confirmed: YES / NO

## Step 2: Single-Tone Sweep
| Freq (Hz) | DDS A Vpp | DDS B Vpp | Notes |
|-----------|-----------|-----------|-------|
| ...       |           |           |       |

## Step 3: Filter
| Freq (Hz) | Vpp (mV) | Attenuation (dB) |
|-----------|----------|-------------------|
| 1000      |          | 0 (ref)           |
25 MHz feedthrough: _____ mVpp → _____ mVpp

## Step 3b: IM3 Measurement
### Wide spacing (f1=5000, f2=6000)
| Product | Freq (Hz) | Level (dBc) |
|---------|-----------|-------------|
| IM2-    | 1000      |             |
| IM3-    | 4000      |             |
| Carrier | 5000      | 0 (ref)     |
| Carrier | 6000      | 0 (ref)     |
| IM3+    | 7000      |             |
| IM2+    | 11000     |             |

### Close spacing (f1=5000, f2=5100)
| Product | Freq (Hz) | Level (dBc) |
|---------|-----------|-------------|
| IM3-    | 4900      |             |
| Carrier | 5000      | 0 (ref)     |
| Carrier | 5100      | 0 (ref)     |
| IM3+    | 5200      |             |

## Step 4: Crosstalk
A→B: _____ dB     B→A: _____ dB

## Step 5: Phase Stability (Shared Clock)
Phase drift over 30 min: _____ degrees
Phase jumps: YES / NO

## Step 6: Amplitude Matching
| Freq (Hz) | Vpp_A | Vpp_B | Mismatch (%) |
|-----------|-------|-------|--------------|
| 3000      |       |       |              |
| 5000      |       |       |              |
| 8000      |       |       |              |
Method: [component selection / trimpot]

## Overall: PASS / FAIL / CONDITIONAL
Notes:
```

---

## Estimated Time

| Step | Duration |
|------|----------|
| 1. Clock verification | 15 min |
| 2. Single-tone sweep | 45 min |
| 3. Filter char | 30 min |
| 3b. IM3 measurement | 30 min |
| 4. Crosstalk | 15 min |
| 5. Phase stability | 35 min |
| 6. Amplitude matching | 30 min |
| **Total** | **~3.5 hours** |

Do this once when the circuit is first built. Repeat Step 3b if any analog component is changed.
