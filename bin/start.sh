#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

# Function to check if Redis is ready
check_redis() {
    nc -z ${CELERY_BROKER_HOST:-localhost} ${CELERY_BROKER_PORT:-6379}
}

# Wait for Redis with timeout
echo "Waiting for Redis..."
TIMEOUT=30
COUNT=0
until check_redis || [ $COUNT -eq $TIMEOUT ]; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $((COUNT%5)) -eq 0 ]; then
        echo "Still waiting for Redis... ($COUNT/$TIMEOUT)"
    fi
done

if [ $COUNT -eq $TIMEOUT ]; then
    echo "Redis did not become available in time"
    exit 1
fi
echo "Redis is ready!"

# Create required directories
mkdir -p ./logs

# Start Gunicorn in the background with proper error handling
echo "Starting Gunicorn..."
gunicorn -c config/gunicorn_config.py src.app:app &
GUNICORN_PID=$!

# Start Celery worker in the background with proper error handling
echo "Starting Celery worker..."
celery -A src.tasks worker --loglevel=info &
CELERY_PID=$!

# Function to cleanup processes
cleanup() {
    echo "Shutting down services..."
    kill -TERM $GUNICORN_PID 2>/dev/null
    kill -TERM $CELERY_PID 2>/dev/null
    wait $GUNICORN_PID 2>/dev/null
    wait $CELERY_PID 2>/dev/null
    exit 0
}

# Setup signal handling
trap cleanup SIGTERM SIGINT

# Monitor child processes
while true; do
    # Check if either process has died
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then
        echo "Gunicorn process died"
        cleanup
        exit 1
    fi
    if ! kill -0 $CELERY_PID 2>/dev/null; then
        echo "Celery process died"
        cleanup
        exit 1
    fi
    sleep 5
done
