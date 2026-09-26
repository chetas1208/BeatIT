# BeatIT Cloudflare Tunnel Verification

## Current result

`cloudflared` is installed on the host, but no named/managed tunnel token,
origin certificate, tunnel configuration, or public hostname is available in
the private environment. The public gate is therefore **BLOCKED**, not passed.

Quick Tunnels are intentionally not used for the canonical public verification:
Cloudflare documents that they are for testing/development and do not support
Server-Sent Events, while BeatIT's live trace surface uses SSE.

## Safe startup

Start BeatIT first, then provide either a private token or config path:

```bash
BEATIT_CLOUDFLARE_TUNNEL_TOKEN='set-in-private-shell' \
BEATIT_ORIGIN_URL=http://127.0.0.1:8000 \
./scripts/start-tunnel.sh
```

The token is never printed or written to the repository. A locally managed
config may be supplied with `BEATIT_CLOUDFLARE_CONFIG` instead. Set the public
HTTPS hostname in `BEATIT_PUBLIC_URL` or `.run/beatit/public-url`, then run:

```bash
./scripts/verify-tunnel.sh
./scripts/verify-model-data-public.sh --public
./scripts/stop-tunnel.sh
```

Verification must exercise the public application routes; a connected
`cloudflared` process alone is not evidence that the BeatIT origin works.
