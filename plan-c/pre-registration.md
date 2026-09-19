# Plan C — Pre-Registration Document (V3 Falsification Test)

**Title:** V3 Falsification: Do prime-integer frequency ratios produce measurably different analog interference patterns than coprime-composite ratios in a linear summing circuit?

**Date:** 2026-09-12
**Version:** 1.1 (Class B cells corrected)
**Investigators:** Adrian Blomkamp
**Status:** PRE-REGISTERED (before any experimental data collected)

---

## 1. Background & Motivation

Previous experiments (V3, GreenPAK-based square-wave dividers) showed apparent differences in interference patterns between "prime" and "non-prime" frequency ratios. However, V3 used square waves — the odd-harmonic content means different divider ratios have fundamentally different spectral content. Any observed "prime effect" was almost certainly the harmonic comb, not the ratio.

**This experiment is a V3 falsification test, not a discovery experiment.** The expected outcome is null — linear circuit theory predicts no dependence on prime factorisation. A resistive summer is an LTI system: H(f), not H(f, isprime). There are no boundary conditions to create an integer spectrum, so the Fundamental Theorem of Arithmetic is irrelevant.

Plan C eliminates the harmonic confound using pure sine waves (AD9833 DDS, THD < −60 dBc). If the null result obtains, V3 is closed cleanly. If a positive result appears, the first step is to **debug the signal chain**, not write ontology.

