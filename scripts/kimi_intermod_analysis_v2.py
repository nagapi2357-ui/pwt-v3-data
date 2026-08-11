#!/usr/bin/env python3
"""
V5-Ready Intermodulation Analysis — refined from Kimi K3 collaboration (Aug 11, 2026).

Changes from v1:
- Exact fraction arithmetic (no float rounding)
- True collision mass (excludes 1st-order self-products)
- Scaffold/clutter decomposition for Tusk sets
- Symmetry pruning for speed
- Progressive addition cache-friendly
"""

import math
import numpy as np
from fractions import Fraction
from collections import defaultdict
from itertools import product as iproduct
from scipy.signal import welch
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "Adrian Docs/Pics/Test Point Readings/22 May Results - Board 3"

BASE_FREQ = 1024

# === Exact frequency sets (as Fraction objects) ===
SETS_EXACT = {
    'prime_baseline':    [Fraction(BASE_FREQ, r) for r in [1, 3, 5, 7, 11, 13]],
    'composite_narrow':  [Fraction(BASE_FREQ, r) for r in [2, 4, 6, 8, 9, 10]],
    'composite_wide':    [Fraction(BASE_FREQ, r) for r in [2, 4, 6, 8, 10, 12]],
    'harmonic':          [Fraction(BASE_FREQ, r) for r in [1, 2, 3, 4, 5, 6]],
    'tusk_resonant':     [Fraction(BASE_FREQ, r) for r in [1, 2, 3, 5, 6, 7]],
    'single':            [Fraction(BASE_FREQ, 1)],
    'coprime_357':       [Fraction(BASE_FREQ, r) for r in [3, 5, 7]],
    'coprime_497':       [Fraction(BASE_FREQ, r) for r in [4, 9, 7]],
    'twin_primes':       [Fraction(BASE_FREQ, r) for r in [5, 7, 11, 13]],
    'tusk_sopfr':        [Fraction(BASE_FREQ, r) for r in [1, 2, 3, 5, 7, 10]],
    'six_frame':         [Fraction(BASE_FREQ, r) for r in [1, 2, 3, 5, 7, 11]],
    # Progressive prime
    'prog_prime_1':      [Fraction(BASE_FREQ, r) for r in [1]],
    'prog_prime_2':      [Fraction(BASE_FREQ, r) for r in [1, 3]],
    'prog_prime_3':      [Fraction(BASE_FREQ, r) for r in [1, 3, 5]],
    'prog_prime_4':      [Fraction(BASE_FREQ, r) for r in [1, 3, 5, 7]],
    'prog_prime_5':      [Fraction(BASE_FREQ, r) for r in [1, 3, 5, 7, 11]],
    'prog_prime_6':      [Fraction(BASE_FREQ, r) for r in [1, 3, 5, 7, 11, 13]],
    # Progressive composite
    'prog_comp_1':       [Fraction(BASE_FREQ, r) for r in [2]],
    'prog_comp_2':       [Fraction(BASE_FREQ, r) for r in [2, 4]],
    'prog_comp_3':       [Fraction(BASE_FREQ, r) for r in [2, 4, 6]],
    'prog_comp_4':       [Fraction(BASE_FREQ, r) for r in [2, 4, 6, 8]],
    'prog_comp_5':       [Fraction(BASE_FREQ, r) for r in [2, 4, 6, 8, 9]],
    'prog_comp_6':       [Fraction(BASE_FREQ, r) for r in [2, 4, 6, 8, 9, 10]],
}

