# Plan C Analog Replication — Test Matrix (Rev 2.1)

*Revised 2026-09-12. V3 falsification test design. Corrected Class B cells with Grok-identified CC coprime pairs.*

## Purpose: V3 Falsification

**This is not a discovery experiment.** Plan C exists to close V3 cleanly.

The V3 board (GreenPAK square-wave dividers) showed apparent differences between "prime" and "non-prime" frequency ratios. But square waves contain odd-harmonic combs — a ÷3 divider and a ÷4 divider have fundamentally different spectral content regardless of any "prime effect." The V3 result was almost certainly the harmonic comb, not ratio physics.

Plan C eliminates the harmonic confound using pure sine waves (AD9833 DDS, THD < −60 dBc). The **expected outcome is null** (Outcome 3: no difference between prime and composite ratios). This is the default prediction of linear circuit theory — a resistive summer is an LTI system with transfer function H(f). It does not know whether f is prime.

> **Key insight:** Prime structure in integer-quantised systems (strings, pipes, crystals) is real mathematics — Euler's harmonic lattice, irreducible generators. But it requires **boundary conditions** that create an integer spectrum. A resistor summer provides no boundary conditions. FTA has nothing to act on.

If a positive result appears, the first response is to **debug the signal chain** (DDS spurs, ADC nonlinearity, grounding), not to write ontology.

## Design Philosophy

> **Does the primality of the numerator and denominator matter, or only their coprimality (and the resulting ratio)?**

To answer this, we need **coprime composites** as controls: pairs like 9:8 where both numbers are composite but GCD=1. If 3:2 behaves differently from 9:8 *after matching geometric mean, beat frequency, and ratio size*, that's evidence for a prime-specific effect. If they're identical, the effect (if any) is about coprimality/commensurability, not primality.

## Geometric Mean Target: 5000 Hz

For ratio a:b, with geometric mean G = 5000 Hz:
- f1 = G × √(a/b)
- f2 = G × √(b/a)
- f1 × f2 = G² = 25,000,000 for every pair

## The Five Strata

### Stratum 1: Prime:Prime, Coprime — The Claimed Effect

Both numerator and denominator are prime. This is the hypothesis under test.

| ID | Ratio | f1 (Hz) | f2 (Hz) | GM | |f1−f2| (Hz) | ln(a/b) | Full Period (ms) |
|----|-------|---------|---------|------|-------------|----------|------------------|
| PP1 | 3:2 | 6123.7 | 4082.5 | 5000 | 2041.2 | 0.405 | 0.490 |
| PP2 | 5:3 | 6454.9 | 3872.9 | 5000 | 2582.0 | 0.511 | 0.387 |
| PP3 | 7:5 | 5916.1 | 4226.5 | 5000 | 1689.6 | 0.336 | 0.592 |
| PP4 | 11:7 | 6267.8 | 3989.5 | 5000 | 2278.3 | 0.452 | 0.439 |
| PP5 | 13:11 | 5435.5 | 4598.3 | 5000 | 837.2 | 0.167 | 1.195 |
| PP6 | 7:3 | 7637.6 | 3273.3 | 5000 | 4364.3 | 0.847 | 0.229 |
| PP7 | 5:2 | 7905.7 | 3162.3 | 5000 | 4743.4 | 0.916 | 0.211 |
| PP8 | 11:3 | 9574.3 | 2613.5 | 5000 | 6960.8 | 1.299 | 0.144 |

### Stratum 2: Composite:Composite, Coprime — THE KILLER CONTROL

Both numerator and denominator are composite, but GCD=1. These pairs are coprime (so they produce clean beat patterns) but have NO prime factors in the ratio position. If primality matters, these should differ from Stratum 1.

| ID | Ratio | f1 (Hz) | f2 (Hz) | GM | |f1−f2| (Hz) | ln(a/b) | Full Period (ms) |
|----|-------|---------|---------|------|-------------|----------|------------------|
| CC1 | 9:8 | 5303.3 | 4714.0 | 5000 | 589.3 | 0.118 | 1.697 |
| CC2 | 25:16 | 6250.0 | 4000.0 | 5000 | 2250.0 | 0.446 | 0.444 |
| CC3 | 9:4 | 7500.0 | 3333.3 | 5000 | 4166.7 | 0.811 | 0.240 |
| CC4 | 15:8 | 6846.5 | 3651.5 | 5000 | 3195.0 | 0.629 | 0.313 |
| CC5 | 25:9 | 8333.3 | 3000.0 | 5000 | 5333.3 | 1.022 | 0.188 |
| CC6 | 49:25 | 7000.0 | 3571.4 | 5000 | 3428.6 | 0.674 | 0.292 |
| CC7 | 36:25 | 6000.0 | 4166.7 | 5000 | 1833.3 | 0.365 | 6.000 |
| CC8 | 49:32 | 6187.2 | 4040.6 | 5000 | 2146.6 | 0.426 | 7.923 |
| CC9 | 27:16 | 6495.2 | 3849.0 | 5000 | 2646.2 | 0.523 | 4.157 |

