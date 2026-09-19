# Plan C — AD9833 Dual-DDS Circuit Design (Rev 2)

*Revised 2026-09-12 per Grok review feedback. Major change: shared master clock.*

## Architecture Overview

```
                    Arduino Mega (5V/3.3V)
                    ┌──────────────────┐
                    │  SPI: CLK (52)   │
                    │  SPI: MOSI (51)  │
                    │  CS_A (48)       │──── to DDS A
                    │  CS_B (46)       │──── to DDS B
                    │  TRIG_OUT (44)   │──── to Scope CH4 (trigger)
                    │  3.3V            │──── (DO NOT USE — see Power)
                    │  GND             │
                    └──────────────────┘
```

## CRITICAL: Shared Master Clock

### Why This Matters

Rev 1 used independent onboard crystals (±50 ppm each). This causes:
- Up to ~2.5 kHz offset at 25 MHz between the two DDS chips
- Continuous phase drift between channels
- The two DDS outputs are **frequency-incoherent** — their ratio is never exactly a:b

For a controlled interference experiment, both DDS must derive frequencies from the **same clock** so that a programmed 3:2 ratio is *exactly* 3:2, not 3.00007:2.00003. Without this, any "coherence" metric measures crystal matching, not ratio physics.

### Implementation: External 25 MHz TCXO → Both MCLK Pins

**Recommended approach:** Use a single external 25 MHz oscillator driving both AD9833 MCLK inputs.

#### AD9833 MCLK Pin Access on Breakout Boards

The AD9833 datasheet specifies MCLK (pin 5) as a **digital input**. Common breakout boards (e.g., the green "AD9833 Signal Generator Module" from AliExpress/eBay) include:
- An onboard 25 MHz crystal connected between MCLK and the internal oscillator circuit
- The MCLK pin is typically **accessible on the header** or via a pad

**To use an external clock:**
1. **Desolder the onboard crystal** from both modules (or cut one leg)
2. Connect external oscillator output to both MCLK pins
3. The AD9833's internal oscillator amplifier is overridden by driving MCLK directly

**Alternative (if desoldering is impractical):** Some modules bring MCLK to a test pad. Wire the external clock there. The external oscillator will override the crystal if it has sufficient drive strength (the onboard crystal presents ~10-20 pF load, easily swamped by a CMOS oscillator output).

#### Clock Source Selection

| Option | Pros | Cons |
|--------|------|------|
| **25 MHz TCXO module** (e.g., SiT8008, ±2.5 ppm) | Excellent stability, clean output, drop-in | ~$3-5, needs 3.3V supply |
| **25 MHz crystal oscillator can** (±50 ppm) | Cheap, simple | Same tolerance as onboard, but *shared* eliminates relative error |
| **Wire MCLK from module A to module B** | Zero extra parts | Module A's crystal quality limits both; potential signal integrity issues with long wire |

**Recommendation:** 25 MHz crystal oscillator can (full-size or SMD). Even ±50 ppm is fine — what matters is that both DDS see the *identical* clock edge. A TCXO is better if absolute frequency accuracy matters, but for ratio experiments it doesn't.

#### Wiring

```
    External 25 MHz Oscillator
    ┌──────────┐
    │  VCC ────┼── +3.3V
    │  GND ────┼── GND
    │  OUT ────┼──┬── MCLK pin, DDS A (crystal removed)
    │          │  └── MCLK pin, DDS B (crystal removed)
    └──────────┘
```

Keep MCLK traces short and direct. At 25 MHz the wavelength is 12 m — even 10 cm of wire is electrically short. No termination needed on breadboard. On PCB, a series 33 Ω resistor at the source helps with ringing.

## PCB vs Breadboard: Recommendation

**Recommendation: Start on breadboard, design PCB in parallel.**

### Analysis

At our operating frequencies (1–10 kHz), breadboard parasitics are negligible:
- Stray capacitance ~2 pF per node → impedance at 10 kHz is ~8 MΩ (irrelevant)
- Contact resistance ~10-50 mΩ (irrelevant vs 3.3 kΩ filter R)
- Crosstalk between adjacent rows is immeasurable at audio frequencies

The 25 MHz clock is the only high-frequency signal, and it only travels from oscillator to MCLK pins (short runs).

