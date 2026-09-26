# AWS service inventory

Audit date: 2026-09-26 UTC.

`Implemented` means source support exists. `Probed` means the campaign made a
read-only/account call. `Deployed` requires a BeatIT resource and runtime
evidence. Only Bedrock has successful runtime evidence, and it was a standalone
smoke—not hosted application traffic.

| AWS service | Purpose | Actual resource | Source reference | Runtime dependency | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Amazon Bedrock | Optional language explanation/reasoning through OpenAI-compatible or Bedrock-specific adapters | Account model access; no BeatIT hosting resource | `python/hearttwin/intelligence/openai_provider.py`, `python/hearttwin/intelligence/bedrock/` | Optional; deterministic cardiac paths survive its absence | **Smoke verified, not deployed as an application** | Model/profile discovery and one minimal `nvidia.nemotron-nano-12b-v2` inference passed in `us-east-1` |
| Amazon CloudWatch Logs | Candidate hosted runtime logs | No BeatIT log group created | No required direct application integration | Optional until an AWS runtime is selected | **Probe allowed; not deployed** | `DescribeLogGroups` allowed |
| Amazon S3 | Optional artifact storage | No bucket created or identified for BeatIT | `python/hearttwin/storage/s3.py`, `python/hearttwin/storage/factory.py` | Optional; local artifact store is default | **Implemented; IAM probe denied; not deployed** | `ListBuckets` denied; audit says no upload occurred |
| Amazon ECR | Candidate container registry | None | No Dockerfile or ECR deployment definition found | Would be required only for a container hosting choice | **Probe denied; not deployed** | `DescribeRepositories` denied |
| Amazon ECS / Fargate | Candidate FastAPI/container hosting | None | No ECS task/service definition found | Optional candidate | **Probe denied; not deployed** | `ListClusters` denied |
| AWS App Runner | Candidate managed container hosting | None | No App Runner service definition found | Optional candidate | **Probe denied; not deployed** | `ListServices` denied |
| AWS Amplify Hosting | Candidate Next.js hosting | None | No Amplify application/configuration found | Optional candidate; current Next.js 16 compatibility was not established | **Probe denied; not deployed** | `ListApps` denied |
| Amazon EC2 | Candidate Docker host | None | No EC2 deployment definition found | Optional candidate | **Probe denied; not deployed** | `DescribeInstances` denied |
| AWS Lambda | Candidate serverless backend | None | `api/index.py` is a generic ASGI export; no Lambda resource definition exists | Optional candidate | **Probe denied; not deployed** | `ListFunctions` denied |
| Amazon Lightsail | Candidate small-instance/container host | None | No Lightsail definition found | Optional candidate | **Probe denied; not deployed** | `GetInstances` denied |
| AWS Secrets Manager | Candidate runtime secret store | None | Environment-driven consumers exist; no Secrets Manager adapter found | Would be recommended for an AWS deployment | **Probe denied; not deployed** | `ListSecrets` denied |
| AWS Systems Manager Parameter Store | Candidate runtime configuration/secret store | None | No Parameter Store adapter found | Optional candidate | **Probe denied; not deployed** | `DescribeParameters` denied |
| AWS CloudFormation | Candidate infrastructure provisioning | None | No CloudFormation template found | Not currently used | **Probe denied; not deployed** | `ListStacks` denied |
| Amazon RDS | Potential database only if architecture changes | None | No RDS-backed BeatIT persistence path found | Not required by current local architecture | **Not selected; not deployed** | Current experiment stores are SQLite; no deployment evidence |

## Safe identity context

- Account: `107171643295`
- Principal at audit: `WSParticipantRole/Participant`
- Region used for successful Bedrock smoke: `us-east-1`
- Hosting outcome: failed before mutation

No credential values are recorded here.