### Stratum 3: Prime:Composite, Coprime — Primality vs Coprimality

One factor is prime, one is composite. Coprime. Tests whether having *one* prime matters.

| ID | Ratio | f1 (Hz) | f2 (Hz) | GM | |f1−f2| (Hz) | ln(a/b) | Full Period (ms) |
|----|-------|---------|---------|------|-------------|----------|------------------|
| PC1 | 5:4 | 5590.2 | 4472.1 | 5000 | 1118.0 | 0.223 | 0.894 |
| PC2 | 11:8 | 5863.1 | 4264.0 | 5000 | 1599.1 | 0.318 | 0.625 |
| PC3 | 13:9 | 6009.3 | 4160.3 | 5000 | 1849.0 | 0.368 | 0.541 |
| PC4 | 7:4 | 6614.4 | 3779.6 | 5000 | 2834.8 | 0.560 | 0.353 |
| PC5 | 11:4 | 8291.6 | 3015.1 | 5000 | 5276.5 | 1.012 | 0.190 |
| PC6 | 13:4 | 9013.9 | 2773.5 | 5000 | 6240.4 | 1.179 | 0.160 |

### Stratum 4: Non-Coprime — Redundancy Test

GCD > 1, so these reduce to simpler ratios. Must produce identical results to their reduced forms. This is a **methodological consistency check**, not a physics test.

| ID | Ratio | Reduces To | f1 (Hz) | f2 (Hz) | GM | |f1−f2| (Hz) | Notes |
|----|-------|------------|---------|---------|------|-------------|-------|
| NC1 | 4:2 | 2:1 | 7071.1 | 3535.5 | 5000 | 3535.5 | Must = a 2:1 pair |
| NC2 | 9:6 | 3:2 | 6123.7 | 4082.5 | 5000 | 2041.2 | Must = PP1 |
| NC3 | 15:10 | 3:2 | 6123.7 | 4082.5 | 5000 | 2041.2 | Must = PP1 |

If NC2 ≠ PP1, something is wrong with the measurement setup. These are sanity checks.

### Stratum 5: Irrational Ratios — Quasiperiodic Control

No closed beat period. These should look "worse" on regularity metrics **by mathematical construction** — this is expected, not evidence for anything.

| ID | Ratio | f1 (Hz) | f2 (Hz) | GM | |f1−f2| (Hz) | ln(ratio) | Notes |
|----|-------|---------|---------|------|-------------|-----------|-------|
| IR1 | √2:1 | 5946.0 | 4204.5 | 5000 | 1741.5 | 0.347 | |
| IR2 | φ:1 | 6365.7 | 3926.5 | 5000 | 2439.2 | 0.481 | φ = 1.6180... |
| IR3 | e/2:1 | 5835.8 | 4283.5 | 5000 | 1552.3 | 0.306 | e/2 = 1.3591... |
| IR4 | π/2:1 | 6268.0 | 3989.4 | 5000 | 2278.6 | 0.452 | π/2 = 1.5708... |

Note: AD9833 has 0.1 Hz resolution, so irrational ratios are rational approximations with denominators ~10⁷. They are "effectively irrational" — no beat repetition within any practical capture window.

## Matched Sub-Comparisons

**This is the heart of the revised design.** Raw stratum comparisons are confounded by different beat frequencies and ratio sizes. We construct matched triplets/quartets where geometric mean, |ln(a/b)| (ratio size), and |f1−f2| (beat frequency) are all similar.

### Comparison Class A: Small Ratios (ln ≈ 0.1–0.25)

