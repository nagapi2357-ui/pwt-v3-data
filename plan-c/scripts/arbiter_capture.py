#!/usr/bin/env python3
"""
arbiter_capture.py — Main automation script for the Arbiter experiment.

Interfaces with:
  - Rigol DS1054Z oscilloscope via SCPI over raw TCP (LAN)
  - Teensy 4.1 via USB serial (115200 baud)

Usage:
  python arbiter_capture.py characterise   # Signal chain validation
  python arbiter_capture.py run            # Full pre-registered experiment
  python arbiter_capture.py analyse [dir]  # Post-hoc analysis of saved data
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import random
import re
import socket
import struct
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# Local imports
from rsp import compute_rsp, compute_metrics, compute_rsp_two_channel
from test_matrix import (
    ALL_PAIRS, PAIRS_BY_ID, PAIRS_BY_STRATUM, PAIRS_BY_CLASS,
    PHASE_OFFSETS_DEG, N_BLOCKS, LONG_CAPTURE_MS, SCREENSHOT_EVERY_N,
    TestPair,
)

# ═══════════════════════════════════════════════════════════════════════════
# SCPI interface to Rigol DS1054Z
# ═══════════════════════════════════════════════════════════════════════════

class RigolDS1054Z:
    """Raw-socket SCPI interface to Rigol DS1054Z oscilloscope."""

    def __init__(self, ip: str = "169.254.201.110", port: int = 5555, timeout: float = 5.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    def connect(self) -> None:
        """Open TCP connection to scope."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.ip, self.port))
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            raise ConnectionError(f"Cannot connect to scope at {self.ip}:{self.port}: {e}") from e
        # Verify identity
        idn = self.query("*IDN?")
        if "RIGOL" not in idn.upper():
            raise ConnectionError(f"Unexpected instrument ID: {idn}")
        print(f"  Scope connected: {idn.strip()}")

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def write(self, cmd: str) -> None:
        """Send SCPI command (no response expected)."""
        assert self._sock is not None, "Not connected"
        self._sock.sendall((cmd + "\n").encode())

    def _recv_all(self, bufsize: int = 65536) -> bytes:
        """Receive until no more data (short timeout on trailing read)."""
        assert self._sock is not None
        chunks: list[bytes] = []
        self._sock.settimeout(self.timeout)
        while True:
            try:
                data = self._sock.recv(bufsize)
                if not data:
                    break
                chunks.append(data)
                # After first chunk, use shorter timeout to detect end
                self._sock.settimeout(0.3)
            except socket.timeout:
                break
        self._sock.settimeout(self.timeout)
        return b"".join(chunks)

    def query(self, cmd: str) -> str:
        """Send query command, return text response."""
        self.write(cmd)
        return self._recv_all().decode(errors="replace").strip()

    def query_binary(self, cmd: str) -> bytes:
        """Send query, return binary response (handles TMC header)."""
        self.write(cmd)
        raw = self._recv_binary()
        return raw

    def _recv_binary(self) -> bytes:
        """Receive binary data block with IEEE 488.2 definite-length header (#NdddD...)."""
        assert self._sock is not None
        self._sock.settimeout(self.timeout)
        # Read until we get the '#' header
        header = b""
        while len(header) < 2:
            header += self._sock.recv(2 - len(header))

        # Find '#' marker
        idx = header.find(b"#")
        if idx < 0:
            # No binary header — just read all
            rest = self._recv_all()
            return header + rest

        # After '#': one digit N, then N digits giving byte count
        while len(header) < idx + 2:
            header += self._sock.recv(1)
        n_digits = int(chr(header[idx + 1]))
        if n_digits == 0:
            # Indefinite length — read until newline
            return self._recv_all()

        # Read N digits
        digits = b""
        while len(digits) < n_digits:
            digits += self._sock.recv(n_digits - len(digits))
        data_len = int(digits)

        # Read exactly data_len bytes
        data = bytearray()
        while len(data) < data_len:
            chunk = self._sock.recv(min(65536, data_len - len(data)))
            if not chunk:
                break
            data.extend(chunk)

        # Read trailing newline
        try:
            self._sock.settimeout(0.2)
            self._sock.recv(2)
        except socket.timeout:
            pass
        self._sock.settimeout(self.timeout)
        return bytes(data)

    # ── High-level methods ────────────────────────────────────────────────

    def setup_channels(self) -> None:
        """Configure CH1-4 scales, coupling, and trigger on CH4 rising edge."""
        cmds = [
            # Channel enables
            ":CHAN1:DISP ON", ":CHAN2:DISP ON", ":CHAN3:DISP ON",
            # DC coupling, 1x probe
            ":CHAN1:COUP DC", ":CHAN1:PROB 1",
            ":CHAN2:COUP DC", ":CHAN2:PROB 1",
            ":CHAN3:COUP DC", ":CHAN3:PROB 1",
            # Vertical scales
            ":CHAN1:SCAL 0.2",   # 200 mV/div for DDS A (~0.66 Vpp)
            ":CHAN2:SCAL 0.2",   # 200 mV/div for DDS B (~0.22 Vpp)
            ":CHAN3:SCAL 0.2",   # 200 mV/div for sum
            # Center signals
            ":CHAN1:OFFS 0", ":CHAN2:OFFS 0", ":CHAN3:OFFS 0",
            # Auto trigger (free-run capture, no external trigger needed)
            ":TRIG:MODE EDGE",
            ":TRIG:EDGE:SOUR CHAN1",
            ":TRIG:EDGE:SLOP POS",
            ":TRIG:EDGE:LEV 0",
            # Timebase
            ":TIM:MAIN:SCAL 0.01",  # 10 ms/div → 120 ms total
            # Memory depth (moderate — balances resolution vs download speed)
            ":ACQ:MDEP 120000",
        ]
        for cmd in cmds:
            self.write(cmd)
            time.sleep(0.05)
        time.sleep(0.5)
        print("  Scope channels configured.")

    def set_timebase(self, capture_ms: int) -> None:
        """Set timebase to fit capture_ms in ~10 divisions."""
        scale_s = (capture_ms / 1000.0) / 10.0
        # Snap to nearest valid Rigol timebase
        valid = [0.000001, 0.000002, 0.000005,
                 0.00001, 0.00002, 0.00005,
                 0.0001, 0.0002, 0.0005,
                 0.001, 0.002, 0.005,
                 0.01, 0.02, 0.05,
                 0.1, 0.2, 0.5, 1.0]
        best = min(valid, key=lambda v: abs(v - scale_s) if v >= scale_s * 0.8 else float("inf"))
        self.write(f":TIM:MAIN:SCAL {best}")
        time.sleep(0.1)

    def single_capture(self, timeout_s: float = 30.0) -> bool:
        """Arm single trigger, wait for acquisition to complete. Returns True if captured."""
        self.write(":SING")
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            status = self.query(":TRIG:STAT?")
            if "STOP" in status.upper():
                return True
            time.sleep(0.1)
        print("  ⚠ Trigger timeout!")
        return False

    def get_waveform(self, channel: int) -> tuple[np.ndarray, float]:
        """Download waveform data from channel (1-4).

        Returns (samples_array, sample_rate_hz).
        """
        ch = f"CHAN{channel}"
        self.write(f":WAV:SOUR {ch}")
        self.write(":WAV:MODE NORM")
        self.write(":WAV:FORM BYTE")
        time.sleep(0.1)

        # Get preamble for reconstruction
        pre_str = self.query(":WAV:PRE?")
        pre = pre_str.split(",")
        # Preamble: format, type, points, count, xincrement, xorigin, xreference,
        #           yincrement, yorigin, yreference
        if len(pre) < 10:
            raise ValueError(f"Bad preamble: {pre_str}")

        points = int(pre[2])
        x_inc = float(pre[4])
        y_inc = float(pre[7])
        y_orig = float(pre[8])
        y_ref = float(pre[9])
        sample_rate = 1.0 / x_inc if x_inc > 0 else 1e6

        # NORM mode: download screen data (up to 1200 pts)
        self.write(":WAV:STAR 1")
        self.write(f":WAV:STOP {min(points, 1200)}")
        time.sleep(0.05)
        raw = self.query_binary(":WAV:DATA?")

        if len(raw) == 0:
            return np.array([]), sample_rate

        # Convert to voltage
        raw_arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        voltage = (raw_arr - y_ref - y_orig) * y_inc
        return voltage, sample_rate

    def get_measurements(self, channel: int) -> dict[str, float]:
        """Read Vpp, Vrms, Freq via :MEAS commands."""
        ch = f"CHAN{channel}"
        results: dict[str, float] = {}
        for item in ["VPP", "VRMS", "FREQ"]:
            self.write(f":MEAS:ITEM {item},{ch}")
            time.sleep(0.15)
            val_str = self.query(f":MEAS:ITEM? {item},{ch}")
            try:
                results[item.lower()] = float(val_str)
            except ValueError:
                results[item.lower()] = float("nan")
        return results

    def screenshot(self, filename: str) -> None:
        """Download scope display as PNG and save to file."""
        try:
            data = self.query_binary(":DISP:DATA? ON,OFF,PNG")
        except Exception:
            # Fallback to BMP
            data = self.query_binary(":DISP:DATA? ON,OFF,BMP")
            if filename.endswith(".png"):
                filename = filename[:-4] + ".bmp"
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "wb") as f:
            f.write(data)


