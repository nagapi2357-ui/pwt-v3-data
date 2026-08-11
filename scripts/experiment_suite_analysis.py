#!/usr/bin/env python3
"""
Full Experiment Suite Analysis — 22 May 2026, Board 3
Compares: Prime, Composite (narrow), Wide Composite, Harmonic, Single, Progressive 1-6
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, correlate
import os, glob

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'Adrian Docs', 'Pics', 'Test Point Readings', '22 May Results - Board 3')

# All experiment files
EXPERIMENTS = {
    'Prime (full)':        'torsion_U2_prime_baseline_*.npz',
    'Composite (narrow)':  'torsion_U2_composite_*.npz',
    'Composite (wide)':    'torsion_U2_wide_composite_*.npz',
    'Harmonic (1-6)':      'torsion_U2_harmonic_*.npz',
    'Single (all 1024)':   'torsion_U2_single_freq_*.npz',
}

PROGRESSIVE = {f'Prog {i} ({["f₀/1","+ f₀/3","+ f₀/5","+ f₀/7","+ f₀/11","+ f₀/13"][i-1]})': 
               f'torsion_U2_progressive_{i}_*.npz' for i in range(1, 7)}

PRIME_FREQS = {'f₀/1': 1024, 'f₀/3': 341, 'f₀/5': 205, 'f₀/7': 146, 'f₀/11': 93, 'f₀/13': 79}

def load_and_analyze(pattern):
    files = sorted(glob.glob(os.path.join(DATA, pattern)))
    if not files:
        return None
    d = np.load(files[-1])  # Use latest
    t1, v1, t2, v2 = d['t1'], d['v1'], d['t2'], d['v2']
    sr = 1.0 / (t1[1] - t1[0])
    N = len(v1)
    
    result = {
        'sr': sr, 'N': N,
        'ch1_vpp': (v1.max() - v1.min()) * 1000,
        'ch2_vpp': (v2.max() - v2.min()) * 1000,
    }
    
    # FFT for both channels
    for ch_idx, (v, prefix) in enumerate([(v1, 'ch1'), (v2, 'ch2')]):
        v_ac = v - v.mean()
        w = np.hanning(N)
        Y = np.abs(fft(v_ac * w))[:N//2] * 2.0 / (N * 0.5) * 1000  # mV
        freqs = fftfreq(N, 1.0/sr)[:N//2]
        
        mask = freqs <= 1200
        f_m, a_m = freqs[mask], Y[mask]
        
        result[f'{prefix}_freqs'] = f_m
        result[f'{prefix}_amps'] = a_m
        
        # Peak amplitude
        result[f'{prefix}_peak'] = a_m.max()
        
        # Spectral flatness (geometric mean / arithmetic mean)
        a_pos = a_m[a_m > 0]
        result[f'{prefix}_flatness'] = np.exp(np.mean(np.log(a_pos))) / np.mean(a_pos)
        
        # Significant peaks
        peaks, _ = find_peaks(a_m, height=a_m.max() * 0.05, distance=2)
        result[f'{prefix}_npeaks'] = len(peaks)
        
        # Spectral entropy (normalized)
        psd = a_m**2
        psd_norm = psd / (psd.sum() + 1e-15)
        psd_pos = psd_norm[psd_norm > 0]
        result[f'{prefix}_entropy'] = -np.sum(psd_pos * np.log2(psd_pos)) / np.log2(len(psd_pos))
    
    # Cross-correlation
    ml = min(len(v1), len(v2))
    v1_ac = v1[:ml] - v1[:ml].mean()
    v2_ac = v2[:ml] - v2[:ml].mean()
    xcorr = correlate(v1_ac, v2_ac, mode='full')
    xcorr = xcorr / (np.sqrt(np.sum(v1_ac**2) * np.sum(v2_ac**2)) + 1e-15)
    center = ml - 1
    win = min(ml//2, int(0.02*sr))
    result['xcorr'] = xcorr[center-win:center+win].max()
    
    return result

def main():
    print("=" * 80)
    print("EXPERIMENT SUITE ANALYSIS — Board 3, U2 — 22 May 2026")
    print("=" * 80)
    
    # Load all experiments
    all_results = {}
    for name, pattern in {**EXPERIMENTS, **PROGRESSIVE}.items():
        r = load_and_analyze(pattern)
        if r:
            all_results[name] = r
            print(f"\n{name}:")
            print(f"  CH1: Vpp={r['ch1_vpp']:.0f}mV, Peak={r['ch1_peak']:.1f}mV, "
                  f"Flatness={r['ch1_flatness']:.3f}, Peaks={r['ch1_npeaks']}, "
                  f"Entropy={r['ch1_entropy']:.3f}")
            print(f"  CH2: Vpp={r['ch2_vpp']:.0f}mV, Peak={r['ch2_peak']:.1f}mV, "
                  f"Flatness={r['ch2_flatness']:.3f}")
            print(f"  Xcorr A↔B: {r['xcorr']:.4f}")
    
    # === HEAD TO HEAD TABLE ===
    main_exps = ['Prime (full)', 'Composite (narrow)', 'Composite (wide)', 'Harmonic (1-6)', 'Single (all 1024)']
    main_exps = [e for e in main_exps if e in all_results]
    
    print(f"\n{'='*80}")
    print("HEAD-TO-HEAD COMPARISON")
    print(f"{'='*80}")
    header = f"{'Metric':>25} | " + " | ".join(f"{n:>14}" for n in main_exps)
    print(header)
    print("-" * len(header))
    
    metrics = [
        ('CH1 Vpp (mV)', 'ch1_vpp'),
        ('CH2 Vpp (mV)', 'ch2_vpp'),
        ('CH1 Peak (mV)', 'ch1_peak'),
        ('CH1 Flatness', 'ch1_flatness'),
        ('CH2 Flatness', 'ch2_flatness'),
        ('CH1 Peaks', 'ch1_npeaks'),
        ('CH1 Entropy', 'ch1_entropy'),
        ('Xcorr A↔B', 'xcorr'),
    ]
    
    for mname, key in metrics:
        vals = [all_results[e][key] for e in main_exps]
        fmt = '.0f' if 'Vpp' in mname or 'Peaks' in mname else '.3f' if 'Peak' not in mname else '.1f'
        row = f"{mname:>25} | " + " | ".join(f"{v:>14{fmt}}" for v in vals)
        print(row)
    
    # === PLOTS ===
    fig = plt.figure(figsize=(20, 20))
    fig.suptitle('Experiment Suite — Board 3, U2 — 22 May 2026', fontsize=16, fontweight='bold')
    
    # Panel 1: FFT overlay of main experiments
    ax1 = fig.add_subplot(3, 2, 1)
    colors_main = {'Prime (full)': 'gold', 'Composite (narrow)': 'dodgerblue', 
                   'Composite (wide)': 'red', 'Harmonic (1-6)': 'lime', 'Single (all 1024)': 'gray'}
    for name in main_exps:
        r = all_results[name]
        ax1.plot(r['ch1_freqs'], r['ch1_amps'], color=colors_main.get(name, 'white'), 
                alpha=0.8, linewidth=1, label=name)
    ax1.set_xlabel('Frequency (Hz)'); ax1.set_ylabel('Amplitude (mV)')
    ax1.set_title('CH1 FFT — All Configurations'); ax1.legend(fontsize=8); ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 1200)
    
    # Panel 2: Bar chart — key metrics
    ax2 = fig.add_subplot(3, 2, 2)
    x = np.arange(len(main_exps))
    w = 0.2
    ax2.bar(x - w, [all_results[e]['ch1_flatness'] for e in main_exps], w*2, 
            color=[colors_main.get(e, 'gray') for e in main_exps], edgecolor='black', label='Flatness')
    ax2.set_xticks(x); ax2.set_xticklabels([n.split('(')[0].strip() for n in main_exps], rotation=30, ha='right')
    ax2.set_ylabel('Spectral Flatness (lower = more structured)')
    ax2.set_title('Spectral Flatness Comparison'); ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Progressive addition — Vpp growth
    ax3 = fig.add_subplot(3, 2, 3)
    prog_names = [f'Prog {i}' for i in range(1, 7)]
    prog_keys = [f'Prog {i} ({["f₀/1","+ f₀/3","+ f₀/5","+ f₀/7","+ f₀/11","+ f₀/13"][i-1]})' for i in range(1, 7)]
    prog_keys = [k for k in prog_keys if k in all_results]
    ch1_vpps = [all_results[k]['ch1_vpp'] for k in prog_keys]
    ch2_vpps = [all_results[k]['ch2_vpp'] for k in prog_keys]
    x_prog = range(1, len(prog_keys)+1)
    ax3.plot(x_prog, ch1_vpps, 'gold', marker='o', linewidth=2, markersize=8, label='CH1 (TORSION_A)')
    ax3.plot(x_prog, ch2_vpps, 'cyan', marker='s', linewidth=2, markersize=8, label='CH2 (TORSION_B)')
    ax3.set_xlabel('Number of Prime Frequencies'); ax3.set_ylabel('Vpp (mV)')
    ax3.set_title('Progressive Addition — Signal Growth')
    ax3.set_xticks(list(x_prog))
    ax3.set_xticklabels(['f₀/1', '+f₀/3', '+f₀/5', '+f₀/7', '+f₀/11', '+f₀/13'])
    ax3.legend(); ax3.grid(True, alpha=0.3)
    
    # Panel 4: Progressive FFT waterfall
    ax4 = fig.add_subplot(3, 2, 4)
    prog_colors = plt.cm.viridis(np.linspace(0.2, 1.0, len(prog_keys)))
    for i, k in enumerate(prog_keys):
        r = all_results[k]
        ax4.plot(r['ch1_freqs'], r['ch1_amps'] + i*20, color=prog_colors[i], linewidth=1,
                label=k.split('(')[1].rstrip(')'))
    ax4.set_xlabel('Frequency (Hz)'); ax4.set_ylabel('Amplitude (mV) + offset')
    ax4.set_title('Progressive FFT Waterfall (CH1)'); ax4.legend(fontsize=7); ax4.grid(True, alpha=0.3)
    ax4.set_xlim(0, 1200)
    
    # Panel 5: Progressive metrics evolution
    ax5 = fig.add_subplot(3, 2, 5)
    flatness = [all_results[k]['ch1_flatness'] for k in prog_keys]
    entropy = [all_results[k]['ch1_entropy'] for k in prog_keys]
    xcorrs = [all_results[k]['xcorr'] for k in prog_keys]
    ax5_twin = ax5.twinx()
    ax5.plot(list(x_prog), flatness, 'r-o', label='Flatness', linewidth=2)
    ax5.plot(list(x_prog), entropy, 'b-s', label='Entropy', linewidth=2)
    ax5_twin.plot(list(x_prog), xcorrs, 'g-^', label='Xcorr A↔B', linewidth=2)
    ax5.set_xlabel('Number of Prime Frequencies'); ax5.set_ylabel('Flatness / Entropy')
    ax5_twin.set_ylabel('Cross-correlation', color='green')
    ax5.set_title('Progressive Metrics Evolution')
    ax5.set_xticks(list(x_prog))
    lines1, labels1 = ax5.get_legend_handles_labels()
    lines2, labels2 = ax5_twin.get_legend_handles_labels()
    ax5.legend(lines1 + lines2, labels1 + labels2, fontsize=8)
    ax5.grid(True, alpha=0.3)
    
    # Panel 6: Radar chart — main experiments
    ax6 = fig.add_subplot(3, 2, 6, projection='polar')
    radar_metrics = ['ch1_peak', 'ch2_peak', 'xcorr', 'ch1_npeaks', 'ch1_entropy']
    radar_labels = ['Peak Amp CH1', 'Peak Amp CH2', 'Xcorr', 'N Peaks', 'Entropy']
    angles = np.linspace(0, 2*np.pi, len(radar_metrics), endpoint=False)
    angles_c = np.append(angles, angles[0])
    
    for name in main_exps:
        r = all_results[name]
        vals = [r[m] for m in radar_metrics]
        # Normalize each to [0, 1] across experiments
        vals_norm = []
        for j, m in enumerate(radar_metrics):
            all_v = [all_results[e][m] for e in main_exps]
            mn, mx = min(all_v), max(all_v)
            vals_norm.append((r[m] - mn) / (mx - mn + 1e-15))
        vals_norm.append(vals_norm[0])
        ax6.plot(angles_c, vals_norm, color=colors_main.get(name, 'gray'), linewidth=2, label=name)
        ax6.fill(angles_c, vals_norm, color=colors_main.get(name, 'gray'), alpha=0.1)
    ax6.set_thetagrids(np.degrees(angles), radar_labels, fontsize=8)
    ax6.set_title('Normalized Metric Radar', pad=20)
    ax6.legend(fontsize=7, loc='lower right')
    
    plt.tight_layout()
    out = os.path.join(DATA, 'experiment_suite_22may.png')
    plt.savefig(out, dpi=150)
    print(f"\n📊 Full suite plot saved: {out}")

if __name__ == '__main__':
    main()
