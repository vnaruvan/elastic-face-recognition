# Elastic Face Recognition

Async face recognition pipeline with SQS job queue and S3 storage. LocalStack demo is runnable; original AWS deployment is documented.

## Background

This project was built and deployed on AWS (Spring 2025) as a cloud computing assignment. The AWS resources were torn down after project completion.

**To run locally:** [LocalStack](https://localstack.cloud/) emulates AWS services, allowing full architecture validation without an AWS account.

## Architecture

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Client │────▶│   API   │────▶│   SQS   │────▶│ Worker  │
└─────────┘     └────┬────┘     └─────────┘     └────┬────┘
                     │                               │
                     │         ┌─────────┐           │
                     └────────▶│   S3    │◀──────────┘
                               └─────────┘
```

### Correlation ID

The `job_id` (UUID) correlates requests end-to-end:

- **SQS message body:** `{job_id}_{filename}`
- **S3 input key:** `{job_id}_{filename}`
- **S3 output key:** `{job_id}`
- **Worker logs:** tagged with `job_id`

### Why S3 Polling

The original design used an SQS response queue. This has a concurrency flaw: under shared response queue consumption, request A can receive request B's result.

**Current implementation:** Worker writes to S3 with `key = job_id`. API polls S3 for that specific key—no shared-queue contention.

The response queue exists for legacy/debug purposes. The API does not consume it.

## Quick Start

```bash
cp .env.example .env
make up
make smoke
```

**What this demo proves:**

- End-to-end async flow (SQS → worker → S3)
- Correlation via `job_id` (no cross-request mixups)
- Failure handling (malformed message, missing input, subprocess timeout)

**Expected output:**

```
Smoke test against http://localhost:8000
Health check OK
Upload OK, job_id=..., status=done
Result: ...
PASS
```

## API

### POST /

Upload image for recognition. Returns `200` if completed within `MAX_WAIT_SECONDS`; otherwise `202` with `job_id` for polling.

```bash
curl -F "inputFile=@photo.jpg" http://localhost:8000/
```

**Response (200):**
```json
{"job_id": "abc-123", "status": "done", "result": "Person Name"}
```

**Response (202):**
```json
{"job_id": "abc-123", "status": "pending"}
```

### GET /status/{job_id}

Poll for result.

```bash
curl http://localhost:8000/status/abc-123
```

### GET /health

Returns `200 {"status": "ok"}`.

---

## Historical AWS Deployment (Spring 2025)

| Component | Implementation |
|-----------|----------------|
| Web tier | Flask on EC2 |
| Request queue | SQS Standard with DLQ |
| Workers | 0–15 EC2 instances |
| Autoscaling | Queue-depth driven (1 instance per message) |
| Storage | S3 input + output buckets |

### Autoscaling

Workers scaled 0→15 based on `ApproximateNumberOfMessages`. Design details in [docs/historical-autoscaling.md](docs/historical-autoscaling.md).

### Performance (Historical)

Measured during original AWS deployment:

| Metric | Value |
|--------|-------|
| Test | 100-request load test |
| Avg latency | ~0.96s (upload → result available) |
| Success rate | 100% |

*Test artifacts not retained. Results reflect the AWS environment at the time and are not reproducible.*

See [docs/historical-aws-results.md](docs/historical-aws-results.md) for details.

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_ENDPOINT_URL` | — | `http://localstack:4566` for LocalStack |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | `test` | Any value for LocalStack |
| `AWS_SECRET_ACCESS_KEY` | `test` | Any value for LocalStack |
| `S3_IN_BUCKET` | `input-bucket` | Upload destination |
| `S3_OUT_BUCKET` | `output-bucket` | Results storage |
| `SQS_REQ_QUEUE_NAME` | `request-queue` | Job queue |
| `SQS_RESP_QUEUE_NAME` | `response-queue` | Legacy/debug only |
| `SQS_WAIT_TIME_SECONDS` | `10` | Long poll duration |
| `SQS_VISIBILITY_TIMEOUT_SECONDS` | `60` | Message lock time |
| `MAX_WAIT_SECONDS` | `30` | API timeout before 202 |
| `MAX_FILE_MB` | `8` | Upload size limit |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Malformed SQS message | Deleted (poison pill) |
| Missing S3 input | Error written to output, message deleted |
| Subprocess timeout | Message returned to queue with backoff |
| Oversized upload | Rejected with 400 |

## Development

```bash
make test          # Unit tests
make logs          # Container logs
make down          # Cleanup
```

## Project Structure

```
├── core/                  # Config, AWS clients
├── web-tier/server.py     # Flask API
├── app-tier/backend.py    # Worker
├── scripts/               # Init + smoke test
├── tests/                 # Unit tests
├── docs/                  # Historical documentation
├── docker-compose.yml
└── Makefile
```

## Runnable Path

LocalStack is the supported demo. AWS resources no longer exist.

```bash
cp .env.example .env
make up
make smoke
# Expected: PASS
```