| Stratum | Pair | ln(a/b) | |f1−f2| Hz | GM |
|---------|------|---------|-----------|------|
| PP | 13:11 (PP5) | 0.167 | 837 | 5000 |
| CC | 9:8 (CC1) | 0.118 | 589 | 5000 |
| PC | 5:4 (PC1) | 0.223 | 1118 | 5000 |
| IR | e/2:1 (IR3) | 0.306 | 1552 | 5000 |

*Note: perfect matching is impossible. The smallest prime:prime ratio (13:11) has ln=0.167; the smallest composite:composite coprime (9:8) has ln=0.118. This ~40% difference in ratio size is a known limitation. Sensitivity analysis required.*

### Comparison Class B: Medium Ratios (ln ≈ 0.33–0.55) — PRIMARY HYPOTHESIS TEST

**This is the ONLY hypothesis test. All other classes interpret; Class B decides.**

Per Grok constraint #1: a single dyad is one draw. We need ≥3 matched PP vs CC cells. Using larger composites (36, 49, 27, 32, 16, 25) fills the gaps that seemed scarce with small composites alone.

#### Cell B1: ln ≈ 0.34–0.37
| Stratum | Pair | Ratio (decimal) | ln(a/b) | |f1−f2| Hz | GM | Δln from PP |
|---------|------|-----------------|---------|-----------|------|-------------|
| PP | 7:5 (PP3) | 1.400 | 0.336 | 1690 | 5000 | — |
| CC | 36:25 (CC7) | 1.440 | 0.365 | 1833 | 5000 | 0.029 |

*Δln = 0.029 (8.6%), Δbeat = 143 Hz (8.5%). Good match.*

#### Cell B2: ln ≈ 0.45 (THE CROWN JEWEL)
| Stratum | Pair | Ratio (decimal) | ln(a/b) | |f1−f2| Hz | GM | Δln from PP |
|---------|------|-----------------|---------|-----------|------|-------------|
| PP | 11:7 (PP4) | 1.571 | 0.452 | 2278 | 5000 | — |
| CC | 25:16 (CC2) | 1.563 | 0.446 | 2250 | 5000 | 0.006 |
| IR | π/2:1 (IR4) | 1.571 | 0.452 | 2279 | 5000 | 0.000 |

*Δln = 0.006 (1.3%), Δbeat = 28 Hz (1.2%). Near-perfect match. This is the primary PP-vs-CC cell.*

#### Cell B3: ln ≈ 0.51–0.52
| Stratum | Pair | Ratio (decimal) | ln(a/b) | |f1−f2| Hz | GM | Δln from PP |
|---------|------|-----------------|---------|-----------|------|-------------|
| PP | 5:3 (PP2) | 1.667 | 0.511 | 2582 | 5000 | — |
| CC | 27:16 (CC9) | 1.688 | 0.523 | 2646 | 5000 | 0.012 |
| IR | φ:1 (IR2) | 1.618 | 0.481 | 2439 | 5000 | 0.030 |

*Δln = 0.012 (2.3%), Δbeat = 64 Hz (2.5%). Excellent match.*

**All three cells have Δln < 0.03.** The earlier "scarcity" concern was wrong — it just required looking at larger composites (36=6², 27=3³, 49=7²... wait, 49=7² but 7 is prime. 49 is composite: 7×7. 32=2⁵. GCD(49,32)=1. ✓ Both composite, coprime.)

**Primary test:** Mixed-effects model over all Class B cells (B1+B2+B3), with stratum as fixed effect and cell as random effect. NOT a lone p-value on PP4 vs CC2.

### Comparison Class C: Large Ratios (ln ≈ 0.8–1.1)

| Stratum | Pair | ln(a/b) | |f1−f2| Hz | GM |
|---------|------|---------|-----------|------|
| PP | 7:3 (PP6) | 0.847 | 4364 | 5000 |
| PP | 5:2 (PP7) | 0.916 | 4743 | 5000 |
| CC | 9:4 (CC3) | 0.811 | 4167 | 5000 |
| CC | 25:9 (CC5) | 1.022 | 5333 | 5000 |
| PC | 11:4 (PC5) | 1.012 | 5277 | 5000 |

### Comparison Class D: Very Large Ratios (ln > 1.1)

| Stratum | Pair | ln(a/b) | |f1−f2| Hz | GM |
|---------|------|---------|-----------|------|
| PP | 11:3 (PP8) | 1.299 | 6961 | 5000 |
| PC | 13:4 (PC6) | 1.179 | 6240 | 5000 |

