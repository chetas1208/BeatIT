# BeatIT artifact storage

`LocalArtifactStore` is the default development implementation. It writes only
under `ARTIFACT_ROOT` and rejects path traversal.

`S3ArtifactStore` is a real optional adapter selected only when:

```bash
AWS_ENABLED=true
AWS_REGION=us-west-2
AWS_S3_BUCKET=...
```

It uses the optional `boto3` dependency and deployment-provided AWS credentials.
Local execution does not require boto3 or AWS credentials. `storage_status()`
reports `local` or `s3` without exposing credentials.