**Note on the electron-membrane argument:** The claim that electron membranes "respond to" prime structure is not an independent prediction mechanism — it is LTI theory restated in philosophical language. Superposition in a linear medium depends on H(f), period. Prime structure in nature is real mathematics (Euler's harmonic lattice) but requires boundary conditions (strings, pipes, crystals) that a resistor summer does not provide.

## 2. Hypotheses

### Primary Null Hypothesis (H₀)
After matching geometric mean, beat frequency |f1−f2|, and log-ratio ln(a/b), there is no difference in Residual Spectral Power (RSP) between:
- **Stratum 1** (prime:prime coprime) pairs, and
- **Stratum 2** (composite:composite coprime) pairs

### Primary Alternative Hypothesis (H₁)
RSP differs between Stratum 1 and Stratum 2 at matched conditions.

**Direction:** If primality enhances interference "coherence," Stratum 1 should have *lower* RSP (less spectral energy outside carriers and beat products).

### Secondary Hypotheses (exploratory, not confirmatory)
- H₂: Stratum 1 ≠ Stratum 3 (prime:composite) → does one prime suffice?
- H₃: All coprime strata (1,2,3) ≠ Stratum 5 (irrational) → rational vs irrational
- H₄: Stratum 4 (non-coprime) = their reduced forms → sanity check

## 3. Test Pairs & Stratum Assignments

### Stratum 1: Prime:Prime, Coprime (n=8)
| ID | Ratio | f1 (Hz) | f2 (Hz) | ln(a/b) | Class |
|----|-------|---------|---------|---------|-------|
| PP1 | 3:2 | 6123.7 | 4082.5 | 0.405 | B |
| PP2 | 5:3 | 6454.9 | 3872.9 | 0.511 | B |
| PP3 | 7:5 | 5916.1 | 4226.5 | 0.336 | B |
| PP4 | 11:7 | 6267.8 | 3989.5 | 0.452 | B |
| PP5 | 13:11 | 5435.5 | 4598.3 | 0.167 | A |
| PP6 | 7:3 | 7637.6 | 3273.3 | 0.847 | C |
| PP7 | 5:2 | 7905.7 | 3162.3 | 0.916 | C |
| PP8 | 11:3 | 9574.3 | 2613.5 | 1.299 | D |

### Stratum 2: Composite:Composite, Coprime (n=9)
| ID | Ratio | f1 (Hz) | f2 (Hz) | ln(a/b) | Class |
|----|-------|---------|---------|---------|-------|
| CC1 | 9:8 | 5303.3 | 4714.0 | 0.118 | A |
| CC2 | 25:16 | 6250.0 | 4000.0 | 0.446 | B |
| CC3 | 9:4 | 7500.0 | 3333.3 | 0.811 | C |
| CC4 | 15:8 | 6846.5 | 3651.5 | 0.629 | C |
| CC5 | 25:9 | 8333.3 | 3000.0 | 1.022 | C |
| CC6 | 49:25 | 7000.0 | 3571.4 | 0.674 | C |
| CC7 | 36:25 | 6000.0 | 4166.7 | 0.365 | B |
| CC8 | 49:32 | 6187.2 | 4040.6 | 0.426 | B |
| CC9 | 27:16 | 6495.2 | 3849.0 | 0.523 | B |

### Stratum 3: Prime:Composite, Coprime (n=6)
| ID | Ratio | f1 (Hz) | f2 (Hz) | ln(a/b) | Class |
|----|-------|---------|---------|---------|-------|
| PC1 | 5:4 | 5590.2 | 4472.1 | 0.223 | A |
| PC2 | 11:8 | 5863.1 | 4264.0 | 0.318 | B |
| PC3 | 13:9 | 6009.3 | 4160.3 | 0.368 | B |
| PC4 | 7:4 | 6614.4 | 3779.6 | 0.560 | B |
| PC5 | 11:4 | 8291.6 | 3015.1 | 1.012 | C |
| PC6 | 13:4 | 9013.9 | 2773.5 | 1.179 | D |

### Stratum 4: Non-Coprime (n=3) — Sanity check only
| ID | Ratio | Reduces To | f1 (Hz) | f2 (Hz) |
|----|-------|------------|---------|---------|
| NC1 | 4:2 | 2:1 | 7071.1 | 3535.5 |
| NC2 | 9:6 | 3:2 | 6123.7 | 4082.5 |
| NC3 | 15:10 | 3:2 | 6123.7 | 4082.5 |

### Stratum 5: Irrational (n=4) — Negative control
| ID | Ratio | f1 (Hz) | f2 (Hz) | ln(ratio) | Class |
|----|-------|---------|---------|-----------|-------|
| IR1 | √2:1 | 5946.0 | 4204.5 | 0.347 | A |
| IR2 | φ:1 | 6365.7 | 3926.5 | 0.481 | B |
| IR3 | e/2:1 | 5835.8 | 4283.5 | 0.306 | A |
| IR4 | π/2:1 | 6268.0 | 3989.4 | 0.452 | B |

**Total: 30 pairs**

## 4. Primary Metric: Residual Spectral Power (RSP)

### Definition
1. Capture 2000 ms of summed waveform (CH3)
2. Amplitude-normalise each channel to unit RMS before summing
3. Compute FFT (resolution: 0.5 Hz)
4. Identify and zero bins at: f1, f2, |f1−f2|, f1+f2, 2f1−f2, 2f2−f1, and their ±2 Hz neighbourhoods
5. RSP = 10·log₁₀(remaining power / total power) in dB

### Why This Metric
RSP measures spectral "mess" — energy that isn't explained by the two carriers and their first-order interaction. If prime ratios produce "cleaner" interference, they should have less unexplained spectral energy.

### Direction
H₁ predicts: RSP(Stratum 1) < RSP(Stratum 2)

## 5. Sample Size

- **N = 8 phase offsets** per pair (exhaustive: 0°, 45°, 90°, ..., 315°)
- **M = 5 complete blocks** (full randomised permutations)
- **Total per pair:** 40 measurements
- **Total trials:** 30 × 40 = 1200

### Power Analysis
- Primary comparison: 8 PP pairs (320 measurements) vs 9 CC pairs (360 measurements)
- Within-comparison-class: Class B has 3 PP (PP2,PP3,PP4), 3 CC (CC2,CC7,CC9), 2 IR (IR2,IR4)
- At α = 0.005 (Bonferroni for ~10 planned comparisons), 40 measurements per pair:
  - Detectable effect size d ≈ 0.6 at 80% power (medium-large)
  - If V3-scale effects exist (d > 1.0), power > 99%

## 6. Exclusion Rules

A trial is excluded if ANY of:
1. **Spur floor** > −30 dBc in single-channel FFT (DDS malfunction)
2. **Amplitude mismatch** > 3 dB between channels at carrier frequencies
3. **IM3 products** > −40 dBc (nonlinear summing artefact)
4. **Scope clipping** (any sample at ADC rail)
5. **Trigger failure** (capture window doesn't align with trigger pulse)
6. **Temperature excursion** > 5°C during a block (log ambient temperature)

If > 10% of trials in a block are excluded, discard the entire block and repeat.

### Spur-Matched Abort Rule (Grok Constraint #4)
Before running the pair matrix, characterise isolated-tone SFDR and two-tone IM3 at every test frequency. If the SFDR or IM3 level differs by more than **6 dB** between the PP frequencies and CC frequencies used in any Class B cell, that cell is **invalid** — any RSP difference could be "the dirtier DDS word." Shared MCLK makes this measurable but does not make it zero.

Specifically:
- **Cell B1:** SFDR at 5916.1, 4226.5 Hz (PP3: 7:5) vs 6000.0, 4166.7 Hz (CC7: 36:25)
- **Cell B2:** SFDR at 6267.8, 3989.5 Hz (PP4: 11:7) vs 6250.0, 4000.0 Hz (CC2: 25:16)
- **Cell B3:** SFDR at 6454.9, 3872.9 Hz (PP2: 5:3) vs 6495.2, 3849.0 Hz (CC9: 27:16)
- If |SFDR_PP − SFDR_CC| > 6 dB for any cell → that cell is invalid
- Repeat for all Class B cells
- If ALL Class B cells fail the spur-match test → experiment cannot answer the primality question with this hardware. Report as inconclusive.

## 7. Statistical Analysis Plan

### Primary Test — CLASS B ONLY (Grok Constraint #5)
Mixed-effects model over Class B cells: RSP ~ stratum (fixed) + cell (random) + phase (random). One test. α = 0.005.

Class B is the only hypothesis test. Classes A, C, D interpret. Irrationals test commensurability. Non-coprime vs reduced form is a sanity check. Do not pool strata and hunt.

### Secondary Tests (exploratory, no significance claims)
- Kruskal-Wallis across all 5 strata within Class B
- Descriptive comparison of Classes A, C, D (effect sizes and CIs, no p-values)
- Irrational vs rational comparison (commensurability question, separate from primality)
- All secondary — report for transparency, do not claim significance

### Confound Checks
- Verify NC pairs match their reduced forms (paired t-test, expect p > 0.5)
- Test for block effects (has the apparatus drifted?)
- Test for order effects (does position in sequence predict RSP?)
- Test RSP vs |f1−f2| correlation within each stratum (is beat frequency a confound despite matching?)

## 8. Decision Tree: V3 Falsification Outcomes

**The expected outcome is Outcome 3 (null).** This is the default prediction of linear circuit theory.

### Outcome 1: Stratum 1 ≠ Stratum 2 (at matched conditions) — UNEXPECTED
**Interpretation:** There is a measurable effect of prime-integer frequency ratios on analog interference patterns that cannot be explained by coprimality alone.

**First response: DEBUG.** Before interpreting as physics:
- Check DDS spur profiles at each frequency — do PP frequencies happen to hit cleaner DDS words?
- Check scope ADC nonlinearity at specific frequency relationships
- Check grounding, power supply modulation
- Replicate with different hardware (different DDS chip, different scope)

**If it survives debugging:** Interesting but circumscribed. NOT evidence for ONM or sopfr. NOT evidence that materials "respond to" prime structure. It would merit investigation into mechanism, not ontological claims.

### Outcome 2: Stratum 1 = Stratum 2, but both ≠ Stratum 5
**Interpretation:** Coprimality/commensurability effect, not primality. Rational beats are more regular than irrational — that's mathematics, not physics. V3 was either the harmonic comb or a mislabelled coprimality effect.

**What to do:** Close V3. Document the commensurability result for completeness.

### Outcome 3: No differences between any strata — EXPECTED (V3 FALSIFIED)
**Interpretation:** Two pure sine waves summed linearly produce interference independent of their ratio's arithmetic properties. LTI theory confirmed. A resistor summer has no boundary conditions, no integer spectrum, FTA is irrelevant. The V3 result was entirely the odd-harmonic comb from square waves.

**What to do:** Close V3. Retire the frequency-ratio claim honestly. Consider follow-up experiments in **boundary-conditioned domains** (acoustic cavities, vibrating strings, crystal resonators) where integer quantisation actually exists and primes are genuine irreducible generators.

### Outcome 4: NC pairs ≠ their reduced forms — APPARATUS FAILURE
**Interpretation:** Measurement error. 9:6 and 3:2 produce physically identical signals.

**What to do:** Debug. Do not interpret any other results until resolved.

## 9. Transparency Commitments

1. **All raw data** will be published (waveform captures, CSVs, scope screenshots)
2. **All code** will be published (Arduino firmware, Python analysis scripts)
3. **This pre-registration document** will be timestamped and not modified after data collection begins
4. **Negative results** will be reported with equal prominence to positive results
5. **Secondary metrics** will be reported in supplementary material regardless of significance

## 10. Apparatus Summary

- **Signal generation:** 2× AD9833 DDS, shared 25 MHz external clock
- **Summing:** Matched 10 kΩ resistive summer (passive, linear)
- **Filtering:** 2× RC low-pass, fc ≈ 48 kHz
- **Measurement:** Rigol DS1054Z, 4 channels, SCPI-automated waveform capture
- **Control:** Arduino Mega 2560 (SPI master)
- **Analysis:** Python (NumPy, SciPy) on Mac mini

See `circuit-design.md`, `characterisation-protocol.md`, `firmware-outline.md` for details.

---

*"The Truth shall set us Free." — This is a falsification test, not a confirmation hunt.*
*The expected outcome is null. A null result closes V3 cleanly and lets us move on.*
*A positive result triggers debugging, not ontology.*
