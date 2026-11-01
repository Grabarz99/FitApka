#!/bin/bash
# Start script dla Render.com
export FLET_APP_STORAGE_DATA="/tmp/fitapp_data"
mkdir -p "$FLET_APP_STORAGE_DATA"
flet run main.py --web --port ${PORT:-10000} --host 0.0.0.0