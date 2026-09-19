# Corrigendum: V3 Experimental Results

**Applies to:** Sutton, A. (2026). *Prime Wave Theory — V3 Experimental Results.* Zenodo. DOI: [10.5281/zenodo.20637347](https://doi.org/10.5281/zenodo.20637347)

**See also:** Sutton, A. (2026). *Prime Resonance Theory: A Unified Framework for Frequency Set Optimisation via Number-Theoretic Structure.* Zenodo. DOI: [10.5281/zenodo.20541350](https://doi.org/10.5281/zenodo.20541350)

**Date:** 19 September 2026 (revised per review)

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

### Pooled Results (1200 trials, 8 metrics)

| Metric | PP Mean | CC Mean | p-value | Cohen's d | Significant? |
|--------|---------|---------|---------|-----------|-------------|
| RSP (dB) | −28.82 | −28.97 | 0.70 | 0.03 | No |
| Crest factor | 1.544 | 1.551 | 0.56 | −0.05 | No |
| Spectral flatness | 0.0045 | 0.0036 | 0.0003 | 0.28 | See below |
| Envelope regularity | 0.291 | 0.293 | 0.71 | −0.03 | No |
| Cross-correlation peak | 0.874 | 0.872 | 0.43 | 0.06 | No |
| Phase coherence | 0.802 | 0.798 | 0.34 | 0.07 | No |
| Vpp | 0.445 | 0.454 | 0.40 | −0.07 | No |
| Vrms | 0.360 | 0.360 | 0.98 | −0.002 | No |

*Bonferroni-corrected α = 0.00625 for 8 metrics.*

**Seven of eight metrics returned null results.** The three specific metrics claimed in V3 (amplitude, spectral sharpness, cross-correlation) showed no significant difference between prime-ratio and composite-ratio pairs.

### Pre-Registered Primary Test: Class B Matched Pairs

The pre-registration specified Class B (matched ratio-magnitude cells) as the primary hypothesis test. All three Class B cells returned null on both RSP and Vpp:

| Cell | PP Pair | CC Pair | RSP p-value | RSP d | Vpp p-value | Vpp d |
|------|---------|---------|-------------|-------|-------------|-------|
| B1 | PP3 (7:5) | CC7 (36:25) | 0.009 | −0.60 | 0.78 | −0.07 |
| B2 | PP4 (11:7) | CC2 (25:16) | 0.30 | −0.24 | 0.62 | −0.11 |
| B3 | PP2 (5:3) | CC9 (27:16) | 0.19 | 0.30 | 0.62 | −0.11 |

B1 shows a nominally significant RSP difference (p = 0.009), but in the *wrong direction* (CC > PP), does not survive Bonferroni correction across the three cells, and is not supported by any other metric or cell. **The pre-registered primary test is null.**

### Spectral Flatness: An Exploratory Leftover, Not a Signal

The pooled spectral flatness metric showed a nominally significant difference (p = 0.0003, d = 0.28). This result **should not be carried forward** as a finding for the following reasons:

1. **Not a pre-registered primary metric.** The pre-registration specified RSP on Class B cells as the primary test. Spectral flatness was one of eight exploratory metrics.
2. **Failed abort conditions.** The pre-registration specified amplitude matching within 3 dB and isolation requirements. The apparatus failed both: DDS B amplitude was erratic (0.14–0.68 V) and channel isolation was −7 to +8.5 dB. Under the pre-registration's own rules, the experiment is inconclusive on fine-grained metrics.
3. **d = 0.28 on a messy summer** is exactly the kind of small effect that arises from frequency-dependent DDS output characteristics, not ratio physics.
4. **Not supported by Class B.** Class B cells do not show a consistent spectral flatness pattern.

This result is reported for transparency but should not be cited, named as "the spectral flatness signal," or carried into future work.

### Sanity Checks Passed

- Non-coprime control pairs (e.g., 9:6) matched their reduced forms (3:2) as expected (p > 0.17 on all metrics).
- Irrational ratios (√2, φ, e/2, π/2) showed no significant difference from either prime or composite strata — consistent with LTI superposition.
- Block-order effects were not detected.

## Diagnosis: The V3 Harmonic Confound

The most parsimonious explanation for the V3 results is the **odd-harmonic content of square waves**.

GreenPAK dividers produce square waves, which contain energy at all odd harmonics (3f, 5f, 7f, ...) with amplitudes falling as 1/n. When two square waves are summed:

- A **prime:prime ratio** (e.g., 3:2) produces harmonic series that share no common frequencies below their product (6f₀). The resulting spectrum has many distinct peaks — high apparent "sharpness" and "coherence" in metrics that reward spectral distinctiveness.
- A **composite:composite ratio** (e.g., 9:8 = 3²:2³) produces harmonic series that share common frequencies at lower harmonics. The resulting spectrum has overlapping peaks that partially cancel or reinforce depending on phase — lower apparent sharpness.

This is a mathematical property of harmonic combs and coprimality, not a physical property of the medium or the ratio's "primeness." When the harmonics are removed (Plan C: pure sine waves), the effect disappears.

## Implications

1. **The claim that prime-ratio frequencies produce superior interference in linear analog circuits is not supported.** LTI theory correctly predicts that a resistive summer's transfer function H(f) depends on frequency, not on the arithmetic properties of frequency ratios.
2. **The live content of Prime Resonance Theory is:** integer spectra have prime generators. That is number theory plus boundary-value physics. It did not need V3, and it does not need V3's percentages. The mathematical results (R(S), Spectral Honeycomb Theorem, Prime Harmonic Transform) stand as mathematics. The experimental validation table (§3.3 of the PRT paper, Spearman ρ = 0.736) used V3 data and is now unreliable.
3. **Linear analog interference is closed as a test domain for primality.** Any future experimental work should start as a new pre-registered question in a system that has an integer mode list (acoustic cavities, crystal resonators, vibrating strings), not be seeded with V3 percentages or the spectral flatness p-value.

## Corrections to the Record

1. The headline V3 claims (+28% amplitude, +18% sharpness, +22% coherence for prime ratios) **should not be cited as evidence** for prime-ratio superiority in analog interference.
2. The V3 result is reclassified as a **harmonic-comb artefact** of square-wave signal generation, not a property of the frequency ratios themselves.
3. The GitHub repository descriptions for `Prime_Maxel-v3` and `pwt-v3-data` have been updated to reference this corrigendum.
4. The Prime Resonance Theory paper (DOI 10.5281/zenodo.20541350) has been updated with an addendum (§12) noting the null replication.

## Data Availability

All Plan C data, code, and analysis are deposited in this repository:

- **Pre-registration:** [`plan-c/pre-registration.md`](plan-c/pre-registration.md) (timestamped before data collection)
- **Circuit design:** [`plan-c/circuit-design.md`](plan-c/circuit-design.md)
- **Firmware:** [`plan-c/firmware/`](plan-c/firmware/)
- **Capture scripts:** [`plan-c/scripts/`](plan-c/scripts/) (arbiter_fast.py, arbiter_full.py, rsp.py)
- **Raw data — measurement run:** [`plan-c/results/runs/merged_5block/results.csv`](plan-c/results/runs/merged_5block/results.csv)
- **Raw data — waveform run (1200 trials):** [`plan-c/results/runs/20260918_175038/`](plan-c/results/runs/20260918_175038/) (per-trial .npz waveforms + results.csv)
- **Analysis reports:** [`plan-c/results/analysis/`](plan-c/results/analysis/)
- **Test matrix:** [`plan-c/test-matrix.md`](plan-c/test-matrix.md)

---

*"The Truth shall set us Free." — A null result honestly reported advances science more than a false positive defended.*

**Adrian Sutton (Tusk Innovations)**
19 September 2026
