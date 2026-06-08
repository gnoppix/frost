#-------------------------------------------------------------------------------
# Name: Gnoppix Linux - Services
# Architecture: all
# Date: 2002-2006 by Gnoppix Linux
# Author: Andreas Mueller
# Website: https://www.gnoppix.com
# Licence: Business Source License (BSL / BUSL)
#-------------------------------------------------------------------------------
#!/usr/bin/env python3
"""
Generate synthetic FROST timing traces for testing analyze.py without a browser.

Simulates two phases: idle (low latency) vs. contention (high latency spikes),
mimicking the SSD contention patterns described in the FROST paper.
"""

import json
import argparse
import numpy as np


def generate(num_samples=10000, contention_ratio=0.3, output="synthetic_trace.json"):
    np.random.seed(42)

    base_latency = np.random.normal(loc=80, scale=15, size=num_samples)  # ~80 µs idle
    base_latency = np.clip(base_latency, 30, 200)

    contention_start = int(num_samples * 0.3)
    contention_end = int(num_samples * (0.3 + contention_ratio))

    noise = np.random.exponential(scale=20, size=num_samples)
    spikes = np.zeros(num_samples)
    spikes[contention_start:contention_end] = np.random.exponential(scale=300, size=(contention_end - contention_start))

    samples = base_latency + noise + spikes
    samples = np.round(np.clip(samples, 10, 5000), 2).tolist()

    data = {
        "timestamp": "2026-01-01T00:00:00Z",
        "fileSizeBytes": 512 * 1024 * 1024,
        "readSize": 4096,
        "numSamples": len(samples),
        "samples": samples,
        "note": "Synthetic trace: idle baseline ~80 µs, contention region with spikes up to 5 ms"
    }

    with open(output, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[+] Wrote {len(samples)} samples to {output}")
    print(f"    Idle average: ~80 µs  |  Contention spikes: up to 5 ms")
    print(f"    Contention region: samples {contention_start}-{contention_end}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic FROST trace")
    parser.add_argument("-n", type=int, default=10000, help="Number of samples")
    parser.add_argument("-r", "--ratio", type=float, default=0.3, help="Contention ratio (0-1)")
    parser.add_argument("-o", "--output", default="synthetic_trace.json", help="Output file")
    args = parser.parse_args()
    generate(args.n, args.ratio, args.output)
