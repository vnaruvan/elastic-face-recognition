"""
LEGACY FILE - AWS EC2 autoscaling controller.
Not part of the LocalStack demo. Kept for reference only.

This file contains hardcoded AWS instance IDs and queue URLs that were
specific to the original AWS deployment. Do not run this locally.

For local testing, use docker-compose which handles scaling via
container orchestration instead of EC2 autoscaling.
"""

import boto3
import time

# HARDCODED VALUES - left intentionally for historical reference
# These would need to be replaced with config-based values for real AWS use

sqs_queue = boto3.client('sqs', region_name='us-east-1')
ec2_instance = boto3.client('ec2', region_name='us-east-1')
sqs_req_queue_url = 'https://sqs.us-east-1.amazonaws.com/REDACTED/req-queue'
sqs_resp_queue_url = 'https://sqs.us-east-1.amazonaws.com/REDACTED/resp-queue'

# Original project had 15 pre-provisioned EC2 instances
ec2_instance_names = [f"app-tier-instance-{i}" for i in range(1, 16)]
ec2_instance_ids = []  


def ec2_instance_initializer():
    """Stop all instances on startup to avoid idle cost."""
    for each_instance in ec2_instance_ids:
        instance_info = ec2_instance.describe_instances(InstanceIds=[each_instance])
        ec2_instance_state = instance_info['Reservations'][0]['Instances'][0]['State']['Name']
        if ec2_instance_state != 'stopped':
            ec2_instance.stop_instances(InstanceIds=[each_instance])
            print(f"Instance stopped {each_instance}")


def sqs_req_message_number():
    """Get approximate message count for scaling decisions."""
    queue_info = sqs_queue.get_queue_attributes(
        QueueUrl=sqs_req_queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(queue_info['Attributes']['ApproximateNumberOfMessages'])


def ec2_instance_running_checker():
    """Return list of currently running instance IDs."""
    running = []
    for each_instance in ec2_instance_ids:
        try:
            info = ec2_instance.describe_instances(InstanceIds=[each_instance])
            state = info['Reservations'][0]['Instances'][0]['State']['Name']
            if state == 'running':
                running.append(each_instance)
        except Exception as e:
            print(f"Error checking instance status: {e}")
    return running


def autoscaling():
    """
    Scale EC2 instances based on queue depth.
    Simple 1:1 mapping - one instance per pending message, max 15.
    """
    msg_count = sqs_req_message_number()
    running = ec2_instance_running_checker()

    if msg_count == 0:
        # no work - stop all to save cost
        for instance in running:
            print(f"Stopping {instance} - queue empty")
            ec2_instance.stop_instances(InstanceIds=[instance])
        return

    # scale up to match queue depth (capped at 15)
    target = min(msg_count, 15)
    needed = target - len(running)

    if needed > 0:
        start_idx = len(running)
        to_start = ec2_instance_ids[start_idx:start_idx + needed]
        for instance in to_start:
            state = ec2_instance.describe_instances(
                InstanceIds=[instance]
            )['Reservations'][0]['Instances'][0]['State']['Name']
            if state == 'stopped':
                print(f"Starting {instance}")
                ec2_instance.start_instances(InstanceIds=[instance])

    # check if we can scale down after processing
    new_count = sqs_req_message_number()
    if new_count == 0:
        for instance in running:
            ec2_instance.stop_instances(InstanceIds=[instance])


# Not meant to be run - legacy reference only
if __name__ == '__main__':
    raise RuntimeError("This is legacy code. Use docker-compose for local testing.")

