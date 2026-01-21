# Historical Autoscaling Design

Autoscaling controller design from the original AWS deployment (Spring 2025). AWS resources were torn down; autoscaling code removed as it contained hardcoded instance IDs.

## Scaling Signal

Polled SQS `ApproximateNumberOfMessages` on the request queue.

## Instance Pool

| Parameter | Value |
|-----------|-------|
| Minimum | 0 (scale to zero when idle) |
| Maximum | 15 EC2 instances |
| AMI | Pre-built with face recognition dependencies |

## Scaling Rule

```
desired = min(queue_depth, 15)

if queue_depth == 0:
    stop all running instances
else:
    start (desired - running) instances
```

Simple 1:1 mapping: one worker per pending message, capped at 15.

## Behavior

| Parameter | Value |
|-----------|-------|
| Poll interval | 10 seconds |
| Cooldown | None (aggressive scale-down) |
| Instance start | From stopped state (faster than launch) |

## Limitations

- No gradual scale-down
- No health checks
- Hardcoded EC2 instance IDs (not portable)
- No CloudWatch/ASG integration

## Why Code Was Removed

The controller contained hardcoded instance IDs specific to the original AWS account. Rather than maintain non-functional code, it was replaced with this design documentation.

The LocalStack demo uses Docker Compose—autoscaling is not applicable.
