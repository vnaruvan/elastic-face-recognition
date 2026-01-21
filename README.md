# Face Recognition Service

Async face recognition API with S3 storage and SQS job queue.

## Background

This project was originally built and deployed on AWS as a cloud computing assignment. The AWS resources (EC2 instances, S3 buckets, SQS queues) have since been destroyed to avoid ongoing costs.

**To run and test locally**, we use [LocalStack](https://localstack.cloud/) - an open-source AWS emulator. This lets you verify the full architecture without an AWS account.

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

**Why S3 polling instead of response queue?**

The original design polled SQS response queue for results. This breaks under concurrency - if two requests are in flight, request A might consume request B's result from the shared queue. Fixed design: worker writes result to S3 keyed by `job_id`, API polls S3 for that specific key. No race conditions.

**Message semantics:**
- SQS provides at-least-once delivery
- Worker is idempotent by `job_id` - reprocessing overwrites same S3 key
- Results keyed by `job_id` prevent cross-request collisions

## Quick Start

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

Results are stored in LocalStack S3:
- Input: `s3://input-bucket/{job_id}_{filename}`
- Output: `s3://output-bucket/{job_id}` (contains recognition result)

## API

### POST /

Upload image for face recognition. Blocks up to `MAX_WAIT_SECONDS` (default 30s) waiting for result.

```bash
curl -F "inputFile=@photo.jpg" http://localhost:8000/
```

**Response:**
- `200` if worker finishes within timeout: `{"job_id": "...", "status": "done", "result": "Person Name"}`
- `202` if still processing: `{"job_id": "...", "status": "pending"}`

### GET /status/{job_id}

Poll for result if POST returned 202.

```bash
curl http://localhost:8000/status/abc123-def456-...
```

**Response:**
- `200` if done: `{"job_id": "...", "status": "done", "result": "..."}`
- `202` if pending: `{"job_id": "...", "status": "pending"}`

### GET /health

Health check. Returns `200 {"status": "ok"}`.

## Configuration

All config via environment variables. Defaults work for LocalStack out of the box.

| Variable | Default | Description |
|----------|---------|-------------|
| AWS_ENDPOINT_URL | (none) | Set to `http://localstack:4566` for LocalStack |
| AWS_REGION | us-east-1 | AWS region |
| AWS_ACCESS_KEY_ID | test | LocalStack accepts any value |
| AWS_SECRET_ACCESS_KEY | test | LocalStack accepts any value |
| S3_IN_BUCKET | input-bucket | Upload destination |
| S3_OUT_BUCKET | output-bucket | Results storage |
| SQS_REQ_QUEUE_NAME | request-queue | Job queue name |
| SQS_RESP_QUEUE_NAME | response-queue | Legacy debug queue |
| SQS_WAIT_TIME_SECONDS | 10 | Long poll duration |
| SQS_VISIBILITY_TIMEOUT_SECONDS | 60 | Message lock time |
| MAX_WAIT_SECONDS | 30 | API blocks this long before returning 202 |
| MAX_FILE_MB | 8 | Upload size limit |

## Development

```bash
# Unit tests (no Docker needed)
make test

# View logs
make logs
make logs-api
make logs-worker

# Inspect LocalStack
docker compose exec localstack awslocal s3 ls s3://output-bucket/
docker compose exec localstack awslocal sqs list-queues

# Cleanup
make down
```

## Project Structure

```
├── core/               # Config and AWS helpers
│   ├── config.py
│   ├── aws_clients.py
│   └── sqs_helpers.py
├── web-tier/
│   └── server.py       # Flask API
├── app-tier/
│   ├── backend.py      # Worker
│   └── face_recognition.py
├── scripts/
│   ├── localstack_init.sh
│   └── smoke_test.py
├── tests/
├── docs/legacy/        # AWS autoscaling (historical)
├── docker-compose.yml
└── Makefile
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Malformed SQS message | Deleted immediately (poison pill) |
| Missing S3 input | Error result written, message deleted |
| Subprocess timeout | Message returned to queue with backoff |
| Oversized upload | Rejected with 400 before S3 upload |

## AWS Deployment

LocalStack is the supported demo path. AWS deployment notes in `docs/legacy/` are historical and incomplete by design - the original AWS resources no longer exist.

