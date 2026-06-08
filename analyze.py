#!/usr/bin/env python3
"""
FROST PoC - Timing trace analyzer and visualization.

Reads exported JSON traces from the browser PoC and performs:
  1. Baseline statistics
  2. Contention detection via thresholding
  3. Spike filtering (as described in the FROST paper)
  4. Visual comparison of idle vs. contention periods
"""

import json
import sys
import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[!] matplotlib not installed; install with: pip install matplotlib")


def filter_spikes(samples: np.ndarray, threshold_us: float = 1000.0, window: int = 100) -> np.ndarray:
    """
    Replace samples > threshold_us with the mean of `window` surrounding values.
    As described in the FROST paper Section 4.
    """
    out = samples.copy().astype(np.float64)
    spikes = np.where(out > threshold_us)[0]
    for idx in spikes:
        lo = max(0, idx - window // 2)
        hi = min(len(out), idx + window // 2)
        out[idx] = np.mean(out[lo:hi])
    return out


def detect_contention(samples: np.ndarray, window: int = 50, threshold_std: float = 2.0) -> np.ndarray:
    """
    Simple contention detection: flag regions where rolling mean exceeds
    baseline + threshold_std * std.
    """
    baseline = np.percentile(samples, 10)
    std = np.std(samples[samples < baseline * 3])
    rolling = np.convolve(samples, np.ones(window) / window, mode='same')
    threshold = baseline + threshold_std * std
    return rolling > threshold, threshold


def analyze(path: str):
    with open(path) as f:
        data = json.load(f)

    samples = np.array(data['samples'], dtype=np.float64)
    print(f"File:              {path}")
    print(f"Samples:           {len(samples)}")
    print(f"File size:         {data.get('fileSizeBytes', 'N/A')} bytes")
    print(f"Read size:         {data.get('readSize', 4096)} B")
    print(f"Duration:          {(len(samples) * 0.005):.1f}s (estimated at 200 Hz)")

    print(f"\n--- Timing Statistics (raw) ---")
    print(f"  Min:    {samples.min():.2f} µs")
    print(f"  Max:    {samples.max():.2f} µs")
    print(f"  Mean:   {samples.mean():.2f} µs")
    print(f"  Median: {np.median(samples):.2f} µs")
    print(f"  Std:    {samples.std():.2f} µs")
    print(f"  p10:    {np.percentile(samples, 10):.2f} µs")
    print(f"  p90:    {np.percentile(samples, 90):.2f} µs")

    filtered = filter_spikes(samples)
    print(f"\n--- After spike filtering (>1000 µs replaced) ---")
    print(f"  Mean:   {filtered.mean():.2f} µs")
    print(f"  Median: {np.median(filtered):.2f} µs")

    contention_mask, threshold = detect_contention(filtered)
    pct_contended = contention_mask.mean() * 100
    print(f"\n--- Contention Detection ---")
    print(f"  Threshold:         {threshold:.2f} µs")
    print(f"  Samples flagged:   {contention_mask.sum()} / {len(samples)} ({pct_contended:.1f}%)")

    if not HAS_MPL:
        return

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    x = np.arange(len(samples))

    ax = axes[0]
    ax.plot(x, samples, color='#0f0', linewidth=0.3, alpha=0.7)
    ax.axhline(threshold, color='red', linestyle='--', linewidth=1, label=f'Contention threshold ({threshold:.0f} µs)')
    ax.set_ylabel('Latency [µs]')
    ax.set_title('FROST PoC - Raw SSD Access Latency Trace')
    ax.legend(fontsize=8)
    ax.set_facecolor('#111')
    ax.grid(True, alpha=0.1)

    ax = axes[1]
    ax.plot(x, filtered, color='#0ff', linewidth=0.3, alpha=0.7)
    ax.fill_between(x, 0, filtered, where=contention_mask, color='red', alpha=0.15, label='Detected Contention')
    ax.axhline(threshold, color='red', linestyle='--', linewidth=1, label=f'Threshold ({threshold:.0f} µs)')
    ax.set_ylabel('Latency [µs]')
    ax.set_title('Filtered Trace with Contention Regions (spikes >1ms replaced)')
    ax.legend(fontsize=8)
    ax.set_facecolor('#111')
    ax.grid(True, alpha=0.1)

    ax = axes[2]
    rolling_mean = np.convolve(filtered, np.ones(50) / 50, mode='same')
    ax.plot(x, rolling_mean, color='#ff0', linewidth=0.8)
    ax.set_ylabel('Rolling Mean [µs]')
    ax.set_title('Rolling Average (window=50)')
    ax.set_facecolor('#111')
    ax.grid(True, alpha=0.1)

    ax = axes[3]
    hist_bins = np.logspace(np.log10(max(samples.min(), 1)), np.log10(samples.max()), 80)
    ax.hist(samples, bins=hist_bins, color='#0f0', alpha=0.7, label='Raw')
    ax.hist(filtered, bins=hist_bins, color='#0ff', alpha=0.5, label='Filtered')
    ax.axvline(threshold, color='red', linestyle='--', linewidth=1, label=f'Threshold ({threshold:.0f} µs)')
    ax.set_xscale('log')
    ax.set_xlabel('Latency [µs] (log scale)')
    ax.set_ylabel('Count')
    ax.set_title('Latency Distribution (log scale)')
    ax.legend(fontsize=8)
    ax.set_facecolor('#111')

    fig.tight_layout()
    out_path = Path(path).with_suffix('.png')
    plt.savefig(out_path, dpi=150, facecolor='#111')
    print(f"\n[+] Saved visualization to {out_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <trace.json> [trace2.json ...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        analyze(p)
        print("=" * 60)
