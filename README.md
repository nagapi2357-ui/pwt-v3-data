# Prime Wave Theory — V3 Experimental Data

Raw waveform data and analysis scripts from the Prime Maxel v3 experiment (Board 3, 22 May 2026).

## What's Here

### `data/22-may-board3/`
- **NPZ files** — NumPy archives containing `t1, v1, t2, v2` (time/voltage pairs for TORSION_A and TORSION_B channels) plus `sample_rate` metadata
- **CSV files** — Same data in CSV format for tools that don't read NPZ

### `scripts/`
- **`rigol_capture.py`** — Oscilloscope capture script (Rigol DS1054Z via SCPI/LAN)
- **`torsion_analyze.py`** — Single-capture analysis: Welch PSD, peak detection, cross-correlation, spectrogram, ratio analysis
- **`experiment_suite_analysis.py`** — Batch analysis of all experiments: head-to-head comparison, progressive addition, radar plots
- **`full_metrics_export.py`** — Complete metrics table for all captures (flatness at 1.2 kHz and 4 kHz, zero-lag and peak xcorr)

## Experiment Structure

The V3 board drives a torsion ring (transmission line) with sets of square-wave frequencies at prime and composite ratios of a 1024 Hz base frequency.

**Key experiments:**
| Name | Frequency Set (f₀/n) | Type |
|------|----------------------|------|
| Prime baseline | {1,2,3,5,7,11,13} | All prime divisors |
| Composite narrow | {2,4,6,8,9,10} | Dense composites |
| Composite wide | {2,4,6,8,10,12} | Spread composites |
| Harmonic | {1,2,3,4,5,6} | Sequential integers |
| Tusk resonant | {1,2,3,5,6,7} | Optimal set from theory |
| Single | 1024 Hz only | Control |
| Progressive 1–6 | Cumulative prime addition | f₀/1, +/3, +/5, +/7, +/11, +/13 |
| Prog composite 1–6 | Cumulative composite addition | f₀/2, +/4, +/6, +/8, +/9, +/10 |
| Coprime dim A–G | 3-tone coprime sets | Various coprime combinations |
| Tusk sopfr | sopfr-weighted set | |
| Twin primes | Twin prime ratios | |
| Six frame | 6-tone frame | |

## Key Metrics

- **Vpp** — Peak-to-peak voltage (mV)
- **Flatness** — Wiener entropy (geometric/arithmetic mean of amplitude spectrum, 0–1200 Hz)
- **Peaks** — Spectral peak count (5% threshold, 2-bin minimum separation)
- **Entropy** — Normalized spectral entropy
- **Xcorr** — Peak cross-correlation within ±20 ms of zero lag (≈ zero-lag for this hardware)

## Results Summary

Prime-ratio frequency sets produce +28% amplitude, +18% spectral sharpness, and +22% coherence vs composite sets. See [V3 paper](https://doi.org/10.5281/zenodo.20541350) and [Prime Resonance Theory](https://doi.org/10.5281/zenodo.20541350).

## Related Publications

1. [Tusk Series](https://doi.org/10.5281/zenodo.19852116) (Apr 2026)
2. [RAS Paper](https://doi.org/10.5281/zenodo.20512346) (Jun 2026)
3. [Prime Resonance Theory](https://doi.org/10.5281/zenodo.20541350) (Jun 2026)
4. [Prime Tree Architecture](https://doi.org/10.5281/zenodo.20609886) (Jun 2026)

## License

CC BY-SA 4.0 — Tusk Innovations

## Contact

- Website: [pwt.life](https://pwt.life)
- Discord: [Nagaπ server](https://discord.gg/nagapi)
