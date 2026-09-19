#!/usr/bin/env python3
"""
arbiter_full.py — Complete data collection: characterisation + waveform run.

Phase 1: Signal chain characterisation (~10 min)
Phase 2: Full waveform capture with RSP + all metrics (~3-4 hours)

All data saved for post-hoc analysis. Designed to run unattended via nohup.
"""

from __future__ import annotations

import csv
import glob
import json
import math
import os
import random
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.signal import hilbert

sys.path.insert(0, str(Path(__file__).parent))
from test_matrix import ALL_PAIRS, PHASE_OFFSETS_DEG, N_BLOCKS, TestPair
from rsp import compute_rsp, compute_metrics, compute_rsp_two_channel


# ═══════════════════════════════════════════════════════════════════════════
# Scope — SCPI interface
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

    def query_binary(self, cmd):
        """Send query, return binary response (handles TMC header)."""
        self.write(cmd)
        self.sock.settimeout(self.timeout)
        # Read until '#' header
        header = b""
        while len(header) < 2:
            header += self.sock.recv(2 - len(header))
        idx = header.find(b"#")
        if idx < 0:
            rest = self._recv_all()
            return header + rest
        while len(header) < idx + 2:
            header += self.sock.recv(1)
        n_digits = int(chr(header[idx + 1]))
        if n_digits == 0:
            return self._recv_all()
        digits = b""
        while len(digits) < n_digits:
            digits += self.sock.recv(n_digits - len(digits))
        data_len = int(digits)
        data = bytearray()
        while len(data) < data_len:
            chunk = self.sock.recv(min(65536, data_len - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        try:
            self.sock.settimeout(0.2)
            self.sock.recv(2)
        except socket.timeout:
            pass
        self.sock.settimeout(self.timeout)
        return bytes(data)

    def _recv_all(self):
        chunks = []
        self.sock.settimeout(0.3)
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
            except socket.timeout:
                break
        self.sock.settimeout(self.timeout)
        return b"".join(chunks)

    def measure(self, channel, items=("VPP", "VRMS")):
        ch = f"CHAN{channel}"
        results = {}
        for item in items:
            self.write(f":MEAS:ITEM {item},{ch}")
            time.sleep(0.08)
            val = self.query(f":MEAS:ITEM? {item},{ch}")
            try:
                v = float(val)
                results[item.lower()] = v if v < 1e30 else float("nan")
            except ValueError:
                results[item.lower()] = float("nan")
        return results

    def measure_freq(self, channel):
        ch = f"CHAN{channel}"
        self.write(f":MEAS:ITEM FREQ,{ch}")
        time.sleep(0.1)
        val = self.query(f":MEAS:ITEM? FREQ,{ch}")
        try:
            v = float(val)
            return v if v < 1e30 else float("nan")
        except ValueError:
            return float("nan")

    def get_waveform(self, channel):
        """Download NORM waveform. Returns (voltage_array, sample_rate)."""
        ch = f"CHAN{channel}"
        self.write(f":WAV:SOUR {ch}")
        self.write(":WAV:MODE NORM")
        self.write(":WAV:FORM BYTE")
        time.sleep(0.1)

        pre_str = self.query(":WAV:PRE?")
        pre = pre_str.split(",")
        if len(pre) < 10:
            return np.array([]), 0.0

        points = int(pre[2])
        x_inc = float(pre[4])
        y_inc = float(pre[7])
        y_orig = float(pre[8])
        y_ref = float(pre[9])
        sr = 1.0 / x_inc if x_inc > 0 else 1e6

        self.write(":WAV:STAR 1")
        self.write(f":WAV:STOP {min(points, 1200)}")
        time.sleep(0.05)
        raw = self.query_binary(":WAV:DATA?")

        if len(raw) == 0:
            return np.array([]), sr

        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        voltage = (arr - y_ref - y_orig) * y_inc
        return voltage, sr

    def setup(self, v_scale=0.2):
        """Configure scope channels."""
        cmds = [
            ":CHAN1:DISP ON", ":CHAN2:DISP ON", ":CHAN3:DISP ON",
            ":CHAN1:COUP DC", ":CHAN1:PROB 1", f":CHAN1:SCAL {v_scale}", ":CHAN1:OFFS 0",
            ":CHAN2:COUP DC", ":CHAN2:PROB 1", f":CHAN2:SCAL {v_scale}", ":CHAN2:OFFS 0",
            ":CHAN3:COUP DC", ":CHAN3:PROB 1", f":CHAN3:SCAL {v_scale}", ":CHAN3:OFFS 0",
            ":TRIG:MODE EDGE", ":TRIG:EDGE:SOUR CHAN1",
            ":TRIG:EDGE:SLOP POS", ":TRIG:EDGE:LEV 0",
            ":ACQ:MDEP AUTO",
        ]
        for c in cmds:
            self.write(c)
            time.sleep(0.03)
        time.sleep(0.3)
        print("  Scope configured.")

    def set_timebase_for_freq(self, f_low, f_high):
        """Set timebase to show ~5-10 cycles of the beat frequency or lowest freq."""
        beat = abs(f_high - f_low)
        # Show at least 3 beat cycles, or 5 cycles of lowest freq
        if beat > 10:
            target_ms = 3000.0 / beat  # 3 beat cycles in ms
        else:
            target_ms = 5000.0 / f_low  # 5 cycles of low freq
        target_ms = max(target_ms, 1.0)  # at least 1ms
        target_ms = min(target_ms, 500.0)  # at most 500ms

        scale_s = (target_ms / 1000.0) / 10.0
        valid = [0.000002, 0.000005, 0.00001, 0.00002, 0.00005,
                 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005,
                 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
        best = min(valid, key=lambda v: abs(v - scale_s) if v >= scale_s * 0.8 else float("inf"))
        self.write(f":TIM:MAIN:SCAL {best}")
        return best

    def capture(self, settle_s=0.5):
        self.write(":RUN")
        time.sleep(settle_s)
        self.write(":STOP")
        time.sleep(0.3)

    def screenshot(self, filename):
        try:
            data = self.query_binary(":DISP:DATA? ON,OFF,PNG")
        except Exception:
            data = self.query_binary(":DISP:DATA? ON,OFF,BMP")
            filename = filename.replace(".png", ".bmp")
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "wb") as f:
            f.write(data)

    def close(self):
        try:
            self.sock.close()
        except:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# Teensy
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

    def set_freq_a(self, f): return self.send(f"FA {f:.1f}")
    def set_freq_b(self, f): return self.send(f"FB {f:.1f}")
    def set_phase_b(self, deg): return self.send(f"PB {deg:.1f}")

    def set_pair(self, f1, f2, phase_deg):
        self.set_freq_a(f1)
        self.set_freq_b(f2)
        self.set_phase_b(phase_deg)

    def off(self):
        self.send("OFF BOTH")

    def close(self):
        self.ser.close()


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Characterisation
# ═══════════════════════════════════════════════════════════════════════════

def run_characterisation(scope, teensy, out_dir):
    """Signal chain validation."""
    print(f"\n{'='*60}")
    print(f"  PHASE 1: CHARACTERISATION")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    # ── Single-tone amplitude vs frequency ──
    print("── Single-Tone Sweep ──")
    test_freqs = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000,
                  12000, 15000, 20000, 30000, 50000]

    sweep_file = out_dir / "single_tone_sweep.csv"
    with open(sweep_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dds", "freq_cmd", "vpp", "vrms", "freq_meas"])

        for dds, set_fn, ch in [("A", teensy.set_freq_a, 1), ("B", teensy.set_freq_b, 2)]:
            # Silence the other
            if dds == "A":
                teensy.set_freq_b(0)
            else:
                teensy.set_freq_a(0)
            time.sleep(0.3)

            for freq in test_freqs:
                set_fn(freq)
                time.sleep(0.3)
                scope.set_timebase_for_freq(freq, freq)
                scope.capture(0.5)
                m = scope.measure(ch)
                fm = scope.measure_freq(ch)
                w.writerow([dds, freq, m["vpp"], m["vrms"], fm])
                print(f"  DDS {dds} {freq:>6} Hz: Vpp={m['vpp']:.4f}V  Freq={fm:.1f}Hz")
            f.flush()

    print(f"  Saved: {sweep_file}")

    # ── Crosstalk ──
    print("\n── Crosstalk ──")
    xtalk_file = out_dir / "crosstalk.csv"
    with open(xtalk_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["active_dds", "freq", "active_vpp", "inactive_vpp", "isolation_db"])

        for freq in [3000, 5000, 8000]:
            # A on, B off
            teensy.set_freq_a(freq)
            teensy.set_freq_b(0)
            time.sleep(0.5)
            scope.set_timebase_for_freq(freq, freq)
            scope.capture(0.5)
            ma = scope.measure(1)
            mb = scope.measure(2)
            iso = 20 * math.log10(mb["vpp"] / ma["vpp"]) if mb["vpp"] > 0 and ma["vpp"] > 0 else -99
            w.writerow(["A", freq, ma["vpp"], mb["vpp"], round(iso, 1)])
            print(f"  A→B {freq}Hz: active={ma['vpp']:.3f}V, leak={mb['vpp']:.4f}V, iso={iso:.1f}dB")

            # B on, A off
            teensy.set_freq_a(0)
            teensy.set_freq_b(freq)
            time.sleep(0.5)
            scope.capture(0.5)
            ma = scope.measure(1)
            mb = scope.measure(2)
            iso = 20 * math.log10(ma["vpp"] / mb["vpp"]) if ma["vpp"] > 0 and mb["vpp"] > 0 else -99
            w.writerow(["B", freq, mb["vpp"], ma["vpp"], round(iso, 1)])
            print(f"  B→A {freq}Hz: active={mb['vpp']:.3f}V, leak={ma['vpp']:.4f}V, iso={iso:.1f}dB")

    print(f"  Saved: {xtalk_file}")

    # ── Amplitude matching (both on, same freq) ──
    print("\n── Amplitude Matching ──")
    amp_file = out_dir / "amplitude_matching.csv"
    with open(amp_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["freq", "vpp_a", "vpp_b", "mismatch_pct"])
        for freq in [2000, 3000, 5000, 7000, 10000]:
            teensy.set_freq_a(freq)
            teensy.set_freq_b(freq)
            teensy.set_phase_b(0)
            time.sleep(0.5)
            scope.set_timebase_for_freq(freq, freq)
            scope.capture(0.5)
            ma = scope.measure(1)
            mb = scope.measure(2)
            avg = (ma["vpp"] + mb["vpp"]) / 2 if (ma["vpp"] + mb["vpp"]) > 0 else 1
            mis = abs(ma["vpp"] - mb["vpp"]) / avg * 100
            w.writerow([freq, ma["vpp"], mb["vpp"], round(mis, 2)])
            print(f"  {freq}Hz: A={ma['vpp']:.3f}V  B={mb['vpp']:.3f}V  Δ={mis:.1f}%")

    print(f"  Saved: {amp_file}")

    # ── Phase stability (2 min at 5kHz) ──
    print("\n── Phase Stability (2 min) ──")
    teensy.set_freq_a(5000)
    teensy.set_freq_b(5000)
    teensy.set_phase_b(0)
    time.sleep(0.5)
    scope.set_timebase_for_freq(5000, 5000)

    phase_file = out_dir / "phase_stability.csv"
    with open(phase_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "vpp_ch1", "vpp_ch2", "vpp_ch3"])
        t0 = time.time()
        for i in range(12):  # every 10s for 2 min
            scope.capture(0.5)
            m1 = scope.measure(1)
            m2 = scope.measure(2)
            m3 = scope.measure(3)
            elapsed = time.time() - t0
            w.writerow([round(elapsed, 1), m1["vpp"], m2["vpp"], m3["vpp"]])
            print(f"  {elapsed:.0f}s: CH1={m1['vpp']:.3f}V CH2={m2['vpp']:.3f}V CH3={m3['vpp']:.3f}V")
            if i < 11:
                time.sleep(10)

    print(f"  Saved: {phase_file}")

    # Screenshot
    scope.screenshot(str(out_dir / "characterisation_screenshot.png"))
    teensy.off()
    print("\n✅ Characterisation complete.")


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: Full waveform experiment
# ═══════════════════════════════════════════════════════════════════════════

def run_waveform_experiment(scope, teensy, out_dir, n_blocks=5, screenshot_every=50):
    """Full experiment with waveform capture + RSP + all metrics."""
    pairs = ALL_PAIRS
    phases = PHASE_OFFSETS_DEG
    total = len(pairs) * n_blocks * len(phases)

    wf_dir = out_dir / "waveforms"
    wf_dir.mkdir(exist_ok=True)
    ss_dir = out_dir / "screenshots"
    ss_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  PHASE 2: WAVEFORM EXPERIMENT")
    print(f"  {len(pairs)} pairs × {n_blocks} blocks × {len(phases)} phases = {total} trials")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    scope.setup(v_scale=0.2)

    # Do one warmup capture to prime the scope measurements
    teensy.set_freq_a(5000)
    teensy.set_freq_b(5000)
    time.sleep(0.3)
    scope.set_timebase_for_freq(5000, 5000)
    scope.capture(0.5)
    scope.measure(1)
    scope.measure(2)
    scope.measure(3)
    print("  Warmup capture done.")

    csv_path = out_dir / "results.csv"
    fields = [
        "trial", "block", "pair_id", "stratum", "ratio", "f1", "f2",
        "phase_offset", "timebase_s",
        # Scope measurements
        "vpp_ch1", "vrms_ch1", "vpp_ch2", "vrms_ch2", "vpp_ch3", "vrms_ch3",
        # RSP metrics (from waveform)
        "rsp_db", "crest_factor", "spectral_flatness", "envelope_regularity",
        "xcorr_peak", "phase_coherence",
        # Waveform info
        "wf_points", "sample_rate",
        "timestamp",
    ]
    csv_file = open(csv_path, "w", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=fields)
    writer.writeheader()

    trial = 0
    t0 = time.time()
    nan_count = 0
    rsp_by_stratum = {s: [] for s in ["PP", "CC", "PC", "NC", "IR"]}

    try:
        for block in range(1, n_blocks + 1):
            block_pairs = list(pairs)
            random.shuffle(block_pairs)
            print(f"\n── Block {block}/{n_blocks} ──")

            for pair in block_pairs:
                for phase_deg in phases:
                    trial += 1

                    # Set frequencies + phase
                    teensy.set_pair(pair.f1, pair.f2, phase_deg)
                    time.sleep(0.4)

                    # Set timebase optimised for this pair
                    tb = scope.set_timebase_for_freq(min(pair.f1, pair.f2),
                                                      max(pair.f1, pair.f2))
                    time.sleep(0.05)

                    # Capture
                    scope.capture(0.5)

                    # Scope measurements
                    m1 = scope.measure(1)
                    m2 = scope.measure(2)
                    m3 = scope.measure(3)

                    # Download waveforms
                    wf1, sr1 = scope.get_waveform(1)
                    wf2, sr2 = scope.get_waveform(2)
                    wf3, sr3 = scope.get_waveform(3)
                    sr = sr3 if sr3 > 0 else sr1

                    # Compute metrics
                    if len(wf3) > 10 and sr > 0:
                        if len(wf1) > 10 and len(wf2) > 10:
                            metrics = compute_rsp_two_channel(
                                wf1, wf2, wf3, sr, pair.f1, pair.f2)
                        else:
                            metrics = compute_metrics(wf3, sr, pair.f1, pair.f2)
                    else:
                        metrics = {
                            "rsp_db": float("nan"), "crest_factor": 0,
                            "spectral_flatness": 0, "envelope_regularity": 0,
                            "xcorr_peak": 0, "phase_coherence": 0,
                        }

                    # Save waveform
                    wf_file = wf_dir / f"t{trial:05d}_{pair.pair_id}_p{int(phase_deg)}.npz"
                    np.savez_compressed(
                        str(wf_file),
                        ch1=wf1, ch2=wf2, ch3=wf3,
                        sample_rate=sr, f1=pair.f1, f2=pair.f2,
                        phase_deg=phase_deg,
                    )

                    # Screenshot
                    if trial % screenshot_every == 0:
                        scope.screenshot(str(ss_dir / f"t{trial:05d}.png"))

                    # Track NaN
                    if math.isnan(m3.get("vpp", float("nan"))):
                        nan_count += 1

                    # Track RSP
                    rsp = metrics["rsp_db"]
                    if not math.isnan(rsp):
                        rsp_by_stratum[pair.stratum].append(rsp)

                    # CSV row
                    row = {
                        "trial": trial, "block": block,
                        "pair_id": pair.pair_id, "stratum": pair.stratum,
                        "ratio": pair.ratio_label,
                        "f1": pair.f1, "f2": pair.f2,
                        "phase_offset": phase_deg,
                        "timebase_s": tb,
                        "vpp_ch1": m1["vpp"], "vrms_ch1": m1["vrms"],
                        "vpp_ch2": m2["vpp"], "vrms_ch2": m2["vrms"],
                        "vpp_ch3": m3["vpp"], "vrms_ch3": m3["vrms"],
                        "rsp_db": round(rsp, 4) if not math.isnan(rsp) else "",
                        "crest_factor": round(metrics["crest_factor"], 4),
                        "spectral_flatness": round(metrics["spectral_flatness"], 6),
                        "envelope_regularity": round(metrics["envelope_regularity"], 4),
                        "xcorr_peak": round(metrics["xcorr_peak"], 4),
                        "phase_coherence": round(metrics["phase_coherence"], 4),
                        "wf_points": len(wf3),
                        "sample_rate": sr,
                        "timestamp": datetime.now().isoformat(),
                    }
                    writer.writerow(row)
                    csv_file.flush()

                    # Progress
                    if trial % 20 == 0 or trial == 1:
                        elapsed = time.time() - t0
                        rate = trial / elapsed if elapsed > 0 else 0
                        eta = (total - trial) / rate / 60 if rate > 0 else 0
                        rsp_str = f"{rsp:.2f}dB" if not math.isnan(rsp) else "N/A"
                        print(f"  [{trial}/{total}] {pair.pair_id} {pair.ratio_label} "
                              f"p={phase_deg}° | RSP={rsp_str} | "
                              f"CH3={m3['vpp']:.3f}V | NaN:{nan_count} | "
                              f"{elapsed:.0f}s, ~{eta:.0f}min left")

            # Block summary
            elapsed = time.time() - t0
            print(f"\n  Block {block} summary ({elapsed:.0f}s elapsed):")
            for s in ["PP", "CC", "PC", "NC", "IR"]:
                vals = rsp_by_stratum[s]
                if vals:
                    a = np.array(vals)
                    print(f"    {s}: n={len(a)}, mean RSP={a.mean():.3f}dB, "
                          f"sd={a.std():.3f}")

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted!")
    finally:
        csv_file.close()
        teensy.off()

    elapsed = time.time() - t0
    meta = {
        "timestamp": out_dir.name,
        "n_blocks": n_blocks, "n_pairs": len(pairs), "n_phases": len(phases),
        "total_trials": trial, "nan_count": nan_count,
        "elapsed_s": round(elapsed, 1),
        "mode": "full_waveform",
    }
    with open(out_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Phase 2 complete! {trial} trials, {nan_count} NaN, {elapsed:.0f}s")
    print(f"   Data: {csv_path}")
    print(f"   Waveforms: {wf_dir} ({trial} .npz files)")
    return csv_path


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", type=int, default=5)
    parser.add_argument("--skip-char", action="store_true", help="Skip characterisation")
    parser.add_argument("--screenshot-every", type=int, default=50)
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(__file__).parent / "results" / "runs" / ts
    base_dir.mkdir(parents=True, exist_ok=True)
    char_dir = base_dir / "characterisation"
    char_dir.mkdir(exist_ok=True)

    print(f"\n{'#'*60}")
    print(f"  ARBITER FULL DATA COLLECTION — {ts}")
    print(f"  Output: {base_dir}")
    print(f"{'#'*60}\n")

    print("Connecting...")
    scope = Scope()
    teensy = Teensy()

    try:
        # Phase 1
        if not args.skip_char:
            scope.setup(v_scale=0.5)  # wider scale for characterisation
            run_characterisation(scope, teensy, char_dir)
        else:
            print("Skipping characterisation.")

        # Phase 2
        run_waveform_experiment(scope, teensy, base_dir,
                                n_blocks=args.blocks,
                                screenshot_every=args.screenshot_every)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        teensy.off()
    finally:
        scope.close()
        teensy.close()

    print(f"\n{'#'*60}")
    print(f"  ALL DONE — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Data: {base_dir}")
    print(f"{'#'*60}")


if __name__ == "__main__":
    main()