*Only two strata represented. Insufficient for cross-stratum comparison. Include for completeness but not primary analysis.*

## Analysis Window Specification

### The Window Problem

For a rational ratio a:b at frequencies f1, f2 with geometric mean G:
- **Beat period** T_beat = 1/|f1 − f2|
- **Full repetition period** T_rep = LCM(1/f1, 1/f2) = 1 / (G × |√(b/a) − √(a/b)|) × (a×b)/GCD(a,b)²

For coprime integers with large products, T_rep can be very long. A capture window that isn't an integer multiple of T_rep will show truncation artefacts that look like "irregularity" — that's windowing, not physics.

### Rule: Capture Duration Per Pair

For each rational pair:
1. Compute T_rep = LCM of the two periods
2. Capture window = N × T_rep where N ≥ 20 (for statistical stability of spectral estimates)
3. Minimum capture: 100 ms (scope/ADC practical limit)
4. Maximum capture: 5000 ms (thermal drift concern beyond this)

For irrational pairs (no finite T_rep):
- Use the **median capture duration of the matched rational comparison class**
- This ensures fair comparison: irrationals get the same observation time as their matched rationals

### Computed Capture Durations

| ID | Ratio | T_rep (ms) | N×T_rep @ N=20 (ms) | Actual Capture (ms) |
|----|-------|-----------|---------------------|---------------------|
| PP1 | 3:2 | 0.490 | 9.8 | 100 (minimum) |
| PP2 | 5:3 | 0.387 | 7.7 | 100 |
| PP3 | 7:5 | 0.592 | 11.8 | 100 |
| PP4 | 11:7 | 0.439 | 8.8 | 100 |
| PP5 | 13:11 | 1.195 | 23.9 | 100 |
| CC1 | 9:8 | 1.697 | 33.9 | 100 |
| CC2 | 25:16 | 0.444 | 8.9 | 100 |
| IR1-4 | (irrational) | ∞ | — | 100 (matched to comparison class) |

