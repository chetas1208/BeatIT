# AWS deployment audit

Date: 2026-09-26 UTC

## Result

**BLOCKED by IAM permissions.** The credentials are valid, but the assumed role
cannot provision or inspect the services required to host BeatIT.

## Safe identity details

- Account: `107171643295`
- Principal: `arn:aws:sts::107171643295:assumed-role/WSParticipantRole/Participant`
- Credential source: shared credentials file
- Configured default region: none
- Only permitted deployment region observed in the role policy: `us-east-1`

No access key, secret key, session token, credential file contents, or model
credentials were recorded.

## Permission probes

| Service | Probe | Result |
| --- | --- | --- |
| ECR | `DescribeRepositories` | denied |
| ECR Public | `DescribeRepositories` | denied |
| ECS | `ListClusters` | denied |
| App Runner | `ListServices` | denied |
| Amplify | `ListApps` | denied |
| EC2 | `DescribeInstances` | denied |
| Lambda | `ListFunctions` | denied |
| Lightsail | `GetInstances` | denied |
| CloudFormation | `ListStacks` | denied |
| S3 | `ListBuckets` | denied |
| Secrets Manager | `ListSecrets` | denied |
| SSM Parameter Store | `DescribeParameters` | denied |
| CloudWatch Logs | `DescribeLogGroups` | allowed |
| Bedrock | model/profile discovery and inference | allowed |

The role has `AmazonBedrockFullAccess`,
`AmazonBedrockMantleInferenceAccess`, `CloudWatchFullAccessV2`, and a local
workshop policy. That workshop policy grants IAM read operations and restricts
regions, but does not grant AWS hosting or storage permissions.

## Repository findings

- Frontend: Next.js `16.2.7`, Node.js 22.
- Backend: FastAPI served from `api.index:app`.
- Persistence: local SQLite for ensemble, Shadow Trial, and Missing Piece
  records; in-memory case state unless Redis is configured.
- Existing AWS container/IaC deployment: none.
- Amplify's stated Next.js through version 15 support does not cover the current
  Next.js 16 application.
- The existing backend allows CORS from `*`; this must be restricted to the
  deployed frontend origin before a public deployment.

## Local evidence

- `GET /api/health/live`: passed.
- `GET /api/v1/system-check`: passed all deterministic, extraction, operation,
  recovery, trace, and safety checks.
- Bedrock Runtime smoke with `nvidia.nemotron-nano-12b-v2`: passed.
- Data directory size: approximately 825 MiB. Public deployment must use only
  the checked-in synthetic demo fixtures. Raw/open-real patient-level assets
  remain excluded pending license and data-governance review.

## Required unblock

Provide an AWS principal in `us-east-1` with narrowly scoped permission to
create and operate the selected hosting path, including its image/artifact
store, logs, service role, and secret mechanism. At minimum this requires one
compute/hosting service plus ECR or another supported artifact source,
CloudWatch Logs, and Secrets Manager or SSM SecureString.

