#!/usr/bin/env bash
set -euo pipefail
export PI_BACKUP_HOST=${PI_BACKUP_HOST:-0.0.0.0}
export PI_BACKUP_PORT=${PI_BACKUP_PORT:-8080}
exec uvicorn app.main:app --host "$PI_BACKUP_HOST" --port "$PI_BACKUP_PORT"