**However, a PCB provides:**
1. **Repeatability** — rebuild from Gerbers, not from a photo of a breadboard
2. **Credibility** — reviewers take a PCB more seriously than a breadboard
3. **Ground plane** — proper return path for clock signals
4. **Matched summing resistors** — 0.1% SMD resistors are easier to source than hand-matching through-hole
5. **Mechanical stability** — no intermittent contacts during a 45-minute test run

**Practical timeline:** JLCPCB 5-day fab + ~10 days shipping to SA = ~2–3 weeks. Design the PCB now, build breadboard prototype immediately, validate the experiment, then switch to PCB for the "publication-quality" dataset.

### KiCad Schematic Structure (if PCB)

```
Sheet 1: Top-level
  ├── Power: 5V in (barrel jack or USB) → AMS1117-3.3 → 3.3V rail
  │         Decoupling: 10µF + 100nF at regulator, 100nF at each IC VCC
  │
  ├── Clock: 25 MHz oscillator can → MCLK_A, MCLK_B (series 33Ω each)
  │
  ├── DDS_A: AD9833BRMZ (MSOP-10)
  │         MCLK ← clock net
  │         FSYNC ← CS_A (Arduino pin 48)
  │         SCLK ← SCK (Arduino pin 52)
  │         SDATA ← MOSI (Arduino pin 51)
  │         VOUT → LP filter A → summing R_A
  │         VDD: 3.3V + 100nF + 10µF
  │         CAP/2.5V: 100nF to GND (internal reference bypass)
  │         COMP: 10nF to GND (DAC compensation)
  │
  ├── DDS_B: (identical to DDS_A, CS_B on pin 46)
  │
  ├── Filters: 2× RC low-pass (3.3kΩ + 1nF, fc≈48 kHz)
  │
  ├── Summer: 2× 10kΩ (0.1% tolerance) → summed output
  │           Optional: 2× test points before summing R for individual channel measurement
  │
  ├── Connectors:
  │   - Arduino Mega header (SPI + CS + trigger + power)
  │   - 3× SMA or BNC for scope (CH_A, CH_B, SUM)
  │   - 1× SMA/BNC for trigger
  │
  └── Ground plane: solid pour on bottom layer, via-stitched
```

**Board size estimate:** 50×40 mm, 2-layer. JLCPCB cost: ~$2 for 5 boards + $15 shipping.

## Power Supply: Separate 3.3V Regulator

**Do NOT use Arduino's 3.3V pin.** It's rated only 50 mA; two AD9833s plus the external oscillator draw ~25 mA total but current transients during SPI writes can cause supply glitches.

**Use: AMS1117-3.3 LDO regulator**
- Input: Arduino 5V pin (USB-powered, 500 mA available)
- Output: 3.3V rail for both AD9833 modules + external oscillator
- Decoupling: 10 µF electrolytic + 100 nF ceramic on input and output

## Output Filtering: RC Low-Pass (per channel)

### Design: fc ≈ 48 kHz
- R = 3.3 kΩ, C = 1 nF (C0G/NP0 dielectric)
- At 10 kHz: −0.17 dB (negligible)
- At 25 MHz: −54 dB (clock suppressed)
- AD9833 output impedance is 200 Ω — the 3.3 kΩ is >>200 Ω, loading minimal

No active filter needed. Op-amp would add its own distortion — counterproductive for an experiment measuring spectral purity.

## Summing Network

Two matched 10 kΩ resistors (0.1% tolerance if available):

```
DDS A filtered ──[10kΩ]──┬── Summed Output → Scope CH3
                          │
DDS B filtered ──[10kΩ]──┘
```

Output impedance: 5 kΩ. Rigol DS1054Z input: 1 MΩ — negligible loading.

**Linearity note:** This is a passive resistive summer. It's inherently linear — no intermodulation products from the summer itself. Any IM products measured at the output come from: (a) DDS nonlinearity, (b) scope ADC nonlinearity, or (c) parasitic nonlinear junctions (corroded contacts, semiconductor junctions in the breadboard — unlikely but testable). See characterisation protocol Step 3b.

## Complete Schematic (Rev 2)

