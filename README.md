# Elastic Face Recognition

Scalable face recognition service with SQS-based decoupling and S3 storage.

## Background

This project was originally built and deployed on AWS (Spring 2025) as a cloud computing assignment demonstrating autoscaling, message queuing, and distributed image processing. The AWS resources have since been destroyed.

**To run and test locally**, we use [LocalStack](https://localstack.cloud/) - an open-source AWS emulator. This validates the architecture without an AWS account.

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

### Correlation ID Design

The `job_id` (UUID) serves as the correlation ID throughout the system:
- **Request message:** SQS body contains `{job_id}_{filename}`
- **Input storage:** S3 key = `{job_id}_{filename}`
- **Output storage:** S3 key = `job_id`
- **Logs:** All worker logs tagged with `job_id`

This enables end-to-end tracing and ensures results map to the correct request.

### Why S3 Polling (Not Response Queue)

The original design used an SQS response queue for results. Under concurrent requests, this creates a race condition: request A might consume request B's message from the shared queue.

**Current implementation:** Worker writes result to S3 keyed by `job_id`. API polls S3 for that specific key. No shared-queue contention.

The response queue (`SQS_RESP_QUEUE_NAME`) exists for legacy/debug purposes only. The API does not consume it.

## Quick Start (LocalStack)

```bash
cp .env.example .env
make up
make smoke
```

**Expected output:**
```
Smoke test against http://localhost:8000
Health check OK
Upload OK, job_id=abc123-..., status=done
Result: UNKNOWN:test.jpg
PASS
```

Results stored in LocalStack S3:
- Input: `s3://input-bucket/{job_id}_{filename}`
- Output: `s3://output-bucket/{job_id}`

## API

### POST /

Upload image for face recognition. Blocks up to `MAX_WAIT_SECONDS` (default 30s) waiting for result.

```bash
curl -F "inputFile=@photo.jpg" http://localhost:8000/
```

**Response:**
- `200` if worker finishes within timeout: `{"job_id": "...", "status": "done", "result": "..."}`
- `202` if still processing: `{"job_id": "...", "status": "pending"}`

### GET /status/{job_id}

Poll for result if POST returned 202.

```bash
curl http://localhost:8000/status/{job_id}
```

**Response:**
- `200` if done: `{"job_id": "...", "status": "done", "result": "..."}`
- `202` if pending: `{"job_id": "...", "status": "pending"}`

### GET /health

Returns `200 {"status": "ok"}`.

---

## Historical AWS Deployment (Spring 2025)

The original deployment ran on AWS with the following architecture:

| Component | Implementation |
|-----------|----------------|
| Web tier | Flask on EC2 |
| Request queue | SQS Standard with DLQ |
| Workers | 0–15 EC2 instances |
| Autoscaling | Custom controller polling queue depth |
| Storage | S3 (input + output buckets) |

### Autoscaling

Workers scaled 0→15 based on `ApproximateNumberOfMessages` in the request queue. Simple 1:1 mapping: one instance per pending message.

See [docs/historical-autoscaling.md](docs/historical-autoscaling.md) for design details.

### Performance Results (Historical)

Measured during original AWS deployment:
- **Test:** 100 concurrent image classification requests
- **Result:** ~0.96s average latency, 100% success rate
- **Scaling:** Worker pool expanded from 0 to ~15 instances

*These measurements are historical. Test artifacts were not retained. Results reflect the specific AWS environment and workload at the time.*

See [docs/historical-aws-results.md](docs/historical-aws-results.md) for full details.

### Note on Response Queue

The original AWS implementation used a response queue for result delivery. This approach has a theoretical concurrency flaw (shared-queue race condition). The LocalStack demo uses S3-based correlation for correctness.

---

## Configuration

All settings via environment variables. Defaults work for LocalStack.

| Variable | Default | Description |
|----------|---------|-------------|
| AWS_ENDPOINT_URL | (none) | `http://localstack:4566` for LocalStack |
| AWS_REGION | us-east-1 | AWS region |
| AWS_ACCESS_KEY_ID | test | Any value works for LocalStack |
| AWS_SECRET_ACCESS_KEY | test | Any value works for LocalStack |
| S3_IN_BUCKET | input-bucket | Upload destination |
| S3_OUT_BUCKET | output-bucket | Results storage |
| SQS_REQ_QUEUE_NAME | request-queue | Job queue |
| SQS_RESP_QUEUE_NAME | response-queue | Legacy/debug only |
| SQS_WAIT_TIME_SECONDS | 10 | Long poll duration |
| SQS_VISIBILITY_TIMEOUT_SECONDS | 60 | Message lock time |
| MAX_WAIT_SECONDS | 30 | API timeout before returning 202 |
| MAX_FILE_MB | 8 | Upload size limit |

## Development

```bash
make test          # Unit tests (no Docker)
make logs          # All container logs
make logs-worker   # Worker logs only

# Inspect LocalStack
docker compose exec localstack awslocal s3 ls s3://output-bucket/
docker compose exec localstack awslocal sqs list-queues

make down          # Cleanup
```

## Project Structure

```
├── core/                  # Config and AWS client helpers
├── web-tier/server.py     # Flask API
├── app-tier/
│   ├── backend.py         # Worker process
│   └── face_recognition.py
├── scripts/
│   ├── localstack_init.sh # S3/SQS setup
│   └── smoke_test.py      # E2E test
├── tests/                 # Unit tests
├── docs/
│   ├── historical-autoscaling.md
│   └── historical-aws-results.md
├── docker-compose.yml
└── Makefile
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Malformed SQS message | Deleted (poison pill prevention) |
| Missing S3 input | Error result written, message deleted |
| Subprocess timeout | Message returned to queue with backoff |
| Oversized upload | Rejected with 400 |

## Runnable Path

**LocalStack is the supported reproducible demo.** The original AWS resources no longer exist. Autoscaling code has been intentionally removed (design documented in `docs/historical-autoscaling.md`).

```bash
cp .env.example .env
make up
make smoke  # Should print PASS
```