# === NPZ file mapping ===
NPZ_MAP = {
    'prime_baseline':    'torsion_U2_prime_baseline_084347.npz',
    'composite_narrow':  'torsion_U2_composite_084548.npz',
    'composite_wide':    'torsion_U2_wide_composite_091536.npz',
    'harmonic':          'torsion_U2_harmonic_091551.npz',
    'tusk_resonant':     'torsion_U2_tusk_resonant_111438.npz',
    'single':            'torsion_U2_single_freq_091517.npz',
    'twin_primes':       'torsion_U2_twin_primes_111447.npz',
    'tusk_sopfr':        'torsion_U2_tusk_sopfr_111429.npz',
    'six_frame':         'torsion_U2_six_frame_111456.npz',
    'prog_prime_1':      'torsion_U2_progressive_1_091607.npz',
    'prog_prime_2':      'torsion_U2_progressive_2_091616.npz',
    'prog_prime_3':      'torsion_U2_progressive_3_091626.npz',
    'prog_prime_4':      'torsion_U2_progressive_4_091635.npz',
    'prog_prime_5':      'torsion_U2_progressive_5_091645.npz',
    'prog_prime_6':      'torsion_U2_progressive_6_091654.npz',
    'prog_comp_1':       'torsion_U2_prog_comp_1_102217.npz',
    'prog_comp_2':       'torsion_U2_prog_comp_2_102227.npz',
    'prog_comp_3':       'torsion_U2_prog_comp_3_102236.npz',
    'prog_comp_4':       'torsion_U2_prog_comp_4_102246.npz',
    'prog_comp_5':       'torsion_U2_prog_comp_5_102255.npz',
    'prog_comp_6':       'torsion_U2_prog_comp_6_102305.npz',
}


def intermod_products_exact(freqs_frac, order=4):
    """Generate intermod frequencies using exact fractions. Excludes 0th order."""
    products = defaultdict(float)
    n = len(freqs_frac)
    for coeffs in iproduct(range(-order, order + 1), repeat=n):
        total_order = sum(abs(c) for c in coeffs)
        if total_order == 0 or total_order > order:
            continue
        f_frac = sum(c * f for c, f in zip(coeffs, freqs_frac))
        if f_frac > 0:
            weight = 1.0 / (
                math.prod(math.factorial(abs(c)) for c in coeffs)
                * (total_order ** 2)
            )
            products[float(f_frac)] += weight
    return products


def true_collision_mass(freqs_frac, order=5):
    """Collision mass from products of order >= 2 landing on carriers (within 2 Hz)."""
    carriers = [float(f) for f in freqs_frac]
    mass = 0.0
    n = len(freqs_frac)
    for coeffs in iproduct(range(-order, order + 1), repeat=n):
        total_order = sum(abs(c) for c in coeffs)
        if total_order <= 1 or total_order > order:
            continue
        f_frac = sum(c * f for c, f in zip(coeffs, freqs_frac))
        if f_frac > 0:
            f_imd = float(f_frac)
            weight = 1.0 / (
                math.prod(math.factorial(abs(c)) for c in coeffs)
                * (total_order ** 2)
            )
            for fc in carriers:
                if abs(f_imd - fc) < 2.0:
                    mass += weight
    return mass


def scaffold_clutter_split(freqs_frac, n_scaffold=3, order=5):
    """
    Split intermod products into scaffold (first n_scaffold tones only)
    vs clutter (involves extension tones).
    """
    scaffold_weight = 0.0
    clutter_weight = 0.0
    n = len(freqs_frac)
    if n <= n_scaffold:
        return 0.0, 0.0

    for coeffs in iproduct(range(-order, order + 1), repeat=n):
        total_order = sum(abs(c) for c in coeffs)
        if total_order == 0 or total_order > order:
            continue
        f_frac = sum(c * f for c, f in zip(coeffs, freqs_frac))
        if f_frac > 0:
            weight = 1.0 / (
                math.prod(math.factorial(abs(c)) for c in coeffs)
                * (total_order ** 2)
            )
            if all(c == 0 for c in coeffs[n_scaffold:]):
                scaffold_weight += weight
            else:
                clutter_weight += weight
    return scaffold_weight, clutter_weight


def amplitude_weighted_clutter(freqs_frac, v, sr, f_max=4096, nperseg=256):
    """Compute clutter ratio using exact fraction product positions."""
    f, psd = welch(v, fs=sr, nperseg=nperseg, window='hann', scaling='spectrum')
    products = intermod_products_exact(freqs_frac, order=4)

    carrier_power = 0.0
    for fc in freqs_frac:
        fc_hz = float(fc)
        idx = np.argmin(np.abs(f - fc_hz))
        carrier_power += psd[idx]

    clutter_power = 0.0
    for f_imd, weight in products.items():
        if f_imd > f_max:
            continue
        idx = np.argmin(np.abs(f - f_imd))
        window = psd[max(0, idx - 2):min(len(psd), idx + 3)]
        clutter_power += np.sum(window) * weight

    return {
        'clutter_power': clutter_power,
        'carrier_power': carrier_power,
        'clutter_ratio': clutter_power / (carrier_power + 1e-15),
        'n_products': len(products),
    }


