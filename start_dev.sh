#!/bin/bash
# start_dev.sh
# Unified script to start the Python backend (connected to Supabase Cloud)

# 1. Start Python Backend
echo "======================================"
echo "Starting Python Backend (Uvicorn via Infisical)..."
echo "======================================"
cd server-python
source ../venv/bin/activate

infisical run --env=dev -- uvicorn main:app --host 0.0.0.0 --port 8000 --reload

