#!/usr/bin/env python3
"""
FROST PoC - Timing trace analyzer and visualization.

Reads exported JSON traces and performs:
  1. Baseline statistics (min, max, median, percentiles)
  2. Spike filtering via rolling-mean replacement (FROST paper §4)
  3. Contention detection via threshold on rolling average
  4. PNG visualization (4-panel: raw, filtered, rolling mean, distribution)
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
    """Replace outliers (>threshold_us) with rolling-mean of `window` neighbors.
    Fully vectorized via convolution — no Python loop over spike indices."""
    out = samples.copy()
    mask = out > threshold_us
    if not mask.any():
        return out
    kernel = np.ones(window) / window
    rolling = np.convolve(out, kernel, mode='same')
    out[mask] = rolling[mask]
    return out


def detect_contention(samples: np.ndarray, window: int = 50, n_std: float = 2.0):
    """Flag regions where rolling mean > baseline + n_std * std.
    Baseline = 10th percentile (robust against outlier contamination)."""
    baseline = np.percentile(samples, 10)
    std = np.std(samples[samples < baseline * 3])
    kernel = np.ones(window) / window
    rolling = np.convolve(samples, kernel, mode='same')
    threshold = baseline + n_std * std
    return rolling > threshold, threshold, rolling


def print_stats(label: str, samples: np.ndarray):
    print(f"  {label:20s}  mean={samples.mean():8.2f}  median={np.median(samples):8.2f}  "
          f"p10={np.percentile(samples, 10):8.2f}  p90={np.percentile(samples, 90):8.2f}  "
          f"min={samples.min():8.2f}  max={samples.max():8.2f}")


def analyze(path: str):
    with open(path) as f:
        data = json.load(f)

    samples = np.asarray(data['samples'], dtype=np.float64)
    n = len(samples)
    print(f"\n{'─' * 70}")
    print(f"  File:            {path}")
    print(f"  Samples:         {n}")
    print(f"  File size:       {data.get('fileSizeBytes', 'N/A'):>12} B")
    print(f"  Read size:       {data.get('readSize', 4096):>12} B")
    print(f"  Est. duration:   {n * 0.005:>8.1f} s  (at ~200 Hz)")

    print(f"\n  {'─' * 55}")
    print(f"  {'Statistic':>20}  {'mean':>8}  {'median':>8}  {'p10':>8}  {'p90':>8}  {'min':>8}  {'max':>8}")
    print(f"  {'─' * 55}")
    print_stats('Raw (µs)', samples)

    filtered = filter_spikes(samples)
    print_stats('Filtered (µs)', filtered)

    print(f"\n  Spikes removed:  {(samples > 1000).sum():>8}  ({((samples > 1000).sum() / n) * 100:.2f}%)")

    contention_mask, threshold, rolling = detect_contention(filtered)
    pct = contention_mask.mean() * 100
    print(f"\n  {'─' * 42}")
    print(f"  Contention threshold:  {threshold:.2f} µs")
    print(f"  Contended samples:     {contention_mask.sum():>8} / {n} ({pct:.1f}%)")

    if HAS_MPL:
        fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
        x = np.arange(n)

        for ax in axes:
            ax.set_facecolor('#111')
            ax.grid(True, alpha=0.1)

        axes[0].plot(x, samples, color='#0f0', linewidth=0.3, alpha=0.7)
        axes[0].axhline(threshold, color='red', ls='--', lw=1, label=f'threshold={threshold:.0f} µs')
        axes[0].set_ylabel('Latency [µs]')
        axes[0].set_title('FROST PoC — Raw SSD Access Latency Trace')
        axes[0].legend(fontsize=8)

        axes[1].plot(x, filtered, color='#0ff', linewidth=0.3, alpha=0.7)
        axes[1].fill_between(x, 0, filtered, where=contention_mask, color='red', alpha=0.15, label='Contention')
        axes[1].axhline(threshold, color='red', ls='--', lw=1, label=f'threshold={threshold:.0f} µs')
        axes[1].set_ylabel('Latency [µs]')
        axes[1].set_title(f'Filtered (±{1000:.0f} µs clipped) with Contention Regions ({pct:.1f}%)')
        axes[1].legend(fontsize=8)

        axes[2].plot(x, rolling, color='#ff0', linewidth=0.8)
        axes[2].axhline(threshold, color='red', ls='--', lw=1, alpha=0.6)
        axes[2].set_ylabel('Rolling Mean [µs]')
        axes[2].set_title('Rolling Average (window=50)')

        lo = max(samples.min(), 1)
        hi = samples.max()
        bins = np.logspace(np.log10(lo), np.log10(hi), 80)
        axes[3].hist(samples, bins=bins, color='#0f0', alpha=0.6, label='Raw')
        axes[3].hist(filtered, bins=bins, color='#0ff', alpha=0.5, label='Filtered')
        axes[3].axvline(threshold, color='red', ls='--', lw=1, label=f'threshold={threshold:.0f} µs')
        axes[3].set_xscale('log')
        axes[3].set_xlabel('Latency [µs]')
        axes[3].set_ylabel('Count')
        axes[3].set_title('Latency Distribution')
        axes[3].legend(fontsize=8)

        fig.tight_layout()
        out_path = Path(path).with_suffix('.png')
        plt.savefig(out_path, dpi=150, facecolor='#111')
        print(f"\n  Saved: {out_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <trace.json> [trace.json ...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        analyze(p)
