# Elastic Face Recognition System

This project focuses on building a scalable and fault-tolerant face recognition application using EC2, S3, and SQS on AWS. The system dynamically handles variable workloads by decoupling compute components and integrating autoscaling logic.

## Architecture Overview

- Incoming image files are stored in an S3 bucket.
- An EC2-based processing layer reads from the bucket and performs face recognition.
- SQS is used to manage inter-service communication and queue workloads between stages.
- Autoscaling groups ensure compute resources scale up or down based on queue size and CPU metrics.

## Technologies

- Python, Bash
- AWS EC2, S3, SQS, CloudWatch
- OpenCV, boto3, autoscaling policies

## Features

- Custom autoscaling triggers based on queue length and resource metrics
- Asynchronous processing using decoupled services
- Monitoring via CloudWatch for health, throughput, and bottlenecks

## Notes

This repository is intended to present the architecture and design of the project only. Source code is not shared due to institutional or confidentiality guidelines.
