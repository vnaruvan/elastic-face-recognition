# Historical AWS Deployment Results

This document records performance measurements from the original AWS deployment (Spring 2025). These results are historical—the AWS resources have been destroyed and the measurements cannot be reproduced.

## Architecture (Original AWS)

```
┌──────────────┐     ┌─────────┐     ┌─────────┐     ┌──────────────────┐
│  Web Tier    │────▶│   SQS   │────▶│ Workers │────▶│  S3 Output       │
│  (EC2/Flask) │     │ Request │     │ (0-15)  │     │                  │
└──────┬───────┘     └─────────┘     └────┬────┘     └──────────────────┘
       │                                   │
       │           ┌─────────┐             │
       └──────────▶│   S3    │◀────────────┘
                   │  Input  │
                   └─────────┘
```

**Components:**
- Web tier: Flask API on EC2 behind load balancer
- Request queue: SQS standard queue with DLQ
- Workers: 0–15 EC2 instances with autoscaling controller
- Storage: S3 for input images and output results

## Message Design

SQS messages contained metadata only (S3 object key), not image payloads:
- Keeps message size small (~100 bytes vs multi-MB images)
- Avoids SQS 256KB message limit
- Workers fetch images directly from S3

Message body format: `{job_id}_{original_filename}`

## Correlation Approach

**Original AWS deployment:** Response queue messages included job_id for correlation.

**Issue identified:** Under concurrent requests, a single API instance polling a shared response queue could consume another request's result. This was not observed during testing but is a design flaw.

**Current LocalStack demo:** Results are written to S3 with `key = job_id`. API polls S3 directly for the specific job_id, eliminating the shared-queue race condition.

## Performance Results

**Test conditions (historical):**
- 100 concurrent image classification requests
- Worker pool: scaled from 0 to ~15 instances during test
- Test executed via workload generator against live AWS endpoint

**Measured results:**
- Average latency: ~0.96 seconds per request
- All 100 requests completed successfully
- Autoscaling responded within polling interval (10s)

*Note: Exact test artifacts and screenshots were not retained. These figures are from the original project submission.*

## Limitations

- AWS resources destroyed after project completion
- Performance numbers reflect specific test conditions and cannot be reproduced
- Autoscaling controller was functional but not production-grade
- Response queue correlation had theoretical concurrency flaw (fixed in LocalStack demo)

## Reproducible Alternative

The LocalStack demo provides a fully reproducible local test path:
```bash
cp .env.example .env
make up
make smoke
```

This validates the core architecture (S3 + SQS + worker) without AWS costs or credentials.

