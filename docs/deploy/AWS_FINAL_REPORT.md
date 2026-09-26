# BeatIT AWS deployment final report

Date: 2026-09-26 UTC

Status: **FAILED — genuine IAM blocker**

The AWS credentials are valid and Bedrock inference works in `us-east-1`.
However, the role cannot access ECR, ECS, App Runner, Amplify, EC2, Lambda,
Lightsail, S3, Secrets Manager, SSM Parameter Store, or CloudFormation as
needed to host the application. No safe AWS deployment path exists with this
principal.

Local BeatIT and VISTA readiness were inspected. BeatIT's deterministic system
check passes. VISTA-3D `0.5.8` is loaded on two RTX 3090 GPUs and the checkpoint
is present, but the current API process has authentication disabled. It was not
tunneled.

No AWS resources were created, no data were uploaded, and no public URLs exist.
See [AWS_DEPLOYMENT_AUDIT.md](./AWS_DEPLOYMENT_AUDIT.md) for exact probes and
[AWS_SECURITY.md](./AWS_SECURITY.md) for the failed VISTA/CORS security gates.

