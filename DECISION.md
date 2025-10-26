# Decision Record — Blue/Green Node.js Deployment Behind Nginx

## Overview
This document explains the reasoning, design choices, and implementation details behind the Blue/Green deployment setup.  
The goal was to deploy two identical Node.js services (Blue and Green) behind an Nginx load balancer with **automatic, health-based failover**, **zero client-side errors**, and **environment-driven configuration** — without modifying or rebuilding application images.

---

## 1. Design Objectives

1. **Zero-downtime routing**
   - Blue is the default active pool.
   - Green automatically takes over if Blue fails.
   - Client requests should always return `200`, even during failover.

2. **No image rebuilds**
   - The explicit forbids modifying or rebuilding application images.
   - All customization is achieved via environment variables and configuration.

3. **Parameterization**
   - The entire stack (images, ports, active pool, release IDs) are driven from a `.env` file.
   - This allows CI/CD pipelines to inject configuration dynamically.

4. **Observability**
   - All upstream headers (`X-App-Pool`, `X-Release-Id`) are preserved to verify correct routing and release identity.

---

## 2. Key Implementation Decisions

### a. **Nginx as Smart Proxy**
- Nginx was chosen to handle routing, retries, and health-based failover.
- The config uses:
  - `max_fails` and `fail_timeout` to mark an upstream as unhealthy.
  - `proxy_next_upstream error timeout http_500 http_502 http_503 http_504` to retry failed requests on the backup.
- `proxy_set_header` directives ensure app headers are preserved.

### b. **Primary/Backup Upstreams**
- Nginx upstream block defines two servers:
  ```nginx
  upstream app_backend {
      server app_blue:3000 max_fails=1 fail_timeout=3s;
      server app_green:3000 backup;
  }


- Blue is always primary.
- Green is marked as backup and becomes active automatically if Blue fails.

### c. **Health and Timeout Tuning**
- `proxy_connect_timeout, proxy_read_timeout`, and `fail_timeout` values are kept tight (1–3 seconds) to detect issues quickly.

- This ensures near-instantaneous failover during `/chaos/start`.

### d. **Dynamic Configuration via Template**
- A template file `nginx.conf.template` is used with `envsubst` to replace `$ACTIVE_POOL` and other environment variables.
- This avoids rebuilding images and supports switching Blue/Green via simple env updates.

### e. **Docker Compose Orchestration**
- `docker-compose.yml` manages all three services:
    - app_blue on port 8081
    - app_green on port 8082
    - nginx on port 8080

- The .env file drives configuration:
```bash
BLUE_IMAGE=
GREEN_IMAGE=
ACTIVE_POOL=
RELEASE_ID_BLUE=
RELEASE_ID_GREEN=
```

### b. **Entrypoint Script Design**
- The entrypoint script is executed before Nginx startup to:
    - Render the active config from the template using envsubst.
    - Print which pool is active.
    - Start Nginx in the foreground.
- The script is mounted at /nginx-entrypoint.sh to avoid permission issues.

---

---

## 3. Failover Verification Logic

| Scenerio | Expected Response | Nginx Behavior |
|-------|----------------|-----|
| Normal (Blue healthy) | 200 OK `X-App-Pool: blue`  | Requests routed to Blue |
| Chaos induced on Blue | 200 OK `X-App-Pool: green` | Automatic retry to Green |
| Blue recovers | 200 OK `X-App-Pool: blue` (after reload) | Can switch back via CI or manual env change |

---

## 4. **Conclusion**
- This implementation achieves:
    - Blue/Green zero-downtime switching
    - No rebuilds or code changes
    - Environment-driven flexibility
    - Fast, transparent failover

- It demonstrates a production-grade deployment strategy using minimal tools (Nginx + Compose) and sound DevOps principles.

---