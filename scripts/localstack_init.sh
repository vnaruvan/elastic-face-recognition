#!/bin/bash
# Idempotent LocalStack resource setup - safe to rerun

ENDPOINT="http://localhost:4566"

# set AWS config for all commands
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"

S3_IN_BUCKET="${S3_IN_BUCKET:-input-bucket}"
S3_OUT_BUCKET="${S3_OUT_BUCKET:-output-bucket}"
SQS_REQ_QUEUE="${SQS_REQ_QUEUE_NAME:-request-queue}"
SQS_RESP_QUEUE="${SQS_RESP_QUEUE_NAME:-response-queue}"
SQS_DLQ="${SQS_REQ_QUEUE}-dlq"
MAX_RECEIVE="${SQS_MAX_RECEIVE_COUNT:-5}"

echo "Creating S3 buckets..."
aws --endpoint-url="$ENDPOINT" s3 mb "s3://$S3_IN_BUCKET" 2>/dev/null || echo "  $S3_IN_BUCKET exists"
aws --endpoint-url="$ENDPOINT" s3 mb "s3://$S3_OUT_BUCKET" 2>/dev/null || echo "  $S3_OUT_BUCKET exists"

echo "Creating SQS queues..."
# DLQ first - needed for redrive policy
aws --endpoint-url="$ENDPOINT" sqs create-queue --queue-name "$SQS_DLQ" 2>/dev/null || echo "  $SQS_DLQ exists"
aws --endpoint-url="$ENDPOINT" sqs create-queue --queue-name "$SQS_RESP_QUEUE" 2>/dev/null || echo "  $SQS_RESP_QUEUE exists"
# request queue - create without redrive first, then add policy
aws --endpoint-url="$ENDPOINT" sqs create-queue --queue-name "$SQS_REQ_QUEUE" 2>/dev/null || echo "  $SQS_REQ_QUEUE exists"

# get DLQ ARN and set redrive policy on request queue
DLQ_ARN=$(aws --endpoint-url="$ENDPOINT" sqs get-queue-attributes \
    --queue-url "$ENDPOINT/000000000000/$SQS_DLQ" \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text 2>/dev/null)

if [ -n "$DLQ_ARN" ]; then
    echo "Setting redrive policy on $SQS_REQ_QUEUE..."
    REDRIVE_POLICY="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"$MAX_RECEIVE\"}"
    aws --endpoint-url="$ENDPOINT" sqs set-queue-attributes \
        --queue-url "$ENDPOINT/000000000000/$SQS_REQ_QUEUE" \
        --attributes "RedrivePolicy=$REDRIVE_POLICY" 2>/dev/null || echo "  redrive policy failed (non-critical)"
fi

echo ""
echo "LocalStack init complete"
echo "  S3 buckets: $S3_IN_BUCKET, $S3_OUT_BUCKET"
echo "  SQS queues: $SQS_REQ_QUEUE, $SQS_RESP_QUEUE, $SQS_DLQ"
