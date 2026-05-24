---
type: error_fix
tool: Docker
topic: containers
project: learnstack
---

# EOF error pulling postgres:15 image from Docker Hub

**Error:** `failed to copy: httpReadSeeker: failed open: failed to do request: EOF`

**When:** Running `docker compose up db -d` for the first time to pull the postgres:15 image.

**Cause:** Intermittent connection drops to Docker Hub's CloudFront CDN
(production.cloudfront.docker.com) during image layer download. The full
postgres:15 image has many large layers, making it more likely a drop occurs
mid-pull.

**Temporary fix:** Switch to `postgres:15-alpine` in docker-compose.yml.

```yaml
image: postgres:15-alpine
```

The alpine variant is roughly 1/4 the size with fewer, smaller layers.
Functionally identical for development — same Postgres 15 engine.

**Note:** Each failed attempt does cache completed layers, so retrying
eventually works too. Alpine is just faster when the connection is flaky.
