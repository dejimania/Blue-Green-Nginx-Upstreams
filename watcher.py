#!/usr/bin/env python3
"""watcher.py

Log watcher script

Tails the nginx JSON access log and sends Slack alerts on:
 - Failover events (pool change)
 - Elevated 5xx error rate over a sliding window

Configuration via environment variables:
 - SLACK_WEBHOOK_URL
 - WINDOW_SIZE (default 200)
 - ERROR_RATE_THRESHOLD (percent, default 2)
 - ALERT_COOLDOWN_SEC (default 300)
 - MAINTENANCE_MODE (optional: '1' to suppress alerts)
"""

import os
import time
import json
import requests
from collections import deque, Counter
from datetime import datetime, timedelta

LOG_PATH = os.environ.get('NGINX_LOG_PATH', '/var/log/nginx/access.log')
SLACK_WEBHOOK = os.environ.get('SLACK_WEBHOOK_URL')
WINDOW_SIZE = int(os.environ.get('WINDOW_SIZE', '200'))
ERROR_RATE_THRESHOLD = float(os.environ.get('ERROR_RATE_THRESHOLD', '2.0'))
ALERT_COOLDOWN = int(os.environ.get('ALERT_COOLDOWN_SEC', '300'))
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', '0') == '1'

def send_slack(msg):
    if not SLACK_WEBHOOK:
        print("No SLACK_WEBHOOK_URL configured; would send:\n", msg)
        return
    payload = {"text": msg}
    try:
        r = requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print("Failed to send Slack message:", e)

def tail(f):
    f.seek(0,2)
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def parse_line(line):
    try:
        return json.loads(line)
    except Exception as e:
        return None

def format_alert(title, details):
    ts = datetime.utcnow().isoformat() + 'Z'
    return f"[{ts}] *{title}*\n{details}"

def main():
    last_pool = None
    last_alert_time = {}
    window = deque(maxlen=WINDOW_SIZE)
    counts = Counter()

    # Wait until log exists
    while not os.path.exists(LOG_PATH):
        print(f"Waiting for log file {LOG_PATH}...")
        time.sleep(0.5)

    with open(LOG_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        for line in tail(f):
            if MAINTENANCE_MODE:
                continue
            data = parse_line(line.strip())
            if not data:
                continue

            pool = data.get('pool') or 'unknown'
            status = int(data.get('status') or 0)
            upstream_status = data.get('upstream_status') or ''
            upstream_addr = data.get('upstream_addr') or ''
            release = data.get('release') or ''

            # Detect pool flip
            if last_pool and pool != last_pool:
                now = time.time()
                # flip via cooldown
                key = f'flip_{last_pool}_to_{pool}'
                last = last_alert_time.get(key, 0)
                if now - last > ALERT_COOLDOWN:
                    msg = format_alert('Failover detected', f"{last_pool} -> {pool} | release={release} | upstream_status={upstream_status} | upstream={upstream_addr}")
                    send_slack(msg)
                    last_alert_time[key] = now

            last_pool = pool

            # Update sliding window
            is_5xx = 500 <= status < 600
            window.append(1 if is_5xx else 0)
            counts['total'] = len(window)
            counts['5xx'] = sum(window)

            # Check error rate
            if counts['total'] >= max(10, WINDOW_SIZE//10):
                err_rate = (counts['5xx'] / counts['total'])*100.0 if counts['total'] else 0.0
                key = 'error_rate'
                now = time.time()
                last = last_alert_time.get(key, 0)
                if err_rate >= ERROR_RATE_THRESHOLD and now - last > ALERT_COOLDOWN:
                    msg = format_alert('Elevated 5xx error rate', f"{err_rate:.2f}% 5xx over last {counts['total']} requests (threshold {ERROR_RATE_THRESHOLD}%)")
                    send_slack(msg)
                    last_alert_time[key] = now

if __name__ == '__main__':
    main()
