#!/bin/bash
# start_dev.sh
# Unified script to start the local Supabase database and the Python backend

# 1. Start Supabase Database
sudo chmod 666 /var/run/docker.sock
echo "======================================"
echo "Starting Local Supabase Database..."
echo "======================================"
npx supabase start

if [ $? -ne 0 ]; then
    echo "Failed to start Supabase. Exiting."
    exit 1
fi

# 2. Start Python Backend
echo "======================================"
echo "Starting Python Backend (Uvicorn via Infisical)..."
echo "======================================"
cd server-python
source ../venv/bin/activate
infisical run --env=dev -- uvicorn main:app --host 0.0.0.0 --port 8000 --reload
