# Production Guide: chipchip.ermiopia.com

This guide shows how to deploy the MVP to a VPS with Docker Compose and a host-level Nginx (installed on the VPS). Nginx will serve the Next.js frontend at `/` and proxy backend routes (`/api`, `/socket.io`, `/static`) to FastAPI. We will not run Nginx in Docker, to match your existing server setup.

## Prerequisites
- Linux VPS (Ubuntu 20.04+ recommended)
- Docker 24+ and Docker Compose v2
- A domain `chipchip.ermiopia.com` pointing (A record) to your VPS public IP
- Optional: SSH access from GitHub Actions for CI/CD

## 1) Clone and prepare environment
```
ssh <user>@<vps-ip>
sudo mkdir -p /opt/chipchip && sudo chown -R $USER:$USER /opt/chipchip
cd /opt/chipchip
git clone <your-repo-url> .

# Copy and edit environment
cp .env.example .env
vi .env
# Set at minimum:
#   GEMINI_API_KEY=<your_ai_studio_or_gemini_key>
# Optional logging toggles:
#   LOG_LEVEL=INFO
#   LOG_JSON=1
#   TRACE_TOOLS=0

# Set public backend URL used by the frontend build (same domain via Nginx)
echo "NEXT_PUBLIC_BACKEND_URL=https://chipchip.ermiopia.com" >> .env
```

Why set `NEXT_PUBLIC_BACKEND_URL`? The frontend uses it to call the backend in the browser (e.g., `fetch(<NEXT_PUBLIC_BACKEND_URL>/api/...)`). With Nginx, both frontend and backend live under the same domain, so this should be the full public base URL.

## 2) Build and start (HTTP only)
```
docker compose -f docker-compose.prod.yml up -d --build
```

Services (host ports):
- `frontend` (Next.js) exposed on host `3005` (container `3000`)
- `backend` (FastAPI) exposed on host `8005` (container `8000`)
- `postgres` (5432 → host 5432), `redis` (6379 → host 6379), `chroma` (8000 → host 8001) as dependencies

Verify:
- http://chipchip.ermiopia.com → frontend
- http://chipchip.ermiopia.com/api/sessions (POST) → backend
- http://chipchip.ermiopia.com/health (frontend 404 is expected; backend health is under `/api/health` if added)

## 3) Configure host Nginx
Create a site config at `/etc/nginx/sites-available/chipchip`:

```
server {
    listen 80;
    server_name chipchip.ermiopia.com;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8005/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSockets (Socket.IO)
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8005/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files served by backend (generated images)
    location /static/ {
        proxy_pass http://127.0.0.1:8005/static/;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
}
```

Enable the site and reload Nginx:
```
sudo ln -s /etc/nginx/sites-available/chipchip /etc/nginx/sites-enabled/chipchip
sudo nginx -t
sudo systemctl reload nginx
```

## 4) Initialize data (first-time only)
```
docker compose -f docker-compose.prod.yml exec backend python scripts/init_db.py
docker compose -f docker-compose.prod.yml exec backend python scripts/load_dataset.py
```

## 5) Optional: Enable HTTPS with Let’s Encrypt (host-level)
Simplest path (host-level install):
```
sudo apt update && sudo apt install -y certbot
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Obtain certificate (standalone HTTP challenge; temporarily stop any service bound to :80)
sudo certbot certonly --standalone -d chipchip.ermiopia.com --agree-tos -m you@example.com --non-interactive

# Certificates at: /etc/letsencrypt/live/chipchip.ermiopia.com/
# Update your Nginx site to listen 443 with ssl_certificate/ssl_certificate_key and reload Nginx.
```

For production hardening, you can maintain a dedicated Nginx reverse proxy on the host or extend the container config with TLS. This guide keeps HTTP simple for MVP; add TLS when ready.

## 6) Environment variables reference
- `.env` (read by backend and compose):
  - `GEMINI_API_KEY` (required)
  - `DATABASE_URL`, `REDIS_URL`, `CHROMA_HOST`, `CHROMA_PORT` (defaults work with Compose services)
  - `LOG_LEVEL`, `LOG_JSON`, `TRACE_TOOLS`, `DB_ECHO` (optional)
- `NEXT_PUBLIC_BACKEND_URL` (read by frontend at build time):
  - Set in `.env` as shown above to `https://chipchip.ermiopia.com`.

## 7) CI/CD: Auto-deploy on push to main
This approach builds and deploys on the VPS via SSH using GitHub Actions. It pulls the latest code and rebuilds containers on the server, avoiding the need for a container registry.

Steps:
1. Create SSH key for GitHub Actions to access your VPS (no passphrase):
   - `ssh-keygen -t ed25519 -C "gh-actions@chipchip"`
   - Add the public key to the VPS: `~/.ssh/authorized_keys` for your deploy user
2. Add GitHub repo secrets:
   - `VPS_HOST` = your VPS IP or hostname
   - `VPS_USER` = deploy username (must have Docker permissions)
   - `VPS_SSH_KEY` = contents of the private key generated above
3. Ensure `.env` on the VPS has the correct values (GEMINI_API_KEY, NEXT_PUBLIC_BACKEND_URL, etc.)
4. Add a GitHub Actions workflow in your repo (example below) to deploy on `main` pushes.

Example `.github/workflows/deploy.yml`:
```yaml
name: Deploy to VPS
on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout (no code needed locally)
        uses: actions/checkout@v4

      - name: Deploy over SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            set -e
            cd /opt/chipchip
            git fetch origin main
            git checkout main
            git pull --rebase origin main
            # Build and restart services
            docker compose -f docker-compose.prod.yml up -d --build
            # Optional: prune old images
            docker image prune -f
```

Notes:
- The workflow assumes the code is already cloned at `/opt/chipchip` on the VPS.
- `.env` stays on the VPS and is not committed to git.
- If you prefer pushing images to a registry (GHCR) instead of building on the VPS, replace the SSH step with `docker buildx` + `docker push`, and remotely `docker compose pull && up -d`.

## 8) Operations
- Restart a single service: `docker compose -f docker-compose.prod.yml restart backend`
- Tail backend logs: `docker compose -f docker-compose.prod.yml logs -f backend`
- Update environment:
  - Edit `.env`
  - Rebuild affected services: `docker compose -f docker-compose.prod.yml up -d --build frontend backend`

## 9) Troubleshooting
- 502/Bad Gateway:
  - Check container health: `docker compose -f docker-compose.prod.yml ps`
  - Check Nginx logs: `docker compose -f docker-compose.prod.yml logs -f nginx`
- Frontend can’t reach backend:
  - Ensure `NEXT_PUBLIC_BACKEND_URL` is set to `https://chipchip.ermiopia.com` and rebuild frontend
  - Confirm Nginx `/api` and `/socket.io` routes proxy properly
- WebSockets not connecting:
  - Confirm Nginx `Upgrade`/`Connection` headers in `deploy/nginx/nginx.conf`