# ═══════════════════════════════════════════════════════════════════════════
# Serial interface to Teensy
# ═══════════════════════════════════════════════════════════════════════════

class TeensyArbiter:
    """USB serial interface to the Teensy 4.1 Arbiter firmware."""

    def __init__(self, port: str | None = None, baudrate: int = 115200, timeout: float = 2.0):
        import serial  # pyserial — one dependency we can't avoid for serial
        if port is None:
            port = self._find_teensy()
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(2)  # Teensy resets on serial open
        self.ser.reset_input_buffer()
        print(f"  Teensy connected on {port}")

    @staticmethod
    def _find_teensy() -> str:
        """Auto-detect Teensy serial port."""
        patterns = [
            "/dev/tty.usbmodem*",
            "/dev/ttyACM*",
            "/dev/ttyUSB*",
        ]
        for pat in patterns:
            matches = glob.glob(pat)
            if matches:
                return matches[0]
        raise FileNotFoundError(
            "No Teensy serial port found. Check USB connection. "
            "Tried: " + ", ".join(patterns)
        )

    def send(self, cmd: str) -> str:
        """Send command, return response line."""
        self.ser.reset_input_buffer()
        self.ser.write((cmd.strip() + "\n").encode())
        time.sleep(0.05)
        lines: list[str] = []
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

    def set_freq_a(self, freq_hz: float) -> str:
        return self.send(f"FA {freq_hz:.1f}")

    def set_freq_b(self, freq_hz: float) -> str:
        return self.send(f"FB {freq_hz:.1f}")

    def set_phase_b(self, phase_deg: float) -> str:
        return self.send(f"PB {phase_deg:.1f}")

    def set_pair(self, f1: float, f2: float, phase_deg: float) -> str:
        """Set both frequencies and phase in sequence."""
        self.set_freq_a(f1)
        self.set_freq_b(f2)
        return self.set_phase_b(phase_deg)

    def trigger(self) -> str:
        """Tell Teensy to fire the trigger pin."""
        return self.send("TRIGGER")

    def off(self) -> str:
        return self.send("OFF BOTH")

    def status(self) -> dict[str, str]:
        resp = self.send("STATUS")
        result: dict[str, str] = {}
        for line in resp.split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
        return result

    def close(self) -> None:
        self.ser.close()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def progress(current: int, total: int, prefix: str = "", width: int = 40) -> None:
    """Print a simple progress bar."""
    frac = current / max(total, 1)
    filled = int(width * frac)
    bar = "█" * filled + "░" * (width - filled)
    pct = frac * 100
    print(f"\r  {prefix} |{bar}| {pct:5.1f}% ({current}/{total})", end="", flush=True)
    if current >= total:
        print()


