# Phase 2 AWS Infrastructure Setup

This runbook matches the current Django backend in this repository.

Relevant code:

- Database config: `newshub_core/settings.py`
- Redis/Channels/Celery config: `newshub_core/settings.py`
- S3 storage config: `newshub_core/settings.py`
- ALB health check endpoint: `/health/`
- WebSocket route: `/ws/live-updates/<article_id>/`

## 1. Create security groups

Create these security groups in the same VPC:

### `alb-sg`

- Inbound `80` from `0.0.0.0/0`
- Inbound `443` from `0.0.0.0/0`

### `app-sg`

- Inbound `8000` from `alb-sg`
- Outbound all traffic

### `db-sg`

- Inbound `5432` from `app-sg`

### `redis-sg`

- Inbound `6379` from `app-sg`

## 2. Create RDS PostgreSQL

AWS Console path:

- `RDS` -> `Databases` -> `Create database`

Recommended values:

- Engine: `PostgreSQL`
- Version: `15.x`
- Template: `Production`
- DB instance identifier: `newshub-postgres`
- Master username: `newshub_user`
- Initial database name: `newshub`
- Public access: `No`
- VPC: same as EC2 and ALB
- Security group: `db-sg`
- Backup retention: at least `7 days`
- Multi-AZ: enable if this is production-critical

After creation, copy the endpoint and put it in `.env`:

```env
DATABASE_URL=postgresql://newshub_user:<PASSWORD>@<RDS_ENDPOINT>:5432/newshub
DATABASE_CONN_MAX_AGE=60
DATABASE_SSL_MODE=require
```

## 3. Create ElastiCache Redis

AWS Console path:

- `ElastiCache` -> `Redis OSS` -> `Create`

Recommended values:

- Deployment option: serverless if budget allows, otherwise small node-based cache
- Engine version: current stable Redis OSS version supported in your region
- VPC: same as EC2
- Security group: `redis-sg`
- Encryption in transit: `Enabled`
- Encryption at rest: `Enabled`

After creation, copy the primary endpoint and put it in `.env`:

```env
REDIS_URL=rediss://<REDIS_ENDPOINT>:6379/0
REDIS_SSL_NO_VERIFY=True
```

## 4. Create S3 bucket and apply CORS

AWS Console path:

- `S3` -> your media bucket -> `Permissions` -> `Cross-origin resource sharing (CORS)`

Apply this JSON:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": [
      "https://dharmanagarlive.com",
      "https://www.dharmanagarlive.com",
      "http://127.0.0.1:5501",
      "http://localhost:5501"
    ],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

Then update `.env`:

```env
USE_S3=True
AWS_STORAGE_BUCKET_NAME=<BUCKET_NAME>
AWS_S3_REGION_NAME=ap-south-1
```

If the EC2 instance uses an IAM role with S3 permissions, do not set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`.

## 5. Launch EC2 for Daphne and Celery

Recommended baseline:

- AMI: Ubuntu LTS
- Instance type: at least `t3.small`
- Security group: `app-sg`
- Same VPC as RDS and Redis
- IAM role with S3 access to your media bucket

Install app dependencies, clone the repo, create a Python virtualenv, then place the production `.env` at:

```text
/home/ubuntu/Myproject/news-backend/.env
```

You can automate most of the server bootstrap with:

```bash
cd /home/ubuntu/Myproject/news-backend
bash deploy/aws/bootstrap_ubuntu.sh
```

## 6. Install systemd services

Copy these files from this repo:

- `deploy/systemd/newshub-daphne.service`
- `deploy/systemd/newshub-celery.service`

Install them:

```bash
sudo cp deploy/systemd/newshub-daphne.service /etc/systemd/system/
sudo cp deploy/systemd/newshub-celery.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable newshub-daphne
sudo systemctl enable newshub-celery
sudo systemctl start newshub-daphne
sudo systemctl start newshub-celery
```

Run one-time setup before starting services if the database is new:

```bash
source /home/ubuntu/venvs/newshub/bin/activate
cd /home/ubuntu/Myproject/news-backend
python manage.py migrate
python manage.py collectstatic --noinput
python create_superuser.py
```

## 7. Create the ALB

AWS Console path:

- `EC2` -> `Load Balancers` -> `Create load balancer` -> `Application Load Balancer`

Recommended values:

- Scheme: `Internet-facing`
- IP address type: `IPv4`
- Security group: `alb-sg`
- Subnets: at least two public subnets in different AZs

Create a target group:

- Target type: `Instance`
- Protocol: `HTTP`
- Port: `8000`
- Health check path: `/health/`
- Health check success code: `200`

Register the EC2 instance in that target group.

Listener setup:

- `HTTP :80` -> redirect to `HTTPS :443`
- `HTTPS :443` -> forward to the backend target group

Important ALB setting:

- Increase `idle_timeout.timeout_seconds` to `300` or `600`

That is required for long-lived WebSocket connections.

## 8. Request ACM certificate and attach it

AWS Console path:

- `ACM` -> `Request` -> `Request a public certificate`

Request these names as needed:

- `api.dharmanagarlive.com`
- `dharmanagarlive.com`
- `www.dharmanagarlive.com`

Choose `DNS validation`, add the generated CNAME records in Route 53 or your DNS provider, and wait for the certificate status to become `Issued`.

Then attach the certificate to the ALB `HTTPS :443` listener.

## 9. Update DNS

Create Route 53 alias records:

- `api.dharmanagarlive.com` -> ALB
- `dharmanagarlive.com` -> frontend hosting target
- `www.dharmanagarlive.com` -> frontend hosting target

If the frontend is also behind the same ALB, route those records to the ALB instead.

## 10. Production `.env`

Use `news-backend/.env.production.example` as the base file for the EC2 server.

Minimum required values:

```env
SECRET_KEY=<SECRET>
DEBUG=False
FRONTEND_URL=https://dharmanagarlive.com
ALLOWED_HOSTS=api.dharmanagarlive.com,dharmanagarlive.com,www.dharmanagarlive.com
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://dharmanagarlive.com,https://www.dharmanagarlive.com
CSRF_TRUSTED_ORIGINS=https://dharmanagarlive.com,https://www.dharmanagarlive.com,https://api.dharmanagarlive.com
DATABASE_URL=postgresql://newshub_user:<PASSWORD>@<RDS_ENDPOINT>:5432/newshub
DATABASE_CONN_MAX_AGE=60
DATABASE_SSL_MODE=require
REDIS_URL=rediss://<REDIS_ENDPOINT>:6379/0
REDIS_SSL_NO_VERIFY=True
USE_S3=True
AWS_STORAGE_BUCKET_NAME=<BUCKET_NAME>
AWS_S3_REGION_NAME=ap-south-1
```

Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` only if you are not using an EC2 IAM role.

## 11. Verification checklist

Run these checks from EC2:

```bash
curl http://127.0.0.1:8000/health/
sudo systemctl status newshub-daphne
sudo systemctl status newshub-celery
```

Verify through the ALB:

```bash
curl -I https://api.dharmanagarlive.com/health/
```

Verify WebSocket support from the browser:

```text
wss://api.dharmanagarlive.com/ws/live-updates/123/
```

Expected results:

- `/health/` returns `200`
- ALB target becomes `healthy`
- media files load from S3 without CORS errors
- live updates connect over `wss://`

## 12. What still requires AWS account access

These steps cannot be completed locally from this repository alone:

- Creating RDS
- Creating ElastiCache
- Creating S3 bucket or editing bucket CORS
- Creating EC2
- Creating the ALB and target group
- Requesting the ACM certificate
- Adding DNS records
