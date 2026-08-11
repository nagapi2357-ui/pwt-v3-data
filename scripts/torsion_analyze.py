#!/usr/bin/env python3
"""
Torsion FFT Analysis — Analyzes captured torsion waveform data.
Produces: time-domain plots, FFT spectrum, peak detection, ratio analysis,
cross-correlation (phase), and spectrogram.

Usage:
    python3 torsion_analyze.py <npz_file> [--ac] [--fmax 5000]
    
    --ac    : Remove DC offset before analysis (use if DC-coupled capture)
    --fmax  : Max frequency for FFT plots (default: 5000 Hz)
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import welch, find_peaks, correlate
from scipy.fft import fft, fftfreq
import os, sys

# Expected prime frequencies from the Arduino signal gen
PRIME_FREQS = {
    'f₀/1': 1024,
    'f₀/3': 341,
    'f₀/5': 205,
    'f₀/7': 146,
    'f₀/11': 93,
    'f₀/13': 79,
}

PRIME_RATIOS = {
    '3/1': 3.0, '5/1': 5.0, '7/1': 7.0, '11/1': 11.0, '13/1': 13.0,
    '5/3': 5/3, '7/3': 7/3, '11/3': 11/3, '13/3': 13/3,
    '7/5': 7/5, '11/5': 11/5, '13/5': 13/5,
    '11/7': 11/7, '13/7': 13/7,
    '13/11': 13/11,
}


def analyze(npz_path, remove_dc=False, fmax=5000):
    data = np.load(npz_path, allow_pickle=True)
    t1, v1 = data['t1'], data['v1']
    t2, v2 = data['t2'], data['v2']
    
    # Try to get sample rate from metadata
    sr = None
    for key in ['sample_rate', 'ch1_sample_rate']:
        if key in data:
            sr = float(data[key])
            break
    if sr is None and len(t1) > 1:
        sr = 1.0 / (t1[1] - t1[0])
    
    duration_ms = (t1[-1] - t1[0]) * 1000
    print(f"=== Torsion Analysis ===")
    print(f"File: {os.path.basename(npz_path)}")
    print(f"Samples: CH1={len(v1)}, CH2={len(v2)}")
    print(f"Sample rate: {sr:,.0f} Sa/s")
    print(f"Duration: {duration_ms:.2f} ms")
    print(f"Frequency resolution: {sr/max(len(v1),1):.2f} Hz")
    
    if remove_dc:
        v1 = v1 - v1.mean()
        v2 = v2 - v2.mean()
        print("DC offset removed.")
    
    ch1_vpp = v1.max() - v1.min()
    ch2_vpp = v2.max() - v2.min()
    print(f"\nCH1 (TORSION_A): Vpp={ch1_vpp*1000:.1f}mV, mean={v1.mean()*1000:.1f}mV")
    print(f"CH2 (TORSION_B): Vpp={ch2_vpp*1000:.1f}mV, mean={v2.mean()*1000:.1f}mV")
    if ch2_vpp > 0 and ch1_vpp > 0:
        print(f"Amplitude ratio A/B: {ch1_vpp/ch2_vpp:.3f}")
    
    # ===== FFT =====
    fig, axes = plt.subplots(5, 1, figsize=(16, 22))
    
    # --- Panel 1: Time domain ---
    ax = axes[0]
    t1_ms = (t1 - t1[0]) * 1000
    t2_ms = (t2 - t2[0]) * 1000
    if len(v1) > 5000:
        step = len(v1) // 5000
        ax.plot(t1_ms[::step], v1[::step]*1000, 'gold', alpha=0.8, linewidth=0.5, label='TORSION_A')
    else:
        ax.plot(t1_ms, v1*1000, 'gold', alpha=0.8, label='TORSION_A')
    if len(v2) > 5000:
        step2 = len(v2) // 5000
        ax.plot(t2_ms[::step2], v2[::step2]*1000, 'cyan', alpha=0.8, linewidth=0.5, label='TORSION_B')
    else:
        ax.plot(t2_ms, v2*1000, 'cyan', alpha=0.8, label='TORSION_B')
    ax.set_xlabel('Time (ms)'); ax.set_ylabel('Voltage (mV)')
    ax.set_title(f'Time Domain — {duration_ms:.1f}ms window')
    ax.legend(); ax.grid(True, alpha=0.3)
    
    # --- Panel 2 & 3: FFT for each channel ---
    for idx, (v, ch_name, color) in enumerate([(v1, 'TORSION_A (CH1)', 'gold'), 
                                                  (v2, 'TORSION_B (CH2)', 'cyan')]):
        ax = axes[1 + idx]
        v_ac = v - v.mean()
        
        if len(v_ac) < 32:
            ax.text(0.5, 0.5, f'{ch_name}: Insufficient data', transform=ax.transAxes, ha='center')
            continue
        
        # Welch PSD for smooth spectrum
        nperseg = min(len(v_ac), max(256, 2**int(np.log2(len(v_ac)/4))))
        freqs_w, psd = welch(v_ac, fs=sr, nperseg=nperseg, window='hann', scaling='spectrum')
        amp = np.sqrt(psd) * 1000  # mV rms
        
        mask = freqs_w <= fmax
        ax.semilogy(freqs_w[mask], amp[mask], color=color, alpha=0.8, linewidth=0.8)
        
        # Mark expected prime frequencies
        for name, f in PRIME_FREQS.items():
            if f <= fmax:
                ax.axvline(f, color='red', alpha=0.3, linestyle='--', linewidth=0.8)
                ax.text(f, amp[mask].max()*0.7, name, rotation=90, fontsize=7, 
                       color='red', ha='right')
        
        # Find and mark peaks
        peaks, props = find_peaks(amp[mask], height=amp[mask].max()*0.05, 
                                   distance=max(3, int(50/(freqs_w[1]-freqs_w[0]))))
        if len(peaks) > 0:
            pf = freqs_w[mask][peaks]
            pa = amp[mask][peaks]
            top = np.argsort(pa)[-10:][::-1]
            for i in top:
                ax.plot(pf[i], pa[i], 'rv', markersize=6)
                ax.annotate(f'{pf[i]:.0f}Hz', (pf[i], pa[i]), fontsize=7,
                          textcoords='offset points', xytext=(5, 5))
            
            print(f"\n{ch_name} — Top FFT peaks:")
            for i in top:
                # Check proximity to expected primes
                closest = min(PRIME_FREQS.items(), key=lambda x: abs(x[1]-pf[i]))
                delta = abs(pf[i] - closest[1])
                match = f" ← {closest[0]} ({closest[1]}Hz, Δ={delta:.0f}Hz)" if delta < 50 else ""
                print(f"  {pf[i]:8.1f} Hz — {pa[i]:.4f} mV rms{match}")
        
        ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('Amplitude (mV rms)')
        ax.set_title(f'FFT — {ch_name}')
        ax.set_xlim(0, fmax); ax.grid(True, alpha=0.3)
    
    # --- Panel 4: Cross-correlation (phase) ---
    ax = axes[3]
    ml = min(len(v1), len(v2))
    if ml > 10:
        v1_ac = v1[:ml] - v1[:ml].mean()
        v2_ac = v2[:ml] - v2[:ml].mean()
        # Normalised cross-correlation
        xcorr = correlate(v1_ac, v2_ac, mode='full')
        xcorr = xcorr / (np.sqrt(np.sum(v1_ac**2) * np.sum(v2_ac**2)) + 1e-15)
        lags = np.arange(-ml+1, ml) / sr * 1000  # ms
        
        # Show central portion
        center = ml - 1
        window = min(ml//2, int(0.02 * sr))  # ±20ms or half the signal
        ax.plot(lags[center-window:center+window], 
               xcorr[center-window:center+window], 'lime', alpha=0.8)
        
        peak_lag_idx = center - window + np.argmax(xcorr[center-window:center+window])
        peak_lag_ms = lags[peak_lag_idx]
        peak_corr = xcorr[peak_lag_idx]
        ax.axvline(peak_lag_ms, color='red', alpha=0.5, linestyle='--')
        ax.set_title(f'Cross-Correlation A↔B — Peak: {peak_corr:.3f} at lag={peak_lag_ms:.3f}ms')
        print(f"\nCross-correlation peak: {peak_corr:.4f} at lag = {peak_lag_ms:.4f} ms")
        if sr > 0:
            phase_at_1khz = (peak_lag_ms/1000) * 1024 * 360
            print(f"Phase offset at 1024Hz: {phase_at_1khz:.1f}°")
    else:
        ax.text(0.5, 0.5, 'Insufficient data for cross-correlation', 
               transform=ax.transAxes, ha='center')
    ax.set_xlabel('Lag (ms)'); ax.set_ylabel('Correlation')
    ax.grid(True, alpha=0.3)
    
    # --- Panel 5: Ratio analysis heatmap ---
    ax = axes[4]
    # Find peaks from CH1 for ratio analysis
    v1_ac = v1 - v1.mean()
    if len(v1_ac) > 64:
        nperseg1 = min(len(v1_ac), max(256, 2**int(np.log2(len(v1_ac)/4))))
        f1, p1 = welch(v1_ac, fs=sr, nperseg=nperseg1, window='hann', scaling='spectrum')
        a1 = np.sqrt(p1) * 1000
        mask1 = f1 <= fmax
        peaks1, _ = find_peaks(a1[mask1], height=a1[mask1].max()*0.05, 
                                distance=max(3, int(50/(f1[1]-f1[0]))))
        if len(peaks1) >= 2:
            pf1 = f1[mask1][peaks1]
            pa1 = a1[mask1][peaks1]
            top1 = np.argsort(pa1)[-8:][::-1]
            top_freqs = sorted(pf1[top1])
            
            print(f"\n=== Frequency Ratio Analysis (CH1 top peaks) ===")
            ratios = []
            for i in range(len(top_freqs)):
                for j in range(i+1, len(top_freqs)):
                    r = top_freqs[j] / top_freqs[i]
                    # Check if close to a prime ratio
                    closest_r = min(PRIME_RATIOS.items(), key=lambda x: abs(x[1]-r))
                    match = f" ≈ {closest_r[0]} ({closest_r[1]:.3f})" if abs(closest_r[1]-r)/closest_r[1] < 0.1 else ""
                    ratios.append((top_freqs[i], top_freqs[j], r, match))
                    print(f"  {top_freqs[j]:.0f}/{top_freqs[i]:.0f} = {r:.3f}{match}")
            
            # Plot ratio scatter
            if ratios:
                r_vals = [r[2] for r in ratios]
                ax.hist(r_vals, bins=30, color='gold', alpha=0.7, edgecolor='black')
                for name, val in PRIME_RATIOS.items():
                    if val <= max(r_vals)*1.1:
                        ax.axvline(val, color='red', alpha=0.4, linestyle='--', linewidth=0.8)
                        ax.text(val, ax.get_ylim()[1]*0.9 if ax.get_ylim()[1]>0 else 1, 
                               name, rotation=90, fontsize=7, color='red')
                ax.set_title('Frequency Ratio Distribution vs Prime Ratios')
            else:
                ax.text(0.5, 0.5, 'No ratio data', transform=ax.transAxes, ha='center')
        else:
            ax.text(0.5, 0.5, 'Not enough peaks for ratio analysis', 
                   transform=ax.transAxes, ha='center')
    ax.set_xlabel('Frequency Ratio'); ax.set_ylabel('Count')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    out_dir = os.path.dirname(npz_path)
    base = os.path.splitext(os.path.basename(npz_path))[0]
    out_path = os.path.join(out_dir, f'{base}_analysis.png')
    plt.savefig(out_path, dpi=150)
    print(f"\n📊 Analysis plot saved: {out_path}")
    return out_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 torsion_analyze.py <npz_file> [--ac] [--fmax 5000]")
        sys.exit(1)
    
    npz_file = sys.argv[1]
    remove_dc = '--ac' in sys.argv
    fmax = 5000
    if '--fmax' in sys.argv:
        idx = sys.argv.index('--fmax')
        fmax = float(sys.argv[idx + 1])
    
    analyze(npz_file, remove_dc=remove_dc, fmax=fmax)
