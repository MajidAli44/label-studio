#!/bin/bash
# Azure App Service Startup Script
# This script runs when the container starts

echo "=========================================="
echo "Label Studio Azure Startup"
echo "=========================================="

# Set working directory
cd /label-studio

# Install additional requirements if needed
echo "Installing additional requirements..."
pip install --no-cache-dir -r requirements-azure.txt || true

# Run database migrations
echo "Running database migrations..."
python label_studio/manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python label_studio/manage.py collectstatic --noinput

# Create data directory if it doesn't exist
mkdir -p /home/labelstudio/data

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    label_studio.wsgi:application
