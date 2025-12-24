# Elastic Face Recognition Service (AWS EC2 + S3 + SQS)

[![Amazon EC2](https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazonec2&logoColor=white)](https://aws.amazon.com/ec2/)
[![Amazon S3](https://img.shields.io/badge/AWS-S3-FF9900?logo=amazons3&logoColor=white)](https://aws.amazon.com/s3/)
[![Amazon SQS](https://img.shields.io/badge/AWS-SQS-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/sqs/)
[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://www.python.org/)

Multi tier face recognition service built on AWS IaaS. A single web tier EC2 instance accepts image uploads over HTTP, persists inputs to S3, and enqueues work to SQS. An elastic application tier scales from 0 to 15 EC2 instances based on queue depth, performs model inference, writes outputs to S3, and returns results to the web tier through a response queue.

> Source code is not public. This repository documents architecture, interfaces, and operational behavior.

---

## System overview

- Ingress: HTTP POST to `/` on port `8000` on a web tier EC2 instance
- Persist: input images stored in an S3 input bucket
- Dispatch: web tier enqueues requests to an SQS request queue (message size constrained so images are not sent through SQS)
- Compute: application tier instances poll the request queue, fetch images from S3, run face recognition inference, and store results in an S3 output bucket
- Egress: application tier publishes results to an SQS response queue; web tier returns plain text `<filename>:<prediction>` to the original HTTP request

---

## Architecture

### Components
- Web tier (EC2): `server.py` (request handling) and `controller.py` (autoscaling controller)
- App tier (EC2): `backend.py` (poll, infer, publish)
- Storage: S3 input bucket and S3 output bucket
- Messaging: SQS request queue and SQS response queue

~~~mermaid
flowchart LR
  User[Client] -->|HTTP POST image| Web[Web tier EC2]
  Web -->|store image| S3In[S3 input bucket]
  Web -->|enqueue filename plus request_id| ReqQ[SQS request queue]
  Ctrl[Autoscaling controller] -->|start or stop| App[App tier EC2 instances]
  App -->|fetch image| S3In
  App -->|write prediction| S3Out[S3 output bucket]
  App -->|publish result| RespQ[SQS response queue]
  Web -->|wait for result| RespQ
  Web -->|plain text response| User
~~~

---

## Interface contract

### Client to web tier (HTTP POST)

Endpoint:
- `/` on port `8000`

Payload:
- form field key must be `inputFile`
- file name example: `test_000.jpg`

Web tier behavior:
- stores the uploaded image in the S3 input bucket using the original file name as the object key
- enqueues a lightweight request to the SQS request queue (images are not sent through SQS)

### Web tier response format

The HTTP response is plain text:

`<filename_without_extension>:<prediction>`

Example:
`test_000:Paul`

---

## Data flow and storage

S3 input bucket
- object key: original file name, for example `test_000.jpg`
- object value: raw image bytes

S3 output bucket
- object key: file name without extension, for example `test_000`
- object value: predicted label, for example `Paul`

SQS request queue message
- contains metadata needed for the app tier to retrieve the input from S3 (not the image bytes)
- request queue max message size is configured to `1 KB` to prevent sending images through SQS

SQS response queue message
- contains the result needed for the web tier to complete the original HTTP request

---

## Autoscaling behavior

Autoscaling is implemented in `controller.py` (custom controller, not managed autoscaling).

Policies:
- app tier scales to `0` instances when there are no requests waiting or in flight
- app tier scales up to a maximum of `15` instances
- each app tier instance processes `1` request at a time
- after completing a request, an app tier instance stops immediately if no more pending requests exist; otherwise it continues to the next request
- instances can be initialized in `stopped` state to reduce startup overhead and started on demand

---

## Technologies

Core

Python

AWS Services

Amazon EC2 (web tier instance and elastic app tier)  
Amazon S3 (input persistence and output storage)  
Amazon SQS (request queue and response queue)  

ML and runtime

Torch CPU build (inference runtime)  
Model weights packaged on the app tier AMI  

---

## Benchmark (representative run)

Workload

100 HTTP POST requests (images) sent to the web tier.

Metric

Time from HTTP POST received by the web tier to plain text response returned to the client.

Results

Requests completed: 100/100  
Failed requests: 0  
Average end to end latency: 0.96 seconds  
Total wall time (100 requests): 115 seconds  
Scale in time to 0 app instances after workload: 0.24 seconds  

Notes

Latency depends on image size, EC2 instance types, AMI warm state, queue depth, and S3 and SQS performance.

---

## Operational notes

Web tier stability

The web tier runs on a single EC2 instance. Use a static IP (Elastic IP) if the service endpoint must remain stable across restarts.

Queue and bucket hygiene

During development, ensure SQS queues and S3 buckets do not retain stale objects or messages that can cause repeated processing or unnecessary compute.

Observability

Track:
- SQS request queue depth and response queue depth
- number of running app tier instances
- S3 object counts in input and output buckets
- per request latency measured at the web tier

---

## Repository notes

This repository is intended to present the architecture and design of the project only. Source code is not shared online due to course policy. If you'd like to take a look at the code, please contact me.
