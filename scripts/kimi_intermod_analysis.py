#!/usr/bin/env python3
"""
Amplitude-weighted intermodulation analysis — from Kimi K3 (Aug 11, 2026).
Implements clutter score, collision mass, and two-term model fitting.
Run against local V3 NPZ data.
"""

import math
import numpy as np
from scipy.signal import welch, find_peaks
from scipy.optimize import curve_fit
from itertools import product as iproduct
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "Adrian Docs/Pics/Test Point Readings/22 May Results - Board 3"

# === Frequency sets (f₀ = 1024 Hz) ===
SETS = {
    'prime_baseline': [1024, 341.3, 204.8, 146.3, 93.1, 78.8],       # /1,/3,/5,/7,/11,/13
    'composite_narrow': [512, 256, 170.7, 128, 113.8, 102.4],         # /2,/4,/6,/8,/9,/10
    'composite_wide': [512, 256, 170.7, 128, 102.4, 85.3],            # /2,/4,/6,/8,/10,/12
    'harmonic': [1024, 512, 341.3, 256, 204.8, 170.7],                # /1,/2,/3,/4,/5,/6
    'tusk_resonant': [1024, 512, 341.3, 204.8, 170.7, 146.3],         # /1,/2,/3,/5,/6,/7
    'coprime_357': [341.3, 204.8, 146.3],                              # /3,/5,/7
    'coprime_497': [256, 113.8, 146.3],                                # /4,/9,/7
}

# === NPZ file mapping (partial — extend as needed) ===
NPZ_MAP = {
    'prime_baseline': 'torsion_U2_prime_baseline_084347.npz',
    'composite_narrow': 'torsion_U2_composite_084548.npz',
    'composite_wide': 'torsion_U2_wide_composite_091536.npz',
    'harmonic': 'torsion_U2_harmonic_091551.npz',
    'tusk_resonant': 'torsion_U2_tusk_resonant_111438.npz',
}


def intermod_products(freqs, order=4):
    """Generate expected intermod frequencies and their theoretical weights."""
    products = defaultdict(float)
    n = len(freqs)
    for coeffs in iproduct(range(-order, order + 1), repeat=n):
        total_order = sum(abs(c) for c in coeffs)
        if total_order == 0 or total_order > order:
            continue
        f_imd = sum(c * f for c, f in zip(coeffs, freqs))
        if f_imd > 0:
            weight = 1.0 / (
                np.prod([math.factorial(abs(c)) for c in coeffs])
                * (total_order ** 2)
            )
            products[abs(f_imd)] += weight
    return products


def amplitude_weighted_clutter(freqs, v, sr, f_max=4096, nperseg=256):
    """Compute clutter ratio for a given frequency set and waveform."""
    f, psd = welch(v, fs=sr, nperseg=nperseg, window='hann', scaling='spectrum')
    products = intermod_products(freqs, order=4)

    clutter_power = 0
    carrier_power = 0

    for f_carrier in freqs:
        idx = np.argmin(np.abs(f - f_carrier))
        carrier_power += psd[idx]

    for f_imd, weight in products.items():
        if f_imd > f_max:
            continue
        idx = np.argmin(np.abs(f - f_imd))
        window = psd[max(0, idx - 2):min(len(psd), idx + 3)]
        measured = np.sum(window)
        clutter_power += measured * weight

    return {
        'clutter_power': clutter_power,
        'carrier_power': carrier_power,
        'clutter_ratio': clutter_power / (carrier_power + 1e-15),
        'n_products': len(products),
    }


def two_term_model(x, alpha, beta, gamma):
    """
    x: array of shape (n_samples, 3)
       x[:,0] = scaffold_score (mean carrier amplitude)
       x[:,1] = clutter_ratio
       x[:,2] = 1/LCM
    """
    scaffold = x[:, 0]
    clutter = x[:, 1]
    inv_lcm = x[:, 2]
    return alpha * scaffold - beta * (clutter ** gamma) * inv_lcm


def main():
    print("=" * 80)
    print("KIMI K3 — AMPLITUDE-WEIGHTED INTERMOD ANALYSIS")
    print("=" * 80)

    for name, npz_file in NPZ_MAP.items():
        path = DATA_DIR / npz_file
        if not path.exists():
            print(f"\n{name}: FILE NOT FOUND")
            continue

        d = np.load(path)
        v1 = d['v1']
        sr = d['sample_rate'] if 'sample_rate' in d else 1.0 / np.median(np.diff(d['t1']))
        freqs = SETS[name]

        result = amplitude_weighted_clutter(freqs, v1, sr)
        print(f"\n{name}:")
        print(f"  Carrier power:  {result['carrier_power']:.6f}")
        print(f"  Clutter power:  {result['clutter_power']:.6f}")
        print(f"  Clutter ratio:  {result['clutter_ratio']:.4f}")
        print(f"  N products:     {result['n_products']}")

    # Intermod comparison for {3,5,7} vs {4,9,7}
    print("\n" + "=" * 80)
    print("{3,5,7} vs {4,9,7} — INTERMOD PRODUCT COMPARISON")
    print("=" * 80)

    for name, freqs in [('coprime_357', SETS['coprime_357']), ('coprime_497', SETS['coprime_497'])]:
        products = intermod_products(freqs, order=5)
        in_band = {f: w for f, w in products.items() if f <= 1200}
        total_weight = sum(products.values())
        in_band_weight = sum(in_band.values())
        print(f"\n{name}:")
        print(f"  Total products:    {len(products)}")
        print(f"  In-band (0-1200):  {len(in_band)}")
        print(f"  Total weight:      {total_weight:.4f}")
        print(f"  In-band weight:    {in_band_weight:.4f}")
        print(f"  LCM:               {name} → {'105' if '357' in name else '252'}")


if __name__ == '__main__':
    main()