```
                         +5V (from Arduino USB)
                          │
                    ┌─────┴─────┐
                    │ AMS1117   │
                    │   3.3V    │
                    └─────┬─────┘
              10µF+100nF  │  10µF+100nF
                 ┌──┤     │     ├──┐
                GND │   +3.3V   │ GND
                    │     │     │
           ┌────────┤     │     ├────────┐
           │        │     │     │        │
     ┌─────┴─────┐  │     │     │  ┌─────┴─────┐
     │ 25MHz OSC │  │     │     │  │           │
     │  VCC──────┤  │     │     │  │           │
     │  OUT──────┼──┼─────┼─────┼──┤           │
     │  GND──────┤  │     │     │  │           │
     └───────────┘  │     │     │  │           │
           │        │     │     │  │           │
     ┌─────┴────┐   │     │     │  ┌─────┴────┐
     │ AD9833 A │   │     │     │  │ AD9833 B │
     │ (crystal │   │     │     │  │ (crystal │
     │ removed) │   │     │     │  │ removed) │
     │ VCC──────┼───┘   +3.3V  └───┼────VCC   │
     │ GND──────┼──GND         GND─┼────GND   │
     │ SCLK─────┼── pin 52 ───────┼────SCLK  │
     │ SDATA────┼── pin 51 ───────┼────SDATA  │
     │ FSYNC────┼── pin 48         │          │
     │          │           pin 46─┼────FSYNC │
     │ VOUT─────┤                  ├────VOUT  │
     └──────────┘                  └──────────┘
          │                              │
     [3.3kΩ]─┬─ CH1              [3.3kΩ]─┬─ CH2
            [1nF]                        [1nF]
             │                            │
            GND                          GND
          │                              │
     [10kΩ]──────────┬──────────[10kΩ]
                     │
                     ├── Scope CH3 (summed)
                    GND

     Arduino pin 44 ── Scope CH4 (trigger)
```

## Bill of Materials

| Qty | Component | Value | Notes |
|-----|-----------|-------|-------|
| 2 | AD9833 DDS module | — | Breakout boards. ~$3-5 each. Must desolder onboard crystal. |
| 1 | 25 MHz crystal oscillator | CMOS output, 3.3V | Full-can or SMD. This replaces both onboard crystals. |
| 1 | Arduino Mega 2560 | — | Already have |
| 1 | AMS1117-3.3 | 3.3V LDO | Or pre-built 3.3V reg module |
| 2 | Resistor | 3.3 kΩ (1%) | LP filter, metal film |
| 2 | Capacitor | 1 nF C0G/NP0 | LP filter |
| 2 | Resistor | 10 kΩ (0.1% if possible) | Summing network. Measure and hand-match if using 1% |
| 2 | Capacitor | 10 µF electrolytic | Power decoupling |
| 4 | Capacitor | 100 nF ceramic | Decoupling (2× IC VCC, 2× regulator) |
| 2 | Resistor | 33 Ω | Series damping on MCLK lines (PCB only; optional on breadboard) |
| 1 | Breadboard | Full-size | Prototype phase |
| ~20 | Jumper wires | M-M | Assorted |
| 4 | Scope probes | — | Already have (DS1054Z) |

**Estimated cost:** ~$15-25 (AD9833 modules from AliExpress, oscillator can from DigiKey/LCSC)

## Layout Guidelines

Same as Rev 1 with additions:
1. **Clock wiring**: Keep oscillator output to MCLK pins as short as possible. Both wires similar length (matching not critical at 25 MHz on breadboard, but good practice).
2. **Crystal removal**: Use hot air or solder wick. Don't damage pads — MCLK pad must remain solderable/wireable.
3. **Star grounding**: Single ground bus, all grounds to one point.
4. **Separate digital/analog zones**: SPI wires top half, filters and summer bottom half.
5. **Decoupling caps**: 100 nF directly adjacent to each AD9833 VCC pin.
6. **Scope probe grounds**: Shortest possible ground leads.
7. **Anti-hum (Grok)**: 50 Hz mains pickup is real at ~400 mVpp signal levels. Use USB power bank (not wall adapter) for Arduino if possible. Record 50 Hz amplitude in every FFT as exclusion metric.
8. **25 MHz radiated pickup**: Clock can radiate into analog section on breadboard. Keep clock wires physically separated from filter/summer. RC filter handles conducted feedthrough (−54 dB) but not radiated. If 25 MHz appears in summed output, add shielding or second filter stage.
