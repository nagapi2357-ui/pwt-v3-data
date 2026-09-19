"""
test_matrix.py — Test pair definitions for the Arbiter experiment.

30 pairs across 5 strata, matching test-matrix.md Rev 2.1.
Geometric mean target: 5000 Hz for all pairs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TestPair:
    pair_id: str
    stratum: str          # PP, CC, PC, NC, IR
    ratio_label: str      # e.g. "3:2", "√2:1"
    ratio_decimal: float
    f1: float             # Hz (higher freq)
    f2: float             # Hz (lower freq)
    gm: float             # geometric mean (always 5000)
    beat_hz: float        # |f1 - f2|
    ln_ratio: float       # ln(a/b)
    capture_ms: int       # short capture duration per window rule
    comparison_class: str  # A, B1, B2, B3, C, D, or ""
    notes: str = ""


# Geometric mean
GM = 5000.0

def _pair(pid: str, stratum: str, label: str, a: float, b: float,
          capture_ms: int, comp_class: str = "", notes: str = "") -> TestPair:
    ratio = a / b
    f1 = GM * math.sqrt(ratio)
    f2 = GM / math.sqrt(ratio)
    return TestPair(
        pair_id=pid, stratum=stratum, ratio_label=label,
        ratio_decimal=round(ratio, 6),
        f1=round(f1, 1), f2=round(f2, 1), gm=GM,
        beat_hz=round(abs(f1 - f2), 1),
        ln_ratio=round(math.log(ratio), 4),
        capture_ms=capture_ms, comparison_class=comp_class, notes=notes,
    )


# ── Stratum 1: Prime:Prime, Coprime ──────────────────────────────────────
PP1 = _pair("PP1", "PP", "3:2",   3, 2,  100, "")
PP2 = _pair("PP2", "PP", "5:3",   5, 3,  100, "B3")
PP3 = _pair("PP3", "PP", "7:5",   7, 5,  100, "B1")
PP4 = _pair("PP4", "PP", "11:7", 11, 7,  100, "B2")
PP5 = _pair("PP5", "PP", "13:11",13,11,  120, "A")
PP6 = _pair("PP6", "PP", "7:3",   7, 3,  100, "C")
PP7 = _pair("PP7", "PP", "5:2",   5, 2,  100, "C")
PP8 = _pair("PP8", "PP", "11:3", 11, 3,  100, "D")

# ── Stratum 2: Composite:Composite, Coprime ──────────────────────────────
CC1 = _pair("CC1", "CC", "9:8",    9,  8, 100, "A")
CC2 = _pair("CC2", "CC", "25:16", 25, 16, 200, "B2")
CC3 = _pair("CC3", "CC", "9:4",    9,  4, 100, "C")
CC4 = _pair("CC4", "CC", "15:8",  15,  8, 100, "")
CC5 = _pair("CC5", "CC", "25:9",  25,  9, 100, "C")
CC6 = _pair("CC6", "CC", "49:25", 49, 25, 100, "")
CC7 = _pair("CC7", "CC", "36:25", 36, 25, 100, "B1")
CC8 = _pair("CC8", "CC", "49:32", 49, 32, 100, "")
CC9 = _pair("CC9", "CC", "27:16", 27, 16, 100, "B3")

# ── Stratum 3: Prime:Composite, Coprime ──────────────────────────────────
PC1 = _pair("PC1", "PC", "5:4",   5,  4, 100, "A")
PC2 = _pair("PC2", "PC", "11:8", 11,  8, 100, "")
PC3 = _pair("PC3", "PC", "13:9", 13,  9, 100, "")
PC4 = _pair("PC4", "PC", "7:4",   7,  4, 100, "")
PC5 = _pair("PC5", "PC", "11:4", 11,  4, 100, "C")
PC6 = _pair("PC6", "PC", "13:4", 13,  4, 100, "D")

# ── Stratum 4: Non-Coprime (sanity checks) ──────────────────────────────
NC1 = _pair("NC1", "NC", "4:2",    4,  2, 100, "", "Must match 2:1")
NC2 = _pair("NC2", "NC", "9:6",    9,  6, 100, "", "Must match PP1 (3:2)")
NC3 = _pair("NC3", "NC", "15:10", 15, 10, 100, "", "Must match PP1 (3:2)")

# ── Stratum 5: Irrational Ratios ─────────────────────────────────────────
_phi = (1 + math.sqrt(5)) / 2
IR1 = _pair("IR1", "IR", "√2:1",   math.sqrt(2), 1, 100, "")
IR2 = _pair("IR2", "IR", "φ:1",    _phi,          1, 100, "B3")
IR3 = _pair("IR3", "IR", "e/2:1",  math.e / 2,    1, 100, "A")
IR4 = _pair("IR4", "IR", "π/2:1",  math.pi / 2,   1, 100, "B2")


# ── All pairs in canonical order ──────────────────────────────────────────
ALL_PAIRS: list[TestPair] = [
    PP1, PP2, PP3, PP4, PP5, PP6, PP7, PP8,
    CC1, CC2, CC3, CC4, CC5, CC6, CC7, CC8, CC9,
    PC1, PC2, PC3, PC4, PC5, PC6,
    NC1, NC2, NC3,
    IR1, IR2, IR3, IR4,
]

# Convenience lookups
PAIRS_BY_ID: dict[str, TestPair] = {p.pair_id: p for p in ALL_PAIRS}
PAIRS_BY_STRATUM: dict[str, list[TestPair]] = {}
for p in ALL_PAIRS:
    PAIRS_BY_STRATUM.setdefault(p.stratum, []).append(p)
PAIRS_BY_CLASS: dict[str, list[TestPair]] = {}
for p in ALL_PAIRS:
    if p.comparison_class:
        PAIRS_BY_CLASS.setdefault(p.comparison_class, []).append(p)

# Phase offsets (8 evenly spaced, in degrees)
PHASE_OFFSETS_DEG: list[float] = [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]

# Default experiment parameters
N_BLOCKS = 5
LONG_CAPTURE_MS = 2000  # for high-resolution spectral analysis
SCREENSHOT_EVERY_N = 30  # save scope screenshot every N trials


if __name__ == "__main__":
    print(f"Total pairs: {len(ALL_PAIRS)}")
    for s in ["PP", "CC", "PC", "NC", "IR"]:
        pairs = PAIRS_BY_STRATUM[s]
        print(f"  {s}: {len(pairs)} pairs")
    print(f"\nComparison classes:")
    for cls in sorted(PAIRS_BY_CLASS):
        ids = [p.pair_id for p in PAIRS_BY_CLASS[cls]]
        print(f"  {cls}: {ids}")
    print(f"\nPhase offsets: {PHASE_OFFSETS_DEG}")
    print(f"Blocks: {N_BLOCKS}, Total trials: {len(ALL_PAIRS) * N_BLOCKS * len(PHASE_OFFSETS_DEG)}")
