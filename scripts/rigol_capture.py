#!/usr/bin/env python3
"""
Rigol DS1054Z Torsion Capture — READ-ONLY mode.
Captures CH1+CH2 waveform data WITHOUT changing any scope settings.
Only sends :TFOR + :STOP to freeze the buffer, then reads, then :RUN to resume.

Usage:
    python3 rigol_capture.py [label]
    
    label: optional name for the capture (default: 'capture')
    
Output saved to: Adrian Docs/Pics/Test Point Readings/20 May Results/
"""
import pyvisa
import numpy as np
import os, sys, time
from datetime import datetime

RIGOL_IP = '169.254.201.110'
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'Adrian Docs', 'Pics', 'Test Point Readings', '22 May Results - Board 3')

def capture(label='capture'):
    rm = pyvisa.ResourceManager('@py')
    scope = rm.open_resource(f'TCPIP::{RIGOL_IP}::5555::SOCKET')
    scope.timeout = 20000
    scope.chunk_size = 1024 * 1024
    scope.read_termination = '\n'
    scope.write_termination = '\n'

    idn = scope.query('*IDN?').strip()
    print(f"Connected: {idn}")
    
    # Set 5ms/div timebase for full FFT resolution (~17 Hz)
    scope.write(':TIM:MAIN:SCAL 0.005')
    time.sleep(0.5)
    
    # Read current settings
    tb = scope.query(':TIM:MAIN:SCAL?').strip()
    ch1_coup = scope.query(':CHAN1:COUP?').strip()
    ch2_coup = scope.query(':CHAN2:COUP?').strip()
    ch1_scale = scope.query(':CHAN1:SCAL?').strip()
    ch2_scale = scope.query(':CHAN2:SCAL?').strip()
    print(f"Timebase: {float(tb)*1000:.2f} ms/div")
    print(f"CH1: {ch1_coup} coupling, {float(ch1_scale)*1000:.0f} mV/div")
    print(f"CH2: {ch2_coup} coupling, {float(ch2_scale)*1000:.0f} mV/div")
    
    # Force trigger and stop to freeze buffer
    scope.write(':TFOR')
    time.sleep(0.5)
    scope.write(':STOP')
    time.sleep(1)
    
    timestamp = datetime.now().strftime('%H%M%S')
    results = {}
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'timebase_s': float(tb),
        'ch1_coupling': ch1_coup,
        'ch2_coupling': ch2_coup,
        'ch1_scale_v': float(ch1_scale),
        'ch2_scale_v': float(ch2_scale),
    }
    
    for ch in [1, 2]:
        name = f'CH{ch}'
        scope.write(f':WAV:SOUR CHAN{ch}')
        scope.write(':WAV:MODE NORM')
        scope.write(':WAV:FORM BYTE')
        scope.write(':WAV:STAR 1')
        scope.write(':WAV:STOP 1200')
        time.sleep(0.5)
        
        pre = scope.query(':WAV:PRE?').strip().split(',')
        points = int(pre[2])
        xinc = float(pre[4])
        xorig = float(pre[5])
        yinc = float(pre[7])
        yorig = int(pre[8])
        yref = int(pre[9])
        
        raw = scope.query_binary_values(':WAV:DATA?', datatype='B', container=np.array)
        
        voltage = (raw.astype(float) - yref - yorig) * yinc
        t = np.arange(len(voltage)) * xinc + xorig
        
        vpp = voltage.max() - voltage.min()
        print(f"{name}: {len(voltage)} pts, {(t[-1]-t[0])*1000:.2f}ms, "
              f"Vpp={vpp*1000:.1f}mV, range={voltage.min():.3f}–{voltage.max():.3f}V")
        
        results[f't{ch}'] = t
        results[f'v{ch}'] = voltage
        metadata[f'ch{ch}_xinc'] = xinc
        metadata[f'ch{ch}_sample_rate'] = 1.0 / xinc
        metadata[f'ch{ch}_points'] = len(voltage)
        metadata[f'ch{ch}_vpp'] = vpp
    
    # Resume scope
    scope.write(':RUN')
    scope.close()
    
    # Save
    fname = f'torsion_{label}_{timestamp}'
    csv_path = os.path.join(BASE_DIR, f'{fname}.csv')
    npz_path = os.path.join(BASE_DIR, f'{fname}.npz')
    
    t1, v1 = results['t1'], results['v1']
    t2, v2 = results['t2'], results['v2']
    ml = min(len(t1), len(t2))
    
    np.savetxt(csv_path, np.column_stack([t1[:ml], v1[:ml], v2[:ml]]),
               delimiter=',', header='time_s,torsion_a_v,torsion_b_v', comments='')
    np.savez(npz_path, t1=t1, v1=v1, t2=t2, v2=v2, **metadata)
    
    print(f"\n✅ Saved: {fname}.csv + .npz ({ml} samples)")
    print("Scope resumed.")
    return npz_path

if __name__ == '__main__':
    label = sys.argv[1] if len(sys.argv) > 1 else 'capture'
    capture(label)
