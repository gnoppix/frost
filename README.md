# FROST PoC — SSD Contention Side Channel via OPFS

Proof-of-concept implementation of the attack described in **"FROST: Fingerprinting Remotely using OPFS-based SSD Timing"** (Weissteiner et al., Graz University of Technology).

## How It Works

Modern SSDs are fast but still ~100x slower than DRAM. When two processes access the same SSD simultaneously, they *contend* for the drive's limited I/O queue — each operation takes measurably longer.

**FROST exploits this from the browser:**

```
Attacker Page (JS)                   Victim Activity on Same SSD
       │                                     │
       ├─ Create 512 MB OPFS file ───────────┤
       │   (bypasses OS page cache)           │
       ├─ Random 4 KB reads ──────────────►   │
       │   measure latency via perf.now()     │  website loads,
       │                                      │  app starts,
       │  ◄── latency spikes when ────────────┤  file writes,
       │       SSD is busy                     │  etc.
       │                                      │
       └─ Export trace → classify with CNN ───┘
```

### Key Techniques from the Paper

| Technique | Why |
|---|---|
| **Large OPFS file** (>RAM size) | Bypasses the OS page cache — every read hits the SSD |
| **Random 4 KB reads** | Defeats hardware prefetching |
| **COOP/COEP headers** (`same-origin` + `require-corp`) | Unlocks high-resolution `performance.now()` timers (~5 µs granularity) |
| **Spike filtering** (>1 ms → replace with local mean) | Removes OS scheduler noise (paper reports ~0.1% of samples) |
| **CNN classification** | Matches latency trace patterns to specific websites/applications |

### Achieved Results (from the paper)

- **Covert channel**: 661 bit/s (Linux), 891 bit/s (macOS) via OPFS
- **Website fingerprinting** (top-50): 88.95% F1 closed-world, 86.95% open-world
- **Application fingerprinting** (10 apps): 95.83% F1 closed-world

## Files

| File | Role |
|---|---|
| `poc.html` | Browser attack page — creates OPFS file, measures read latency in real-time |
| `server.py` | Python HTTP server that serves the page with required COOP/COEP headers |
| `analyze.py` | Post-processing: spike filtering, contention detection, PNG visualization |
| `synthetic_trace.py` | Generates synthetic traces for testing the analysis pipeline offline |

## Quick Start

### 1. Install dependencies

```bash
pip install --user numpy matplotlib
```

### 2. Start the server

```bash
python3 server.py --port 8443
```

Opens at `http://localhost:8443/poc.html`. The server sets `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` — these are required for sub-millisecond timer resolution.

### 3. Use the PoC in the browser

| Step | Button | What happens |
|---|---|---|
| 1 | **Init OPFS File** | Creates a 512 MB file in the browser's Origin Private File System |
| 2 | **Measure SSD Timing** | Starts random 4 KB reads in a loop, recording latency via `performance.now()` |
| — | *Run other apps / visit websites* | SSD contention appears as latency spikes in real-time |
| 3 | **Export Trace (JSON)** | Downloads timing data for offline analysis |
| — | **Generate Contention** | Writes ~50 MB to OPFS as synthetic contention (immediate test without leaving the browser) |

### 4. Analyze the trace

```bash
python3 analyze.py frost_trace_*.json
```

Output includes statistics, detected contention percentage, and saves a 4-panel PNG visualization.

### 5. Test without a browser

```bash
python3 synthetic_trace.py -n 5000 -o /tmp/test.json
python3 analyze.py /tmp/test.json
```

## Trace Format (JSON)

```json
{
  "timestamp": "2026-06-08T12:00:00.000Z",
  "fileSizeBytes": 536870912,
  "readSize": 4096,
  "numSamples": 10000,
  "samples": [87.3, 92.1, 105.7, ...]
}
```

## Contention Detection Algorithm (`analyze.py`)

1. Compute **baseline** = 10th percentile of all samples
2. Compute **std** from samples below `3 × baseline` (excludes outlier spikes)
3. **Threshold** = baseline + `2 × std`
4. Compute **rolling mean** (window = 50 samples)
5. Flag any region where rolling mean exceeds threshold as *contended*

## Browser Compatibility

| Browser | OPFS Support | Notes |
|---|---|---|
| Chrome 102+ | ✓ | Up to 60% of disk space |
| Edge 102+ | ✓ | Same as Chrome (Chromium) |
| Safari 16.4+ | ✓ | Up to 60% of disk space |
| Firefox 111+ | ✓ | Limited to 10 GB per origin |

## Limitations (as noted in the paper)

- Requires the victim's activity to hit the **same physical SSD** as the OPFS file — typically true on laptops with one internal drive
- The large OPFS file (~512 MB+) is necessary to bypass the page cache; this is detectable as unusual disk usage
- Firefox's 10 GB per-origin cap can be sidestepped by using multiple origins or requesting persistent storage permission

## References

- Weissteiner, H., Weiser, T., Czerny, R., Neela, S.R., Rauscher, F., Juffinger, J., Gruss, D. *"FROST: Fingerprinting Remotely using OPFS-based SSD Timing"* — NDSS 2025 (Graz University of Technology)
- Prior work: Juffinger et al. *"Secret Spilling Drive: Leaking User Behavior through SSD Contention"* — NDSS 2025
