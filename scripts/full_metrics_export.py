#!/usr/bin/env python3
"""Export flatness, xcorr, peaks for ALL V3 NPZ files — for Kimi K3 analysis."""

import numpy as np
from scipy.signal import welch, find_peaks, correlate
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "Adrian Docs/Pics/Test Point Readings/22 May Results - Board 3"

def analyze(npz_path):
    d = np.load(npz_path)
    t1, v1, t2, v2 = d['t1'], d['v1'], d['t2'], d['v2']
    sr = d['sample_rate'] if 'sample_rate' in d else 1.0 / np.median(np.diff(t1))
    
    results = {}
    for prefix, v in [('ch1', v1), ('ch2', v2)]:
        nperseg = max(256, len(v) // 4)
        f, psd = welch(v, fs=sr, nperseg=nperseg, window='hann', scaling='spectrum')
        a = np.sqrt(psd)
        
        # Limit to 1200 Hz
        mask = f <= 1200
        f_m, a_m = f[mask], a[mask]
        
        results[f'{prefix}_vpp'] = (v.max() - v.min()) * 1000
        results[f'{prefix}_peak_mv'] = a_m.max() * 1000
        
        # Flatness (Wiener entropy)
        a_pos = a_m[a_m > 0]
        results[f'{prefix}_flatness'] = np.exp(np.mean(np.log(a_pos))) / np.mean(a_pos)
        
        # Peaks
        peaks, _ = find_peaks(a_m, height=a_m.max() * 0.05, distance=2)
        results[f'{prefix}_npeaks'] = len(peaks)
        
        # Entropy
        psd_n = a_m**2
        psd_n = psd_n / (psd_n.sum() + 1e-15)
        psd_pos = psd_n[psd_n > 0]
        results[f'{prefix}_entropy'] = -np.sum(psd_pos * np.log2(psd_pos)) / np.log2(len(psd_pos))
        
        # Extended flatness (0-4096 Hz) for Kimi's test
        mask4k = f <= 4096
        a_4k = np.sqrt(psd[mask4k])
        a_4k_pos = a_4k[a_4k > 0]
        results[f'{prefix}_flatness_4k'] = np.exp(np.mean(np.log(a_4k_pos))) / np.mean(a_4k_pos)
    
    # Cross-correlation (peak in ±20ms AND true zero-lag)
    ml = min(len(v1), len(v2))
    v1_ac = v1[:ml] - v1[:ml].mean()
    v2_ac = v2[:ml] - v2[:ml].mean()
    xcorr = correlate(v1_ac, v2_ac, mode='full')
    xcorr = xcorr / (np.sqrt(np.sum(v1_ac**2) * np.sum(v2_ac**2)) + 1e-15)
    center = ml - 1
    win = min(ml // 2, int(0.02 * sr))
    results['xcorr_peak'] = xcorr[center - win:center + win].max()
    results['xcorr_zero'] = xcorr[center]  # TRUE zero-lag
    
    return results

print(f"{'File':<45} {'CH1_Flat':>8} {'CH1_F4k':>8} {'CH1_Pk':>7} {'CH1_Ent':>8} {'CH2_Flat':>8} {'Xcorr_pk':>9} {'Xcorr_0':>8}")
print("-" * 110)

for npz in sorted(DATA_DIR.glob("*.npz")):
    try:
        r = analyze(npz)
        print(f"{npz.stem:<45} {r['ch1_flatness']:8.4f} {r['ch1_flatness_4k']:8.4f} {r['ch1_npeaks']:7d} {r['ch1_entropy']:8.4f} {r['ch2_flatness']:8.4f} {r['xcorr_peak']:9.4f} {r['xcorr_zero']:8.4f}")
    except Exception as e:
        print(f"{npz.stem:<45} ERROR: {e}")
