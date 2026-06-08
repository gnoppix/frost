# Changelog

## [1.0.0] — 2026-06-08

### Added

- **PoC implementation** (`poc.html`, `server.py`, `analyze.py`, `synthetic_trace.py`) — browser-based SSD contention measurement via OPFS, reproducing the core technique from the FROST paper
- **README.md** with full attack explanation, file descriptions, usage guide, trace format, browser compatibility table, and references
- **COOP/COEP server** with cross-origin isolation headers for high-resolution `performance.now()` timers (required by the attack)

### Changed

- `poc.html` — major performance rewrite:
  - **Float64Array ring buffer** (500K pre-allocated) replaces growing `Array` — zero GC pressure during sustained measurement
  - **Cached `File` reference** — `getFile()` called once at init instead of per-read, eliminating redundant async metadata lookups
  - **`requestAnimationFrame`-throttled UI** — DOM updates at display refresh rate instead of every measurement batch
  - **Larger init chunks** (256 KB vs 64 KB) — file creation ~4x faster
  - **Inlined DOM selector cache** — `document.getElementById` calls resolved once at load
  - **Simplified measurement loop** — fire-and-forget promises instead of `Promise.all` batching
  - Removed unused `lastValues` tracking array
- `analyze.py` — fully vectorized spike filter:
  - **`np.convolve` rolling mean** replaces per-index Python `for` loop (~50x faster)
  - **Compact aligned output table** shows raw + filtered stats side by side
  - Contention detection returns rolling mean directly, avoiding recomputation for plot
  - Removed `plt.show()` call that hung on headless Wayland
- `server.py` — `ThreadingMixIn` server handles concurrent requests; `allow_reuse_address` prevents bind errors on restart
- `synthetic_trace.py` — single-pass numpy chained operations; compact JSON output (no indent)

### Fixed

- Operator precedence bug in `avgText` display (`sum / last.length.toFixed(2)` → `(sum / last.length).toFixed(2)`)
- Plot generation blocking on systems without display server (`matplotlib.use('Agg')` added at import)
- Async error in `generateLoad()` — unhandled promise rejection now caught with `.catch()`

### Removed

- Gnoppix Linux license header from `server.py` and `synthetic_trace.py` (irrelevant boilerplate)
- Redundant `# COOP/COEP` inline comments (self-documenting header names)
- `MEASURE_INTERVAL_MS` constant (unused)
- `=` separator line in analyze.py multi-file mode
