#!/usr/bin/env python3
"""
Generate synthetic FROST timing traces for testing the analysis pipeline.

Simulates two phases:
  - Idle:    ~80 µs baseline with Gaussian noise
  - Contention:  exponential-distribution latency spikes (up to 5 ms)
"""

import json
import argparse
import numpy as np


def generate(num_samples=10000, contention_ratio=0.3, output="synthetic_trace.json"):
    np.random.seed(42)

    base = np.random.normal(loc=80, scale=15, size=num_samples).clip(30, 200)
    noise = np.random.exponential(scale=20, size=num_samples)

    spikes = np.zeros(num_samples)
    start = int(num_samples * 0.3)
    end = int(num_samples * (0.3 + contention_ratio))
    spikes[start:end] = np.random.exponential(scale=300, size=end - start)

    samples = np.round((base + noise + spikes).clip(10, 5000), 2).tolist()

    data = {
        "timestamp": "2026-01-01T00:00:00Z",
        "fileSizeBytes": 512 * 1024 * 1024,
        "readSize": 4096,
        "numSamples": len(samples),
        "samples": samples,
        "note": f"Synthetic: idle ~80 µs, contention at samples {start}-{end}"
    }

    with open(output, "w") as f:
        json.dump(data, f)
    print(f"[+] {len(samples)} samples written to {output}")
    print(f"    Idle ~80 µs  |  Contention region: {start}–{end}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic FROST trace")
    parser.add_argument("-n", type=int, default=10000, help="Samples (default: 10000)")
    parser.add_argument("-r", "--ratio", type=float, default=0.3, help="Contention ratio (default: 0.3)")
    parser.add_argument("-o", "--output", default="synthetic_trace.json", help="Output path")
    args = parser.parse_args()
    generate(args.n, args.ratio, args.output)
