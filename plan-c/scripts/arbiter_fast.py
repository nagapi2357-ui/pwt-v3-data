#!/usr/bin/env python3
"""
arbiter_fast.py — Fast measurement-only run (no waveform downloads).

Collects SCPI measurements (Vpp, Vrms, Freq) for all 3 signal channels
per trial. Skips waveform download to keep ~2-3s per trial.
Full waveform capture can be done separately for interesting pairs.
"""

from __future__ import annotations

import csv
import glob
import json
import os
import random
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

# Import test matrix
sys.path.insert(0, str(Path(__file__).parent))
from test_matrix import ALL_PAIRS, PHASE_OFFSETS_DEG, N_BLOCKS, TestPair


# ═══════════════════════════════════════════════════════════════════════════
# Scope (minimal SCPI)
# ═══════════════════════════════════════════════════════════════════════════

class Scope:
    def __init__(self, ip="169.254.201.110", port=5555, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((ip, port))
        self.timeout = timeout
        idn = self.query("*IDN?")
        print(f"  Scope: {idn.strip()}")

    def write(self, cmd):
        self.sock.sendall((cmd + "\n").encode())

    def query(self, cmd):
        self.write(cmd)
        self.sock.settimeout(self.timeout)
        chunks = []
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
                self.sock.settimeout(0.3)
            except socket.timeout:
                break
        self.sock.settimeout(self.timeout)
        return b"".join(chunks).decode(errors="replace").strip()

    def measure(self, channel):
        """Get Vpp, Vrms for a channel. Returns dict."""
        ch = f"CHAN{channel}"
        results = {}
        for item in ["VPP", "VRMS"]:
            self.write(f":MEAS:ITEM {item},{ch}")
            time.sleep(0.08)
            val = self.query(f":MEAS:ITEM? {item},{ch}")
            try:
                v = float(val)
                results[item.lower()] = v if v < 1e30 else float("nan")
            except ValueError:
                results[item.lower()] = float("nan")
        return results

    def measure_all(self):
        """Measure Vpp+Vrms for CH1,CH2,CH3 in one batch."""
        results = {}
        for ch in [1, 2, 3]:
            results[ch] = self.measure(ch)
        return results

    def setup(self):
        """Configure scope for experiment."""
        cmds = [
            ":CHAN1:DISP ON", ":CHAN2:DISP ON", ":CHAN3:DISP ON",
            ":CHAN1:COUP DC", ":CHAN1:PROB 1", ":CHAN1:SCAL 0.2", ":CHAN1:OFFS 0",
            ":CHAN2:COUP DC", ":CHAN2:PROB 1", ":CHAN2:SCAL 0.2", ":CHAN2:OFFS 0",
            ":CHAN3:COUP DC", ":CHAN3:PROB 1", ":CHAN3:SCAL 0.2", ":CHAN3:OFFS 0",
            ":TRIG:MODE EDGE", ":TRIG:EDGE:SOUR CHAN1",
            ":TRIG:EDGE:SLOP POS", ":TRIG:EDGE:LEV 0",
            ":ACQ:MDEP AUTO",
        ]
        for c in cmds:
            self.write(c)
            time.sleep(0.03)
        time.sleep(0.3)
        print("  Scope configured.")

    def set_timebase(self, capture_ms):
        scale_s = (capture_ms / 1000.0) / 10.0
        valid = [0.000001, 0.000002, 0.000005,
                 0.00001, 0.00002, 0.00005,
                 0.0001, 0.0002, 0.0005,
                 0.001, 0.002, 0.005,
                 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
        best = min(valid, key=lambda v: abs(v - scale_s) if v >= scale_s * 0.8 else float("inf"))
        self.write(f":TIM:MAIN:SCAL {best}")

    def capture(self):
        """Free-run capture: RUN → settle → STOP."""
        self.write(":RUN")
        time.sleep(0.5)
        self.write(":STOP")
        time.sleep(0.2)

    def close(self):
        try:
            self.sock.close()
        except:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# Teensy (minimal serial)
# ═══════════════════════════════════════════════════════════════════════════

class Teensy:
    def __init__(self, port=None):
        import serial
        if port is None:
            for pat in ["/dev/tty.usbmodem*", "/dev/ttyACM*"]:
                matches = glob.glob(pat)
                if matches:
                    port = matches[0]
                    break
            else:
                raise FileNotFoundError("No Teensy found")
        self.ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        self.ser.reset_input_buffer()
        print(f"  Teensy: {port}")

    def send(self, cmd):
        self.ser.reset_input_buffer()
        self.ser.write((cmd.strip() + "\n").encode())
        time.sleep(0.05)
        lines = []
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if self.ser.in_waiting:
                line = self.ser.readline().decode(errors="replace").strip()
                if line:
                    lines.append(line)
                    if line.startswith("OK") or line.startswith("ERR"):
                        break
            else:
                time.sleep(0.01)
        return "\n".join(lines)

    def set_pair(self, f1, f2, phase_deg):
        self.send(f"FA {f1:.1f}")
        self.send(f"FB {f2:.1f}")
        self.send(f"PB {phase_deg:.1f}")

    def off(self):
        self.send("OFF BOTH")

    def close(self):
        self.ser.close()


# ═══════════════════════════════════════════════════════════════════════════
# Main experiment
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", type=int, default=N_BLOCKS)
    parser.add_argument("--settle", type=float, default=0.5, help="Settle time after freq change (s)")
    args = parser.parse_args()

    n_blocks = args.blocks
    pairs = ALL_PAIRS
    phases = PHASE_OFFSETS_DEG
    total = len(pairs) * n_blocks * len(phases)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(__file__).parent / "results" / "runs" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  FAST RUN — {ts}")
    print(f"  {len(pairs)} pairs × {n_blocks} blocks × {len(phases)} phases = {total} trials")
    print(f"  Est: ~{total * 3 / 60:.0f} minutes")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    print("Connecting...")
    scope = Scope()
    teensy = Teensy()
    scope.setup()

    csv_path = out_dir / "results.csv"
    fields = [
        "trial", "block", "pair_id", "stratum", "ratio", "f1", "f2",
        "phase_offset", "vpp_ch1", "vrms_ch1",
        "vpp_ch2", "vrms_ch2",
        "vpp_ch3", "vrms_ch3", "timestamp",
    ]
    csv_file = open(csv_path, "w", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=fields)
    writer.writeheader()

    trial = 0
    t0 = time.time()

    try:
        for block in range(1, n_blocks + 1):
            block_pairs = list(pairs)
            random.shuffle(block_pairs)
            print(f"\n── Block {block}/{n_blocks} ──")

            for pair in block_pairs:
                for phase_deg in phases:
                    trial += 1

                    # Set frequencies
                    teensy.set_pair(pair.f1, pair.f2, phase_deg)
                    time.sleep(args.settle)

                    # Set timebase for this pair
                    scope.set_timebase(pair.capture_ms)

                    # Capture
                    scope.capture()

                    # Measure all 3 channels
                    meas = scope.measure_all()

                    row = {
                        "trial": trial, "block": block,
                        "pair_id": pair.pair_id, "stratum": pair.stratum,
                        "ratio": pair.ratio_label,
                        "f1": pair.f1, "f2": pair.f2,
                        "phase_offset": phase_deg,
                        "vpp_ch1": meas[1]["vpp"], "vrms_ch1": meas[1]["vrms"],
                        "vpp_ch2": meas[2]["vpp"], "vrms_ch2": meas[2]["vrms"],
                        "vpp_ch3": meas[3]["vpp"], "vrms_ch3": meas[3]["vrms"],
                        "timestamp": datetime.now().isoformat(),
                    }
                    writer.writerow(row)
                    csv_file.flush()

                    # Progress every 10 trials
                    if trial % 10 == 0 or trial == 1:
                        elapsed = time.time() - t0
                        rate = trial / elapsed if elapsed > 0 else 0
                        eta = (total - trial) / rate / 60 if rate > 0 else 0
                        print(f"  [{trial}/{total}] {pair.pair_id} {pair.ratio_label} "
                              f"p={phase_deg}° | CH3 Vpp={meas[3]['vpp']:.3f}V | "
                              f"{elapsed:.0f}s elapsed, ~{eta:.0f}min left")

            # Block summary
            print(f"\n  Block {block} done. {trial} trials total, "
                  f"{time.time()-t0:.0f}s elapsed")

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted!")
    finally:
        csv_file.close()
        teensy.off()
        scope.close()
        teensy.close()

    # Save metadata
    meta = {
        "timestamp": ts, "n_blocks": n_blocks,
        "n_pairs": len(pairs), "n_phases": len(phases),
        "total_trials": trial, "mode": "fast_measurements_only",
        "elapsed_s": round(time.time() - t0, 1),
    }
    with open(out_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Done! {trial} trials in {time.time()-t0:.0f}s")
    print(f"   Data: {csv_path}")


if __name__ == "__main__":
    main()
