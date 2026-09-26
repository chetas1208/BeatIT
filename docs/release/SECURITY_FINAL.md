# M10.5 Security Final

## PASS

- `.env` is mode `0600` and Git-ignored.
- No high-confidence secret exposure was found in tracked source, build
  output, demo artifacts, or inspected logs.
- `.dockerignore` excludes secrets, dependencies, private/generated data, and
  model weights.
- Public status responses omit secret values.
- Invalid input and unsafe clinical requests are rejected or degraded safely.
- CORS now uses an explicit local/configured origin allow-list without browser
  credentials by default.
- API errors and validation failures include the canonical safety disclaimer.
- Trace sanitization redacts credential-shaped keys and upload filenames are
  reduced to safe basenames before storage.
- Baseline API response headers include `nosniff`, `DENY` framing, and a strict
  referrer policy.

## OPEN / synthetic-demo-only boundary

- Authentication, authorization, tenant isolation, and retention remain absent;
  the API is unsuitable for patient data.
- Uploads are still fully buffered before the 200 MiB limit is enforced, and
  MIME/content scanning is not a hosted security certification.
- Local stores lack tenant isolation, retention enforcement, and authenticated
  access.
- Public proxy/TLS/header verification is not complete; HSTS/CSP must be set by
  the approved TLS proxy.
