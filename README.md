# Blue/Green Node.js App behind Nginx (Docker Compose)


## Overview
This repository composes two pre-built Node.js images (`BLUE_IMAGE` and `GREEN_IMAGE`) behind an Nginx reverse proxy that implements primary/backup semantics and per-request failover.


The Entry Points:
- Nginx available at: `http://localhost:8080`
- Blue app directly: `http://localhost:8081` (`/chaos/*` will be call here)
- Green app directly: `http://localhost:8082`


Both apps exposes these endpoints (already implemented inside the images):
- `GET /version` → returns JSON and includes headers `X-App-Pool` and `X-Release-Id`
- `POST /chaos/start` → simulate downtime
- `POST /chaos/stop` → end simulated downtime
- `GET /healthz` → liveness

## Files
- `docker-compose.yml` — defines `blue`, `green`, and `nginx` services
- `nginx.conf.template` — Nginx config template (uses envsubst)
- `nginx-entrypoint.sh` — renders template and starts nginx
- `.env.example` — environment variable examples


## Requirements
- Docker and Docker Compose
- `chmod +x nginx-entrypoint.sh` (one-time local step)


## Quick start
1. Copy `.env.example` to `.env` and set the image names and release ids.

2. Run:
   ```bash
   docker-compose up -d
   ```
3. Access via http://localhost:8080/version
4. Induce failure on Blue:
   ```bash
   curl -X POST "http://localhost:8081/chaos/start?mode=error"
   curl -X POST http://localhost:8081/chaos/start?mode=timeout
   ```
5. Verify failover to Green:
   ```bash
   curl -i http://localhost:8080/version
   ```

6. Stop chaos and return trafic to Blue:
   ```bash
   curl -X POST "http://localhost:8081/chaos/stop"
   ```

7.  Remove or Stop Containers
```bash
   docker compose down
   ```


## 💬 Author

**Kamil Balogun**  
DevOps / Cloud Engineer  
📧 kamilbalogun@hotmail.com  
🐙 GitHub: [dejimania](https://github.com/dejimania)