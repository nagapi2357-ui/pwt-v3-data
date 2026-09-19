"""
rsp.py — Residual Spectral Power computation module for the Arbiter experiment.

Frozen RSP definition (do not modify after first run):
  After amplitude-normalising the two-tone record to unit RMS per channel,
  notch f₁, f₂, |f₁−f₂|, and f₁+f₂ at fixed RBW = ±5 bins (±2.5 Hz at
  0.5 Hz resolution). RSP = 10·log₁₀(remaining integrated power in [0, fs/2]
  / total power before notching), in dB.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import hilbert


def compute_rsp(
    waveform: np.ndarray,
    sample_rate: float,
    f1: float,
    f2: float,
    rbw_bins: int = 5,
) -> float:
    """Compute Residual Spectral Power in dB.

    Parameters
    ----------
    waveform : 1-D real array — the summed (CH3) waveform.
    sample_rate : sampling rate in Hz.
    f1, f2 : the two carrier frequencies in Hz.
    rbw_bins : half-width of notch in FFT bins (±rbw_bins around each tone).

    Returns
    -------
    RSP in dB (more negative = less residual energy).
    """
    N = len(waveform)
    # Normalise to unit RMS
    rms = np.sqrt(np.mean(waveform.astype(np.float64) ** 2))
    if rms == 0:
        return 0.0
    sig = waveform / rms

    # FFT (one-sided power spectrum)
    spectrum = np.fft.rfft(sig)
    power = np.abs(spectrum) ** 2
    total_power = np.sum(power)
    if total_power == 0:
        return 0.0

    freq_res = sample_rate / N  # Hz per bin

    # Frequencies to notch
    notch_freqs = [f1, f2, abs(f1 - f2), f1 + f2]
    notched = power.copy()

    for f in notch_freqs:
        if f <= 0 or f >= sample_rate / 2:
            continue
        centre_bin = int(round(f / freq_res))
        lo = max(0, centre_bin - rbw_bins)
        hi = min(len(notched) - 1, centre_bin + rbw_bins)
        notched[lo : hi + 1] = 0.0

    remaining = np.sum(notched)
    if remaining <= 0:
        return -np.inf
    return 10.0 * np.log10(remaining / total_power)


def compute_metrics(
    waveform: np.ndarray,
    sample_rate: float,
    f1: float,
    f2: float,
) -> dict:
    """Compute RSP and all secondary metrics.

    Returns dict with keys:
        rsp_db, crest_factor, spectral_flatness, envelope_regularity,
        xcorr_peak (placeholder — needs two-channel data), phase_coherence,
        total_power, remaining_power, notch_freqs
    """
    sig = waveform.astype(np.float64)
    N = len(sig)

    # RSP
    rsp_db = compute_rsp(sig, sample_rate, f1, f2)

    # Crest factor
    rms = np.sqrt(np.mean(sig ** 2))
    crest = float(np.max(np.abs(sig)) / rms) if rms > 0 else 0.0

    # Spectral flatness (Wiener entropy)
    spectrum = np.abs(np.fft.rfft(sig)) ** 2
    spectrum_pos = spectrum[1:]  # skip DC
    if len(spectrum_pos) > 0 and np.all(spectrum_pos >= 0):
        # Replace zeros with tiny value for log
        sp = np.where(spectrum_pos > 0, spectrum_pos, 1e-30)
        log_mean = np.mean(np.log(sp))
        arith_mean = np.mean(sp)
        flatness = float(np.exp(log_mean) / arith_mean) if arith_mean > 0 else 0.0
    else:
        flatness = 0.0

    # Envelope regularity (CV of beat envelope peaks)
    analytic = hilbert(sig)
    envelope = np.abs(analytic)
    # Find local maxima in envelope
    env_smooth = envelope  # could smooth, but keep simple
    peaks = []
    for i in range(1, len(env_smooth) - 1):
        if env_smooth[i] > env_smooth[i - 1] and env_smooth[i] > env_smooth[i + 1]:
            peaks.append(env_smooth[i])
    if len(peaks) >= 2:
        peaks_arr = np.array(peaks)
        env_reg = float(np.std(peaks_arr) / np.mean(peaks_arr))  # CV
    else:
        env_reg = 0.0

    # Phase coherence — circular variance of instantaneous phase difference
    # (requires two channels; for single-channel, compute self-consistency)
    # Placeholder: use envelope regularity as proxy
    phase_coh = 1.0 - env_reg  # higher = more coherent

    return {
        "rsp_db": rsp_db,
        "crest_factor": crest,
        "spectral_flatness": flatness,
        "envelope_regularity": env_reg,
        "xcorr_peak": 0.0,  # needs two-channel input
        "phase_coherence": phase_coh,
    }


def compute_rsp_two_channel(
    ch1: np.ndarray,
    ch2: np.ndarray,
    ch3_sum: np.ndarray,
    sample_rate: float,
    f1: float,
    f2: float,
    rbw_bins: int = 5,
) -> dict:
    """Full two-channel RSP + metrics including cross-correlation.

    ch1: DDS A waveform, ch2: DDS B waveform, ch3_sum: summed output.
    """
    metrics = compute_metrics(ch3_sum, sample_rate, f1, f2)

    # Cross-correlation peak between ch1 and ch2
    c1 = ch1.astype(np.float64)
    c2 = ch2.astype(np.float64)
    n1 = np.sqrt(np.sum(c1 ** 2))
    n2 = np.sqrt(np.sum(c2 ** 2))
    if n1 > 0 and n2 > 0:
        xcorr = np.correlate(c1 / n1, c2 / n2, mode="full")
        metrics["xcorr_peak"] = float(np.max(np.abs(xcorr)))

    # Phase coherence from two channels
    a1 = hilbert(c1)
    a2 = hilbert(c2)
    phase_diff = np.angle(a1) - np.angle(a2)
    # Circular variance: 1 - |mean(e^{i*theta})|
    circ_var = 1.0 - float(np.abs(np.mean(np.exp(1j * phase_diff))))
    metrics["phase_coherence"] = 1.0 - circ_var

    return metrics
