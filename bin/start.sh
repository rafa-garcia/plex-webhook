#!/bin/sh
set -e  # Exit immediately if a command exits with a non-zero status

# Wait for Redis to be available
echo "Waiting for Redis..."
while ! nc -z localhost 6379; do
    sleep 1
done
echo "Redis is ready!"

# Start Gunicorn in the background
echo "Starting Gunicorn..."
gunicorn -c config/gunicorn_config.py src.app:app &

# Start Celery worker in the foreground (keeps the container alive)
echo "Starting Celery worker..."
exec celery -A src.tasks worker --loglevel=info