**Window rule (Grok constraint #3):** Capture duration = max(50/f₀, 100 ms) per pair, where f₀ = GCD(f₁, f₂) is the fundamental period frequency. This ensures ≥50 full sum periods for every pair.

| ID | Ratio | f₀ = GCD(f1,f2) approx (Hz) | T_sum (ms) | 50/f₀ (ms) | Capture (ms) |
|----|-------|------------------------------|-----------|-----------|-------------|
| PP4 | 11:7 | 569.6 | 1.76 | 87.8 | 100 |
| CC2 | 25:16 | 250.0 | 4.00 | 200.0 | **200** |
| PP5 | 13:11 | 418.0 | 2.39 | 119.6 | **120** |
| CC1 | 9:8 | 589.3 | 1.70 | 84.9 | 100 |

**Key:** CC2 (25:16) needs 200 ms while PP4 (11:7) needs only 100 ms. Using a fixed 100 ms would give 57 periods of PP4 but only 25 of CC2 — unfair windowing per Grok's constraint. Each pair gets its own capture duration.

For irrational pairs (no finite f₀): use the median capture duration of their matched comparison class.

Additionally capture a separate 2000 ms record per pair for high-resolution spectral analysis (0.5 Hz bins). Both captures are taken per trial.

*Note: The "long period" problem from Grok's review is relevant for pairs like 101:97 (T_rep ~ 103 ms). Our test matrix avoids such pairs — the largest product a×b is 25×16 = 400, giving manageable periods.*

## Primary Metric (Pre-Specified)

### THE metric: Residual Spectral Power (RSP)

**Definition:** Integrated power in the summed waveform spectrum *outside* the two carrier frequencies and their first-order beat products, normalised by total power, measured in a fixed resolution bandwidth.

**Frozen definition (Grok constraint #2 — do not modify after first run):**

> After amplitude-normalising the two-tone record to unit RMS per channel, notch f₁, f₂, |f₁−f₂|, and f₁+f₂ at fixed RBW = ±5 bins (±2.5 Hz at 0.5 Hz resolution). RSP = 10·log₁₀(remaining integrated power in [0, fs/2] / total power before notching), in dB.

Note: the beat product |f₁−f₂| IS notched. If it were left in, Class B pairs are matched by construction and RSP would not move — defeating the test. Higher-order products (2f₁−f₂, 2f₂−f₁) are NOT notched — they are part of the residual we're measuring.

Concretely:
1. Capture N × T_rep milliseconds of summed waveform (see window rule below)
2. Amplitude-normalise each channel to unit RMS before summing
3. Compute FFT (resolution: 0.5 Hz, i.e., 2-second windows or zero-padded)
4. Notch (zero) bins at f₁ ± 5 bins, f₂ ± 5 bins, |f₁−f₂| ± 5 bins, (f₁+f₂) ± 5 bins
5. RSP = 10·log₁₀(Σ remaining bins / Σ all bins before notching)
6. Record both the notched spectrum and the RSP scalar

**Direction of claim:** If primality enhances interference coherence, prime:prime pairs should have *lower* RSP (less spectral splatter) than composite:composite coprime pairs at matched conditions.

**Null hypothesis (H₀):** RSP(prime:prime) = RSP(composite:composite coprime) after matching geometric mean, beat frequency, and log-ratio.

### Secondary Metrics (report all, no significance testing)

1. **Crest factor** — peak/RMS of summed waveform
2. **Envelope regularity** — coefficient of variation of beat envelope peak amplitudes
3. **Cross-correlation peak** — max of normalised cross-correlation between channels
4. **Phase coherence** — circular variance of instantaneous phase difference
5. **Spectral flatness** — geometric mean / arithmetic mean of power spectrum

These are reported for transparency and future hypothesis generation, but statistical significance is judged ONLY on RSP. This prevents metric shopping.

## Summary

| Stratum | Count | Purpose |
|---------|-------|---------|
| 1. Prime:prime coprime | 8 | Hypothesis: primality enhances interference |
| 2. Composite:composite coprime | 9 | KILLER CONTROL: coprime but not prime |
| 3. Prime:composite coprime | 6 | Does one prime suffice? |
| 4. Non-coprime | 3 | Sanity/consistency check |
| 5. Irrational | 4 | Quasiperiodic negative control |
| **Total** | **30** | |

## Experimental Protocol

### Randomised Trial Ordering
- Generate random permutation of all 27 pairs before each block
- Never run all pairs from one stratum consecutively (thermal drift confound)
- Use Python-generated permutation (not Arduino `random()`)

### Phase Randomisation
- For each trial, set DDS B phase to random value from {0, π/4, π/2, 3π/4, π, 5π/4, 3π/2, 7π/4}
- Record phase offset in data log
- This prevents systematic phase-dependent artefacts

### Repetitions & Statistical Power
- **N = 8 phase draws per pair** (one at each of the 8 phase offsets)
- **M = 5 pair repeats** (complete blocks)
- Total per pair: 40 measurements
- Total trials: 30 × 40 = 1200
- At ~4 seconds per trial (0.5s settle + 0.2s short capture + 2s long capture + 1.3s processing): ~80 minutes
- Power analysis: 40 measurements per pair gives power ≈ 0.95 to detect d=0.8 at α=0.005 (Bonferroni-corrected for ~10 comparisons)

### Data Recording
- CSV: `trial, block, pair_id, stratum, ratio, f1, f2, phase_offset, capture_ms, rsp_db, crest, env_reg, xcorr, phase_coh, spec_flat, timestamp`
- Raw waveform saves (scope `:WAV:DATA?`) for offline reanalysis
- Scope screenshots for visual QA

## What Results Mean — V3 Falsification Outcomes

See `pre-registration.md` for full decision tree. **The expected outcome is Outcome 3 (null).**

| Outcome | Interpretation | Next Step |
|---------|---------------|-----------|
| 1. PP ≠ CC at matched conditions | Unexpected. Prime-specific effect on interference. **Debug signal chain first** — DDS spur differences, ADC nonlinearity at specific frequencies, grounding. If it survives debugging, it's interesting but circumscribed — NOT evidence for ONM or sopfr. | Replicate on different hardware |
| 2. PP = CC but both ≠ IR | Coprimality/commensurability effect, not primality. Rational beats are more regular than irrational — that's mathematics, not physics. | Close V3, document commensurability result |
| 3. Nothing differs (**EXPECTED**) | V3 result was the odd-harmonic comb from square waves, not frequency ratios. LTI theory confirmed. A resistor summer has no boundary conditions → no integer spectrum → FTA irrelevant. | Close V3, retire frequency-ratio claim, consider follow-up in boundary-conditioned domains (acoustic/string/cavity) |
| 4. NC ≠ their reduced forms | Measurement error. Abort and debug. | Fix apparatus |