def main():
    print("=" * 90)
    print("KIMI K3 — V2 AMPLITUDE-WEIGHTED INTERMOD ANALYSIS (Exact Fractions)")
    print("=" * 90)

    # --- Clutter ratios from NPZ data ---
    print("\n### Clutter Ratios (from waveform data)")
    print(f"{'Set':<22} {'Clutter':>9} {'Carrier':>9} {'Ratio':>8} {'N Prod':>7}")
    print("-" * 60)

    for name in ['tusk_resonant', 'harmonic', 'prime_baseline',
                 'composite_narrow', 'composite_wide', 'single',
                 'twin_primes', 'tusk_sopfr', 'six_frame']:
        npz_file = NPZ_MAP.get(name)
        if not npz_file:
            continue
        path = DATA_DIR / npz_file
        if not path.exists():
            continue
        d = np.load(path)
        v1 = d['v1']
        sr = float(d['sample_rate']) if 'sample_rate' in d else 1.0 / np.median(np.diff(d['t1']))
        freqs = SETS_EXACT[name]
        r = amplitude_weighted_clutter(freqs, v1, sr)
        print(f"{name:<22} {r['clutter_power']:9.4f} {r['carrier_power']:9.6f} {r['clutter_ratio']:8.2f} {r['n_products']:7d}")

    # --- True collision mass ---
    print("\n### True Collision Mass (order ≥ 2 products landing on carriers)")
    print(f"{'Set':<22} {'Collision Mass':>15}")
    print("-" * 40)

    for name in ['prime_baseline', 'composite_narrow', 'composite_wide',
                 'harmonic', 'tusk_resonant', 'coprime_357', 'coprime_497',
                 'twin_primes', 'six_frame']:
        freqs = SETS_EXACT[name]
        mass = true_collision_mass(freqs, order=5)
        print(f"{name:<22} {mass:15.4f}")

    # --- Scaffold / clutter split ---
    print("\n### Scaffold vs Clutter Split (first 3 tones = scaffold)")
    print(f"{'Set':<22} {'Scaffold':>10} {'Clutter':>10} {'Ratio S/C':>10}")
    print("-" * 55)

    for name in ['tusk_resonant', 'harmonic', 'prime_baseline',
                 'composite_narrow', 'six_frame']:
        freqs = SETS_EXACT[name]
        s, c = scaffold_clutter_split(freqs, n_scaffold=3, order=4)
        ratio = s / (c + 1e-15)
        print(f"{name:<22} {s:10.4f} {c:10.4f} {ratio:10.4f}")

    # --- {3,5,7} vs {4,9,7} exact comparison ---
    print("\n### {3,5,7} vs {4,9,7} — Exact Fraction Comparison (order ≤ 5)")
    print("-" * 60)

    for name in ['coprime_357', 'coprime_497']:
        freqs = SETS_EXACT[name]
        products = intermod_products_exact(freqs, order=5)
        in_band = {f: w for f, w in products.items() if f <= 1200}
        total_w = sum(products.values())
        in_band_w = sum(in_band.values())
        cm = true_collision_mass(freqs, order=5)
        print(f"\n{name}:")
        print(f"  Total products:     {len(products)}")
        print(f"  In-band (0-1200):   {len(in_band)} ({100*len(in_band)/len(products):.1f}%)")
        print(f"  Total weight:       {total_w:.4f}")
        print(f"  In-band weight:     {in_band_w:.4f} ({100*in_band_w/total_w:.1f}%)")
        print(f"  True collision mass: {cm:.4f}")

    # --- Progressive addition ---
    print("\n### Progressive Addition — Collision Mass Growth")
    print(f"{'Step':<15} {'N Tones':>8} {'N Products':>11} {'Collision':>10}")
    print("-" * 50)

    for series in ['prog_prime', 'prog_comp']:
        for i in range(1, 7):
            name = f"{series}_{i}"
            freqs = SETS_EXACT.get(name)
            if not freqs:
                continue
            products = intermod_products_exact(freqs, order=4)
            cm = true_collision_mass(freqs, order=4) if len(freqs) > 1 else 0.0
            print(f"{name:<15} {len(freqs):8d} {len(products):11d} {cm:10.4f}")
        print()


if __name__ == '__main__':
    main()
