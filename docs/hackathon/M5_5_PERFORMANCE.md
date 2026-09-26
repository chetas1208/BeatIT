# M5.5 performance evidence

Measured locally with a synthetic baseline, fresh file-backed SQLite database,
and the current full-state response contract:

| Requested samples | Generation | JSON serialization | SQLite save | Approx. payload |
|---:|---:|---:|---:|---:|
| 50 | 9.6 ms | 2.9 ms | 51.0 ms | 238 KiB |
| 100 | 32.1 ms | 6.0 ms | 48.5 ms | 473 KiB |
| 250 | 58.4 ms | 14.5 ms | 107.3 ms | 1.18 MiB |
| 500 | 141 ms | 27.8 ms | 111 ms | 2.35 MiB |
| 1000 | 269 ms | 57.4 ms | 239 ms | 4.69 MiB |

The POST route now runs ensemble generation and persistence in a worker thread,
so synchronous CPU/SQLite work does not block the FastAPI event loop. These are
local measurements, not a hosted-capacity guarantee. The demo default remains
100 samples; 250–500 is the safe local range until target-host repeats exist.

The current contract persists a full typed state per sample. Large CT payloads
must not be placed in that state for a production deployment; M5.5 remains a
trusted-network hackathon persistence seam, not a multi-worker clinical store.
