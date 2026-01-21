# Historical AWS Deployment Results

Performance measurements from the original AWS deployment (Spring 2025). AWS resources were torn down after project completion.

## Architecture

```
┌──────────────┐     ┌─────────┐     ┌─────────┐     ┌──────────────┐
│  Web Tier    │────▶│   SQS   │────▶│ Workers │────▶│  S3 Output   │
│  (EC2/Flask) │     │ Request │     │ (0-15)  │     │              │
└──────┬───────┘     └─────────┘     └────┬────┘     └──────────────┘
       │                                   │
       │           ┌─────────┐             │
       └──────────▶│   S3    │◀────────────┘
                   │  Input  │
                   └─────────┘
```

| Component | Implementation |
|-----------|----------------|
| Web tier | Flask API on EC2 |
| Request queue | SQS Standard with DLQ |
| Workers | 0–15 EC2 instances with autoscaling |
| Storage | S3 for input images and output results |

## Message Design

SQS messages contained metadata only (S3 object key), not image payloads:

- Keeps message size small (~100 bytes)
- Avoids SQS 256KB limit
- Workers fetch images from S3

Format: `{job_id}_{original_filename}`

## Performance Results

Measured during original AWS deployment:

| Metric | Value |
|--------|-------|
| Test | 100-request load test |
| Avg end-to-end latency | ~0.96s |
| Success rate | 100% |
| Worker scaling | 0 → ~15 instances |

**End-to-end latency** = time from image upload to result available in S3.

*Test artifacts not retained. These figures are from the original project submission and reflect the AWS environment at the time.*

## Correlation Approach

**Original AWS:** Response queue messages included `job_id`.

**Issue:** Under concurrent requests with shared response queue consumption, request A could receive request B's result.

**LocalStack demo:** Results written to S3 with `key = job_id`. API polls S3 directly—no shared-queue contention.

## Limitations

- AWS resources torn down
- Performance numbers not reproducible
- Autoscaling controller was functional but not production-grade
- Response queue approach had concurrency flaw (fixed in LocalStack demo)

## Reproducible Alternative

```bash
cp .env.example .env
make up
make smoke
```

Validates core architecture locally without AWS.
