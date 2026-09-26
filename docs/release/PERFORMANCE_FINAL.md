# M10.5 Performance Final

Local bounded evidence:

- Demo seed: approximately 0.4 seconds and below 48 MiB RSS in the agent probe.
- `/api/v1/system-check`: approximately 28.64 ms median across five requests.
- Production frontend build: passed; peak RSS was approximately 2.45 GiB in the
  local probe.
- API E2E, ensemble, Shadow Trial, and Missing Piece completed on temporary
  SQLite stores.

Not measured: supported-browser FPS, Split Heart FPS, concurrent load, soak,
proxy capacity, VISTA inference, or live language-model latency. This is not a
hosted-capacity certification.
