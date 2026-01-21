# Historical Autoscaling Design

This document describes the autoscaling controller used in the original AWS deployment (Spring 2025). The AWS resources have been destroyed and the autoscaling code has been intentionally removed as it was not production-quality.

## Scaling Signal

The controller polled SQS `ApproximateNumberOfMessages` attribute on the request queue to determine current backlog.

## Instance Pool

- **Minimum:** 0 instances (scale to zero when idle)
- **Maximum:** 15 EC2 worker instances
- Pre-provisioned AMIs with face recognition dependencies installed

## Scaling Rule

```
desired_instances = min(queue_depth, 15)

if queue_depth == 0:
    stop all running instances
else:
    start (desired_instances - running_instances) stopped instances
```

Simple 1:1 mapping: one worker instance per pending message, capped at 15.

## Cooldown Behavior

- Poll interval: 10 seconds
- No explicit cooldown period between scale events
- Instances started from stopped state (not launched fresh) for faster spin-up

## Limitations

- No gradual scale-down (aggressive stop on empty queue)
- No health checks on worker instances
- Hardcoded instance IDs (not suitable for production)
- No CloudWatch alarms or ASG integration

## Why Code Was Removed

The autoscaling controller contained hardcoded EC2 instance IDs specific to the original AWS account. Rather than maintain non-functional code, it has been replaced with this design documentation.

The LocalStack demo uses Docker Compose for the worker, which does not require autoscaling.