# ═══════════════════════════════════════════════════════════════════════════
# Mode 1: Characterise
# ═══════════════════════════════════════════════════════════════════════════

def run_characterise(scope: RigolDS1054Z, teensy: TeensyArbiter) -> None:
    """Run the characterisation protocol from characterisation-protocol.md."""
    ts = timestamp()
    out_dir = RESULTS_DIR / "characterisation" / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"  CHARACTERISATION — {ts}")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    # ── Step 2: Single-tone sweep ─────────────────────────────────────
    print("── Step 2: Single-Tone Sweep ──")
    test_freqs = [2614, 3000, 3536, 3873, 4083, 4472, 5000,
                  5916, 6124, 6455, 7072, 7500, 7906, 8333, 9574]

    sweep_file = out_dir / "single_tone_sweep.csv"
    with open(sweep_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dds", "freq_cmd", "ch", "vpp", "vrms", "freq_meas"])

        for dds_label, set_fn, ch in [("A", teensy.set_freq_a, 1), ("B", teensy.set_freq_b, 2)]:
            print(f"\n  DDS {dds_label} (CH{ch}):")
            # Turn other DDS off
            if dds_label == "A":
                teensy.set_freq_b(0)
            else:
                teensy.set_freq_a(0)

            for i, freq in enumerate(test_freqs):
                set_fn(freq)
                time.sleep(0.5)
                scope.set_timebase(max(100, int(5000 / freq)))
                scope.write(":RUN")
                time.sleep(0.3)
                scope.write(":STOP")
                time.sleep(0.2)
                meas = scope.get_measurements(ch)
                w.writerow([dds_label, freq, ch, meas["vpp"], meas["vrms"], meas["freq"]])
                progress(i + 1, len(test_freqs), f"DDS {dds_label}")

    print(f"  Saved: {sweep_file}")

    # ── Step 3: Filter rolloff ────────────────────────────────────────
    print("\n── Step 3: Filter Rolloff ──")
    rolloff_freqs = [1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000]
    rolloff_file = out_dir / "filter_rolloff.csv"

    teensy.set_freq_b(0)
    with open(rolloff_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["freq_hz", "vpp", "attenuation_db"])
        v_ref: float | None = None
        for i, freq in enumerate(rolloff_freqs):
            teensy.set_freq_a(freq)
            time.sleep(0.5)
            scope.write(":RUN")
            time.sleep(0.3)
            scope.write(":STOP")
            time.sleep(0.2)
            meas = scope.get_measurements(1)
            vpp = meas["vpp"]
            if v_ref is None:
                v_ref = vpp
            atten = 20 * math.log10(vpp / v_ref) if vpp > 0 and v_ref > 0 else float("-inf")
            w.writerow([freq, vpp, round(atten, 2)])
            progress(i + 1, len(rolloff_freqs), "Rolloff")

    print(f"  Saved: {rolloff_file}")

    # ── Step 4: Crosstalk ─────────────────────────────────────────────
    print("\n── Step 4: Crosstalk ──")
    xtalk_file = out_dir / "crosstalk.csv"
    with open(xtalk_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["active_dds", "active_ch_vpp", "inactive_ch_vpp", "isolation_db"])

        # A on, B off
        teensy.set_freq_a(5000)
        teensy.set_freq_b(0)
        time.sleep(0.5)
        scope.write(":RUN"); time.sleep(0.3); scope.write(":STOP"); time.sleep(0.2)
        m1 = scope.get_measurements(1)
        m2 = scope.get_measurements(2)
        iso = 20 * math.log10(m2["vpp"] / m1["vpp"]) if m2["vpp"] > 0 and m1["vpp"] > 0 else -99
        w.writerow(["A", m1["vpp"], m2["vpp"], round(iso, 1)])
        print(f"  A→B isolation: {iso:.1f} dB")

        # B on, A off
        teensy.set_freq_a(0)
        teensy.set_freq_b(5000)
        time.sleep(0.5)
        scope.write(":RUN"); time.sleep(0.3); scope.write(":STOP"); time.sleep(0.2)
        m1 = scope.get_measurements(1)
        m2 = scope.get_measurements(2)
        iso = 20 * math.log10(m1["vpp"] / m2["vpp"]) if m1["vpp"] > 0 and m2["vpp"] > 0 else -99
        w.writerow(["B", m2["vpp"], m1["vpp"], round(iso, 1)])
        print(f"  B→A isolation: {iso:.1f} dB")

    print(f"  Saved: {xtalk_file}")

    # ── Step 5: Phase stability ───────────────────────────────────────
    print("\n── Step 5: Phase Stability (5 min) ──")
    teensy.set_freq_a(5000)
    teensy.set_freq_b(5000)
    teensy.set_phase_b(0)
    time.sleep(1)

    phase_file = out_dir / "phase_stability.csv"
    with open(phase_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_s", "phase_deg"])
        t0 = time.time()
        n_samples = 30  # every 10 seconds for 5 minutes
        for i in range(n_samples):
            scope.write(":RUN"); time.sleep(0.3); scope.write(":STOP"); time.sleep(0.2)
            # Read phase measurement
            scope.write(":MEAS:ITEM RPH,CHAN1,CHAN2")
            time.sleep(0.15)
            phase = scope.query(":MEAS:ITEM? RPH,CHAN1,CHAN2")
            elapsed = time.time() - t0
            try:
                phase_val = float(phase)
            except ValueError:
                phase_val = float("nan")
            w.writerow([round(elapsed, 1), phase_val])
            progress(i + 1, n_samples, "Phase")
            if i < n_samples - 1:
                time.sleep(10)

    print(f"  Saved: {phase_file}")

    # ── Step 6: Amplitude matching ────────────────────────────────────
    print("\n── Step 6: Amplitude Matching ──")
    amp_file = out_dir / "amplitude_matching.csv"
    match_freqs = [3000, 5000, 8000]
    with open(amp_file, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["freq_hz", "vpp_a", "vpp_b", "mismatch_pct"])
        for freq in match_freqs:
            teensy.set_freq_a(freq)
            teensy.set_freq_b(freq)
            time.sleep(0.5)
            scope.write(":RUN"); time.sleep(0.3); scope.write(":STOP"); time.sleep(0.2)
            ma = scope.get_measurements(1)
            mb = scope.get_measurements(2)
            mismatch = abs(ma["vpp"] - mb["vpp"]) / ((ma["vpp"] + mb["vpp"]) / 2) * 100 if (ma["vpp"] + mb["vpp"]) > 0 else 0
            w.writerow([freq, ma["vpp"], mb["vpp"], round(mismatch, 2)])
            print(f"  {freq} Hz: A={ma['vpp']:.3f}V  B={mb['vpp']:.3f}V  Δ={mismatch:.1f}%")

    print(f"  Saved: {amp_file}")

    # ── Screenshot ────────────────────────────────────────────────────
    scope.screenshot(str(out_dir / "final_screenshot.png"))

    teensy.off()
    print(f"\n✅ Characterisation complete. Results in {out_dir}")


# ═══════════════════════════════════════════════════════════════════════════
# Mode 2: Run experiment
# ═══════════════════════════════════════════════════════════════════════════

def run_experiment(scope: RigolDS1054Z, teensy: TeensyArbiter,
                   n_blocks: int = N_BLOCKS,
                   screenshot_every: int = SCREENSHOT_EVERY_N) -> None:
    """Run the full pre-registered experiment."""
    ts = timestamp()
    out_dir = RESULTS_DIR / "runs" / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    waveform_dir = out_dir / "waveforms"
    waveform_dir.mkdir(exist_ok=True)
    screenshot_dir = out_dir / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)

    # Exclude NC pairs from main experiment loop (they're sanity checks, still run them)
    pairs = ALL_PAIRS  # all 30

    total_trials = len(pairs) * n_blocks * len(PHASE_OFFSETS_DEG)
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT RUN — {ts}")
    print(f"  {len(pairs)} pairs × {n_blocks} blocks × {len(PHASE_OFFSETS_DEG)} phases = {total_trials} trials")
    print(f"  Estimated time: ~{total_trials * 4 / 60:.0f} minutes")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    # Setup scope
    scope.setup_channels()

    # CSV output
    csv_path = out_dir / "results.csv"
    fieldnames = [
        "trial", "block", "pair_id", "stratum", "ratio", "f1", "f2",
        "phase_offset", "capture_ms", "rsp_db", "crest_factor",
        "spectral_flatness", "envelope_regularity", "xcorr_peak",
        "phase_coherence", "vpp_ch1", "vpp_ch2", "vpp_ch3",
        "freq_ch3", "timestamp",
    ]
    csv_file = open(csv_path, "w", newline="")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    # Running statistics
    rsp_by_stratum: dict[str, list[float]] = {s: [] for s in ["PP", "CC", "PC", "NC", "IR"]}
    trial_num = 0
    t_run_start = time.time()

    try:
        for block in range(1, n_blocks + 1):
            print(f"\n── Block {block}/{n_blocks} ──")
            # Shuffle pair order (randomised block design)
            block_pairs = list(pairs)
            random.shuffle(block_pairs)

            for pair_idx, pair in enumerate(block_pairs):
                for phase_deg in PHASE_OFFSETS_DEG:
                    trial_num += 1

                    # Set frequencies and phase
                    teensy.set_pair(pair.f1, pair.f2, phase_deg)
                    time.sleep(0.5)  # settle time

                    # Set timebase for this pair's capture duration
                    scope.set_timebase(pair.capture_ms)
                    time.sleep(0.1)

                    # Capture: free-run then stop (no trigger pin needed)
                    scope.write(":RUN")
                    time.sleep(0.5)
                    scope.write(":STOP")
                    time.sleep(0.3)
                    captured = True

                    # Get measurements from all signal channels
                    meas_ch1 = scope.get_measurements(1)
                    meas_ch2 = scope.get_measurements(2)
                    meas_ch3 = scope.get_measurements(3)

                    # Download waveforms (CH1-3 only, skip trigger CH4)
                    waveforms: dict[int, tuple[np.ndarray, float]] = {}
                    for ch in [1, 2, 3]:
                        try:
                            waveforms[ch] = scope.get_waveform(ch)
                        except Exception as e:
                            print(f"\n  ⚠ Waveform CH{ch} failed: {e}")
                            waveforms[ch] = (np.array([]), 0.0)
                    waveforms[4] = (np.array([]), 0.0)  # placeholder

                    # Compute RSP
                    ch3_data, sr = waveforms[3]
                    if len(ch3_data) > 0 and sr > 0:
                        if len(waveforms[1][0]) > 0 and len(waveforms[2][0]) > 0:
                            metrics = compute_rsp_two_channel(
                                waveforms[1][0], waveforms[2][0], ch3_data,
                                sr, pair.f1, pair.f2,
                            )
                        else:
                            metrics = compute_metrics(ch3_data, sr, pair.f1, pair.f2)
                    else:
                        metrics = {
                            "rsp_db": float("nan"), "crest_factor": 0,
                            "spectral_flatness": 0, "envelope_regularity": 0,
                            "xcorr_peak": 0, "phase_coherence": 0,
                        }

                    # Save waveform (every trial — raw data is sacred)
                    wf_file = waveform_dir / f"trial_{trial_num:05d}_{pair.pair_id}_p{int(phase_deg)}.npz"
                    np.savez_compressed(
                        str(wf_file),
                        ch1=waveforms[1][0], ch2=waveforms[2][0],
                        ch3=waveforms[3][0], ch4=waveforms[4][0],
                        sample_rate=sr, f1=pair.f1, f2=pair.f2,
                        phase_deg=phase_deg,
                    )

                    # Screenshot periodically
                    if trial_num % screenshot_every == 0:
                        scope.screenshot(str(screenshot_dir / f"trial_{trial_num:05d}.png"))

                    # Write CSV row
                    row = {
                        "trial": trial_num,
                        "block": block,
                        "pair_id": pair.pair_id,
                        "stratum": pair.stratum,
                        "ratio": pair.ratio_label,
                        "f1": pair.f1,
                        "f2": pair.f2,
                        "phase_offset": phase_deg,
                        "capture_ms": pair.capture_ms,
                        "rsp_db": round(metrics["rsp_db"], 4) if not math.isnan(metrics["rsp_db"]) else "",
                        "crest_factor": round(metrics["crest_factor"], 4),
                        "spectral_flatness": round(metrics["spectral_flatness"], 6),
                        "envelope_regularity": round(metrics["envelope_regularity"], 4),
                        "xcorr_peak": round(metrics["xcorr_peak"], 4),
                        "phase_coherence": round(metrics["phase_coherence"], 4),
                        "vpp_ch1": meas_ch1.get("vpp", ""),
                        "vpp_ch2": meas_ch2.get("vpp", ""),
                        "vpp_ch3": meas_ch3.get("vpp", ""),
                        "freq_ch3": meas_ch3.get("freq", ""),
                        "timestamp": datetime.now().isoformat(),
                    }
                    writer.writerow(row)
                    csv_file.flush()

                    # Track RSP
                    if not math.isnan(metrics["rsp_db"]):
                        rsp_by_stratum[pair.stratum].append(metrics["rsp_db"])

                    # Progress: print every 10 trials for monitoring
                    if trial_num % 10 == 0 or trial_num == 1:
                        elapsed = time.time() - t_run_start
                        print(f"  Trial {trial_num}/{total_trials} | {pair.pair_id} {pair.ratio_label} "
                              f"p={phase_deg}° | RSP={metrics['rsp_db']:.2f}dB | "
                              f"Vpp={meas_ch3.get('vpp', '?')} | {elapsed:.0f}s elapsed")
                    progress(trial_num, total_trials, "Running")

            # Block summary
            print(f"\n  Block {block} summary:")
            for s in ["PP", "CC", "PC", "NC", "IR"]:
                vals = rsp_by_stratum[s]
                if vals:
                    print(f"    {s}: n={len(vals)}, mean RSP={np.mean(vals):.2f} dB, "
                          f"std={np.std(vals):.2f}")

    finally:
        csv_file.close()
        teensy.off()

    # Save run metadata
    meta = {
        "timestamp": ts,
        "n_blocks": n_blocks,
        "n_pairs": len(pairs),
        "n_phases": len(PHASE_OFFSETS_DEG),
        "total_trials": trial_num,
        "screenshot_every": screenshot_every,
    }
    with open(out_dir / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Experiment complete. {trial_num} trials saved to {out_dir}")


# ═══════════════════════════════════════════════════════════════════════════
# Mode 3: Analyse
# ═══════════════════════════════════════════════════════════════════════════

def run_analyse(data_dir: str | None = None) -> None:
    """Post-hoc analysis of saved experiment data."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats

    # Find data directory
    if data_dir:
        run_dir = Path(data_dir)
    else:
        runs_dir = RESULTS_DIR / "runs"
        if not runs_dir.exists():
            print("No runs found. Run the experiment first.")
            return
        # Use most recent
        subdirs = sorted(runs_dir.iterdir())
        if not subdirs:
            print("No runs found.")
            return
        run_dir = subdirs[-1]

    csv_path = run_dir / "results.csv"
    if not csv_path.exists():
        print(f"No results.csv in {run_dir}")
        return

    ts = timestamp()
    out_dir = RESULTS_DIR / "analysis" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  ANALYSIS — {ts}")
    print(f"  Data: {run_dir}")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    # Load data
    rows: list[dict] = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["rsp_db"] = float(row["rsp_db"]) if row["rsp_db"] else float("nan")
            except ValueError:
                row["rsp_db"] = float("nan")
            rows.append(row)

    print(f"  Loaded {len(rows)} trials")

    # Recompute RSP from saved waveforms if needed
    wf_dir = run_dir / "waveforms"
    n_recomputed = 0
    if wf_dir.exists():
        for row in rows:
            if math.isnan(row["rsp_db"]):
                trial = int(row["trial"])
                pair_id = row["pair_id"]
                phase = int(float(row["phase_offset"]))
                wf_file = wf_dir / f"trial_{trial:05d}_{pair_id}_p{phase}.npz"
                if wf_file.exists():
                    data = np.load(str(wf_file))
                    ch3 = data["ch3"]
                    sr = float(data["sample_rate"])
                    f1 = float(data["f1"])
                    f2 = float(data["f2"])
                    if len(ch3) > 0 and sr > 0:
                        row["rsp_db"] = compute_rsp(ch3, sr, f1, f2)
                        n_recomputed += 1
    if n_recomputed:
        print(f"  Recomputed RSP for {n_recomputed} trials from waveforms")

    # ── Group by stratum ──────────────────────────────────────────────
    by_stratum: dict[str, list[float]] = {}
    by_pair: dict[str, list[float]] = {}
    by_block: dict[int, list[float]] = {}

    for row in rows:
        rsp = row["rsp_db"]
        if math.isnan(rsp):
            continue
        s = row["stratum"]
        by_stratum.setdefault(s, []).append(rsp)
        by_pair.setdefault(row["pair_id"], []).append(rsp)
        by_block.setdefault(int(row["block"]), []).append(rsp)

    # ── Summary statistics ────────────────────────────────────────────
    report_lines: list[str] = []
    report_lines.append(f"# Arbiter Analysis Report — {ts}\n")
    report_lines.append(f"Data source: {run_dir}\n")
    report_lines.append(f"Total trials: {len(rows)}\n")
    report_lines.append("")
    report_lines.append("## Stratum Summary\n")
    report_lines.append("| Stratum | N | Mean RSP (dB) | SD | Median |")
    report_lines.append("|---------|---|---------------|-----|--------|")

    for s in ["PP", "CC", "PC", "NC", "IR"]:
        vals = by_stratum.get(s, [])
        if vals:
            arr = np.array(vals)
            report_lines.append(
                f"| {s} | {len(arr)} | {np.mean(arr):.3f} | {np.std(arr):.3f} | {np.median(arr):.3f} |"
            )
        else:
            report_lines.append(f"| {s} | 0 | — | — | — |")

    # ── Primary hypothesis test: Class B (PP vs CC) ───────────────────
    report_lines.append("\n## Primary Hypothesis Test: Class B (PP vs CC)\n")

    class_b_pp: list[float] = []
    class_b_cc: list[float] = []
    for row in rows:
        if math.isnan(row["rsp_db"]):
            continue
        pair = PAIRS_BY_ID.get(row["pair_id"])
        if pair and pair.comparison_class in ("B1", "B2", "B3"):
            if pair.stratum == "PP":
                class_b_pp.append(row["rsp_db"])
            elif pair.stratum == "CC":
                class_b_cc.append(row["rsp_db"])

    if len(class_b_pp) >= 2 and len(class_b_cc) >= 2:
        pp_arr = np.array(class_b_pp)
        cc_arr = np.array(class_b_cc)

        # Welch's t-test
        t_stat, p_value = stats.ttest_ind(pp_arr, cc_arr, equal_var=False)
        # Effect size (Cohen's d)
        pooled_std = math.sqrt((np.var(pp_arr) + np.var(cc_arr)) / 2)
        cohens_d = (np.mean(pp_arr) - np.mean(cc_arr)) / pooled_std if pooled_std > 0 else 0

        # 95% CI for difference of means
        diff = np.mean(pp_arr) - np.mean(cc_arr)
        se = math.sqrt(np.var(pp_arr) / len(pp_arr) + np.var(cc_arr) / len(cc_arr))
        ci_lo = diff - 1.96 * se
        ci_hi = diff + 1.96 * se

        report_lines.append(f"PP (Class B): n={len(pp_arr)}, mean={np.mean(pp_arr):.4f}, sd={np.std(pp_arr):.4f}")
        report_lines.append(f"CC (Class B): n={len(cc_arr)}, mean={np.mean(cc_arr):.4f}, sd={np.std(cc_arr):.4f}")
        report_lines.append(f"")
        report_lines.append(f"Welch's t-test: t={t_stat:.4f}, p={p_value:.6f}")
        report_lines.append(f"Cohen's d: {cohens_d:.4f}")
        report_lines.append(f"Mean difference (PP−CC): {diff:.4f} dB")
        report_lines.append(f"95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")
        report_lines.append(f"")

        if p_value < 0.005:
            report_lines.append("⚠️ **Statistically significant at α=0.005 (Bonferroni-corrected)**")
            report_lines.append("→ DEBUG SIGNAL CHAIN before interpreting as a real effect.")
        else:
            report_lines.append("✅ Not significant — consistent with null hypothesis (expected).")
    else:
        report_lines.append("Insufficient data for Class B test.")

    # ── NC consistency check ──────────────────────────────────────────
    report_lines.append("\n## NC Consistency Check\n")
    nc2_vals = by_pair.get("NC2", [])
    pp1_vals = by_pair.get("PP1", [])
    if nc2_vals and pp1_vals:
        t_nc, p_nc = stats.ttest_ind(nc2_vals, pp1_vals, equal_var=False)
        report_lines.append(f"NC2 (9:6→3:2) vs PP1 (3:2): t={t_nc:.3f}, p={p_nc:.4f}")
        if p_nc < 0.05:
            report_lines.append("⚠️ NC2 ≠ PP1 — possible measurement issue!")
        else:
            report_lines.append("✅ NC2 ≈ PP1 — measurement consistency confirmed.")

    # ── Block effects ─────────────────────────────────────────────────
    report_lines.append("\n## Block Effects\n")
    for b in sorted(by_block):
        vals = by_block[b]
        report_lines.append(f"Block {b}: n={len(vals)}, mean RSP={np.mean(vals):.3f} dB")

    # Write report
    report_path = out_dir / "report.md"
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"  Report: {report_path}")

    # ── Plots ─────────────────────────────────────────────────────────
    print("  Generating plots...")

    # 1. RSP by stratum (box plot)
    fig, ax = plt.subplots(figsize=(10, 6))
    strata_order = ["PP", "CC", "PC", "NC", "IR"]
    plot_data = [by_stratum.get(s, []) for s in strata_order]
    bp = ax.boxplot(plot_data, labels=strata_order, patch_artist=True)
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#95a5a6", "#f39c12"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.set_ylabel("RSP (dB)")
    ax.set_xlabel("Stratum")
    ax.set_title("Residual Spectral Power by Stratum")
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(out_dir / "rsp_by_stratum.png"), dpi=150)
    plt.close(fig)

    # 2. RSP by pair (strip plot)
    fig, ax = plt.subplots(figsize=(16, 6))
    pair_ids = [p.pair_id for p in ALL_PAIRS]
    pair_data = [by_pair.get(pid, []) for pid in pair_ids]
    positions = list(range(len(pair_ids)))
    for i, (pid, vals) in enumerate(zip(pair_ids, pair_data)):
        if vals:
            jitter = np.random.normal(0, 0.1, len(vals))
            pair = PAIRS_BY_ID[pid]
            color = colors[strata_order.index(pair.stratum)]
            ax.scatter([i + j for j in jitter], vals, c=color, alpha=0.5, s=10)
            ax.plot(i, np.mean(vals), "k_", markersize=15, markeredgewidth=2)
    ax.set_xticks(positions)
    ax.set_xticklabels(pair_ids, rotation=90, fontsize=7)
    ax.set_ylabel("RSP (dB)")
    ax.set_title("RSP by Pair (strip plot)")
    fig.tight_layout()
    fig.savefig(str(out_dir / "rsp_by_pair.png"), dpi=150)
    plt.close(fig)

    # 3. Block effects
    if len(by_block) > 1:
        fig, ax = plt.subplots(figsize=(8, 5))
        blocks = sorted(by_block)
        means = [np.mean(by_block[b]) for b in blocks]
        sds = [np.std(by_block[b]) for b in blocks]
        ax.errorbar(blocks, means, yerr=sds, fmt="o-", capsize=5)
        ax.set_xlabel("Block")
        ax.set_ylabel("Mean RSP (dB)")
        ax.set_title("RSP by Block (drift check)")
        fig.tight_layout()
        fig.savefig(str(out_dir / "block_effects.png"), dpi=150)
        plt.close(fig)

    print(f"\n✅ Analysis complete. Results in {out_dir}")

    # Print key result to console
    print("\n── Key Result ──")
    for line in report_lines:
        if "Welch" in line or "Cohen" in line or "significant" in line or "Not significant" in line:
            print(f"  {line}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Arbiter experiment automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  characterise   Run signal chain validation (Steps 2-6)
  run            Run full pre-registered experiment
  analyse [dir]  Post-hoc analysis of saved data
        """,
    )
    parser.add_argument("mode", choices=["characterise", "run", "analyse"],
                        help="Operation mode")
    parser.add_argument("data_dir", nargs="?", default=None,
                        help="Data directory (analyse mode only)")
    parser.add_argument("--blocks", type=int, default=N_BLOCKS,
                        help=f"Number of blocks (default: {N_BLOCKS})")
    parser.add_argument("--scope-ip", default="169.254.201.110",
                        help="Scope IP address")
    parser.add_argument("--scope-port", type=int, default=5555,
                        help="Scope SCPI port")
    parser.add_argument("--serial-port", default=None,
                        help="Teensy serial port (auto-detect if not specified)")
    parser.add_argument("--screenshot-every", type=int, default=SCREENSHOT_EVERY_N,
                        help=f"Screenshot interval (default: every {SCREENSHOT_EVERY_N} trials)")
    args = parser.parse_args()

    if args.mode == "analyse":
        run_analyse(args.data_dir)
        return

    # Connect to hardware
    print("Connecting to hardware...")
    scope = RigolDS1054Z(ip=args.scope_ip, port=args.scope_port)
    try:
        scope.connect()
    except ConnectionError as e:
        print(f"❌ Scope connection failed: {e}")
        sys.exit(1)

    try:
        teensy = TeensyArbiter(port=args.serial_port)
    except (FileNotFoundError, Exception) as e:
        print(f"❌ Teensy connection failed: {e}")
        scope.close()
        sys.exit(1)

    try:
        if args.mode == "characterise":
            scope.setup_channels()
            run_characterise(scope, teensy)
        elif args.mode == "run":
            run_experiment(scope, teensy, n_blocks=args.blocks,
                           screenshot_every=args.screenshot_every)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user.")
        teensy.off()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        teensy.off()
        raise
    finally:
        scope.close()
        teensy.close()


if __name__ == "__main__":
    main()
