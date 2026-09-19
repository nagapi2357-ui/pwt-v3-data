# Corrigendum: V3 Experimental Results

**Applies to:** Sutton, A. (2026). *Prime Wave Theory — V3 Experimental Results.* Zenodo. DOI: [10.5281/zenodo.20637347](https://doi.org/10.5281/zenodo.20637347)

**See also:** Sutton, A. (2026). *Prime Resonance Theory: From Factorisation to Frequency.* Zenodo. DOI: [10.5281/zenodo.20541350](https://doi.org/10.5281/zenodo.20541350)

**Date:** 19 September 2026

---

## Summary

The V3 experimental results reported statistically significant differences between prime-ratio and composite-ratio frequency pairs in analog interference patterns: +28% amplitude (Vpp), +18% sharpness (spectral power ratio), and +22% coherence (cross-correlation). A subsequent pre-registered replication experiment (Plan C) using improved methodology has failed to reproduce these results. **The original V3 claims should be considered unreliable**, and the observed effects are most parsimoniously explained by a harmonic confound in the V3 apparatus.

## What Was Claimed (V3)

The V3 experiment used GreenPAK-generated square-wave frequency dividers driving 12 radial analog cells on a torsion ring PCB. It reported that frequency pairs with prime-integer ratios produced measurably stronger and more coherent interference patterns than pairs with composite-integer ratios. Three metrics were reported as significant:

| Metric | Claimed Effect | Reported Significance |
|--------|---------------|----------------------|
| Amplitude (Vpp) | +28% for prime ratios | Significant |
| Sharpness (spectral power ratio) | +18% for prime ratios | Significant |
| Coherence (cross-correlation) | +22% for prime ratios | Significant |

## What We Found (Plan C Replication)

### Methodology Improvements

Plan C was designed as a **pre-registered falsification test** of the V3 claims, with the following improvements over V3:

1. **Pure sine waves** — Two AD9833 DDS modules (THD < −60 dBc) replaced GreenPAK square-wave dividers, eliminating the odd-harmonic comb that is the most likely confound in V3.
2. **Shared master clock** — Both DDS modules driven from a single 25 MHz TCXO, ensuring exact frequency ratios (not crystal-tolerance approximations).
3. **Pre-registered analysis plan** — Primary hypothesis, test pairs, sample size, exclusion rules, and decision tree specified before data collection.
4. **Blinded pair ordering** — 30 test pairs (8 prime:prime, 9 composite:composite, 6 prime:composite, 3 non-coprime controls, 4 irrational controls) presented in randomised order across 5 complete blocks.
5. **Automated data collection** — Python-controlled Arduino + Rigol DS1054Z SCPI capture, removing operator bias.

### Results (1200 trials, 8 metrics)

| Metric | PP Mean | CC Mean | p-value | Cohen's d | Significant? |
|--------|---------|---------|---------|-----------|-------------|
| RSP (dB) | −28.82 | −28.97 | 0.70 | 0.03 | No |
| Crest factor | 1.544 | 1.551 | 0.56 | −0.05 | No |
| **Spectral flatness** | **0.0045** | **0.0036** | **0.0003** | **0.28** | **Yes*** |
| Envelope regularity | 0.291 | 0.293 | 0.71 | −0.03 | No |
| Cross-correlation peak | 0.874 | 0.872 | 0.43 | 0.06 | No |
| Phase coherence | 0.802 | 0.798 | 0.34 | 0.07 | No |
| Vpp | 0.445 | 0.454 | 0.40 | −0.07 | No |
| Vrms | 0.360 | 0.360 | 0.98 | −0.002 | No |

*Bonferroni-corrected α = 0.00625 for 8 metrics. Spectral flatness survives correction.*

**Seven of eight metrics returned null results.** The three specific metrics claimed in V3 (Vpp, spectral power ratio, cross-correlation) all showed no significant difference between prime and composite ratio pairs.

### The Spectral Flatness Signal

One metric — spectral flatness — showed a small but statistically significant difference (p = 0.0003, d = 0.28): prime-ratio pairs produced marginally more spread-out frequency spectra than composite-ratio pairs. However, this result must be interpreted with caution due to hardware limitations (see below) and the small effect size. It was not a pre-registered primary metric.

### Hardware Limitations

The Plan C apparatus had significant limitations that constrain interpretation of all results, including the spectral flatness signal:

1. **Channel crosstalk:** The resistive summing network provided near-zero isolation between channels (−7 to +8.5 dB coupling). CH1 and CH2 probe points were not independent measurements.
2. **Amplitude mismatch:** DDS A produced stable output (0.62–0.66 V), while DDS B was erratic (0.14–0.68 V), with mismatches of 23–107%.
3. **No buffer amplifiers:** Both DDS outputs fed directly into the summing network with no impedance buffering.

These limitations mean the spectral flatness result could reflect frequency-dependent DDS output characteristics rather than any property of the ratio itself.

### Sanity Checks Passed

- Non-coprime control pairs (e.g., 9:6) matched their reduced forms (3:2) as expected (p > 0.17 on all metrics).
- Irrational ratios (√2, φ, e/2, π/2) showed no significant difference from either prime or composite strata.
- Block-order effects were not detected.

## Diagnosis: The V3 Harmonic Confound

The most parsimonious explanation for the V3 results is the **odd-harmonic content of square waves**.

GreenPAK dividers produce square waves, which contain energy at all odd harmonics (3f, 5f, 7f, ...) with amplitudes falling as 1/n. When two square waves are summed:

- A **prime:prime ratio** (e.g., 3:2) produces harmonic series that share no common frequencies below their product (6f₀). The resulting spectrum has many distinct peaks — high apparent "sharpness" and "coherence" in metrics that reward spectral distinctiveness.
- A **composite:composite ratio** (e.g., 9:8 = 3²:2³) produces harmonic series that share common frequencies at lower harmonics. The resulting spectrum has overlapping peaks that partially cancel or reinforce depending on phase — lower apparent sharpness.

This is a mathematical property of harmonic combs and coprimality, not a physical property of the medium or the ratio's "primeness." When the harmonics are removed (Plan C: pure sine waves), the effect disappears.

## Implications for Prime Resonance Theory

The theoretical framework in *Prime Resonance Theory: From Factorisation to Frequency* (DOI 10.5281/zenodo.20541350) made predictions contingent on experimental validation. With the V3 results now unreliable and Plan C returning null on 7/8 metrics:

1. **The claim that prime-ratio frequencies produce superior interference in linear analog circuits is not supported.** LTI (linear time-invariant) theory correctly predicts that a resistive summer's transfer function H(f) depends on frequency, not on the arithmetic properties of frequency ratios.
2. **The theoretical framework is not falsified in domains where it was not tested.** Plan C tested linear superposition of pure sine waves in a passive circuit — a domain where integer structure has no mechanism to matter. Domains with boundary conditions that enforce integer quantisation (acoustic cavities, vibrating strings, crystal lattices, electromagnetic resonant cavities) remain untested and may warrant future investigation.
3. **The spectral flatness anomaly** (d = 0.28) is noted for completeness but requires independent replication on hardware with proper channel isolation before any interpretation is warranted.

## Corrections to the Record

1. The headline V3 claims (+28% amplitude, +18% sharpness, +22% coherence for prime ratios) **should not be cited as evidence** for prime-ratio superiority in analog interference.
2. The V3 result is reclassified as a **harmonic-comb artefact** of square-wave signal generation, not a property of the frequency ratios themselves.
3. The GitHub repository description for `pwt-v3-data` will be updated to reference this corrigendum.
4. Future versions of *Prime Resonance Theory* will note the null replication result.

## Data Availability

All Plan C data, code, and analysis are available at:
- **Pre-registration:** `pre-registration.md` (timestamped before data collection)
- **Raw data:** `scripts/results/runs/` (1200-trial waveform captures + measurement CSVs)
- **Analysis reports:** `scripts/results/analysis/`
- **Firmware:** `firmware/arbiter/`
- **Circuit design:** `circuit-design.md`

## Acknowledgements

Plan C was designed with input from Grok (xAI) for experimental methodology review, and executed with Nagaπ (OpenClaw) for automation and analysis. The pre-registration document incorporated adversarial review to minimise confirmation bias.

---

*"The Truth shall set us Free." — A null result honestly reported advances science more than a false positive defended.*

**Adrian Sutton (Tusk Innovations)**
19 September 2026
