#!/usr/bin/env sh
set -e


# Defaults
: "${ACTIVE_POOL:=blue}"
: "${PORT:=8080}"

# Compute backup tokens (leading space when present, empty otherwise)
if [ "$ACTIVE_POOL" = "blue" ]; then
    BLUE_BACKUP=""
    GREEN_BACKUP=" backup"
else
    BLUE_BACKUP=" backup"
    GREEN_BACKUP=""
fi


export PORT
export BLUE_BACKUP
export GREEN_BACKUP

# Ensure log dir exists and permissions
mkdir -p /var/log/nginx
chown -R nginx:nginx /var/log/nginx || true

# Render template
envsubst '$PORT $BLUE_BACKUP $GREEN_BACKUP' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf


# Start nginx (foreground)
nginx -g 'daemon off;'