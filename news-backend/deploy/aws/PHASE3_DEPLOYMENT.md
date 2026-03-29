# Phase 3 Deployment and Configuration

This phase assumes the Phase 2 infrastructure already exists:

- PostgreSQL in RDS
- Redis in ElastiCache
- S3 for media
- EC2 for the application containers
- ALB terminating HTTPS with ACM

Relevant files added in this phase:

- `news-backend/.env.production.example`
- `news-backend/docker-compose.prod.yml`
- `news-backend/nginx/prod.conf`

## Task 3.1: Production `.env`

Copy the template into place on the EC2 host:

```bash
cd /home/ubuntu/Myproject/news-backend
cp .env.production.example .env
```

Then replace all placeholder values.

### Exact production values for the critical settings

#### `DEBUG`

Use:

```env
DEBUG=False
```

Do not set `DEBUG=True` in production. This project enables SSL redirects and secure cookies when `DEBUG=False`.

#### `ALLOWED_HOSTS`

Use every hostname that can legitimately reach Django, separated by commas with no spaces.

For the current domain setup in this repo:

```env
ALLOWED_HOSTS=dharmanagarlive.com,www.dharmanagarlive.com,api.dharmanagarlive.com
```

Rules:

- Include the bare domain.
- Include `www` if it resolves to the site.
- Include `api` only if you expose the API/admin on that hostname.
- Do not use `*` in production.

#### `CORS_ALLOWED_ORIGINS`

Lock this to browser origins that serve the frontend.

Use:

```env
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://dharmanagarlive.com,https://www.dharmanagarlive.com
```

Rules:

- Use full origins with scheme: `https://...`
- Do not include paths like `/api`
- Do not include trailing slashes
- Do not include internal AWS hostnames or the EC2 private IP

Also keep CSRF aligned:

```env
CSRF_TRUSTED_ORIGINS=https://dharmanagarlive.com,https://www.dharmanagarlive.com,https://api.dharmanagarlive.com
```

## Task 3.2: Production Docker Compose

Use the production compose file from the backend directory:

```bash
cd /home/ubuntu/Myproject/news-backend
docker compose -f docker-compose.prod.yml up -d --build
```

What is intentionally removed compared to local development:

- No Postgres container
- No Redis container
- No source-code bind mount
- No backend port published to the public internet
- No local TLS certificate handling inside the container stack
- No Celery startup migrations or superuser bootstrap

This compose file expects:

- `DATABASE_URL` to point to RDS
- `REDIS_URL` to point to ElastiCache
- TLS to terminate at the ALB
- ALB target group to forward to the EC2 instance on port `80`
- The EC2 application security group to allow inbound `80` from the ALB security group

Recommended checks after startup:

```bash
docker compose -f docker-compose.prod.yml ps
curl -I http://127.0.0.1/health/
curl -I http://127.0.0.1/api/settings/
```

## Task 3.3: VAPID and Social Media Configuration

### VAPID keys for web push

The backend uses:

- `VAPID_PRIVATE_KEY`
- `VAPID_ADMIN_EMAIL`

The frontend uses:

- `VAPID_PUBLIC_KEY`

This repo now reads the frontend API URL dynamically, but the VAPID public key still needs to match the private key used by Django.

If you already have a working production VAPID pair, keep using the same pair. Rotating the keys invalidates existing browser subscriptions.

If you need a new pair, generate one with a standard VAPID tool such as `web-push`, then place the values in `.env` and update the public key in [news-website/js/config.js](/home/md-helal-uddin/Desktop/Myproject/news-website/js/config.js).

Verification checklist:

1. Confirm `.env` has the correct `VAPID_PRIVATE_KEY` and `VAPID_ADMIN_EMAIL`.
2. Confirm the frontend is serving the matching `VAPID_PUBLIC_KEY`.
3. Open the production site in a browser and allow notifications.
4. Check that a row is created in the `PushSubscription` table.
5. Publish a test article with notifications enabled.
6. Confirm the notification arrives and clicking it opens the production article URL.

Operational note:

- If you generate a brand-new VAPID key pair, clear old subscriptions and re-subscribe browsers. Old subscriptions will not work with the new private key.

### Facebook auto-posting

The code posts directly to:

```text
https://graph.facebook.com/v18.0/<FACEBOOK_PAGE_ID>/feed
```

Required env vars:

```env
FACEBOOK_PAGE_ID=<numeric-page-id>
FACEBOOK_ACCESS_TOKEN=<page-access-token-with-page-post-permission>
```

Verify before going live:

1. The token belongs to the correct Facebook Page, not just a user.
2. The token can publish posts for that page.
3. The page ID matches the page tied to the token.
4. Publish one article with `post_to_facebook=True` and check the page feed.

### X (Twitter) auto-posting

The code uses Tweepy `Client.create_tweet()` and needs a write-capable app.

Required env vars:

```env
TWITTER_API_KEY=<consumer-key>
TWITTER_API_SECRET=<consumer-secret>
TWITTER_ACCESS_TOKEN=<user-access-token>
TWITTER_ACCESS_TOKEN_SECRET=<user-access-token-secret>
```

Verify before going live:

1. The app has read/write permissions.
2. The access token belongs to the account you want to post from.
3. Publish one article with `post_to_twitter=True` and confirm the post appears on X.

### Telegram auto-posting

Required env vars:

```env
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHANNEL_ID=@yourchannel
```

Use either the `@channelusername` or the numeric chat ID. The bot must be an admin in that channel.

Verify before going live:

1. Add the bot to the target channel.
2. Promote it so it can post messages.
3. Publish one article with `post_to_telegram=True`.
4. Confirm the message appears in the correct channel.

## Final production checklist

- `.env` copied from `.env.production.example` and placeholders replaced
- `DEBUG=False`
- `ALLOWED_HOSTS` does not contain `*`
- `CORS_ALLOW_ALL_ORIGINS=False`
- `CORS_ALLOWED_ORIGINS` contains only public frontend origins
- RDS and ElastiCache endpoints reachable from EC2
- S3 bucket configured when `USE_S3=True`
- ALB forwards to EC2 port `80`
- Push subscription test passes
- Facebook, X, and Telegram post tests each pass once in production
