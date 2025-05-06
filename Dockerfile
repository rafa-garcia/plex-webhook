# Stage 1: Build dependencies
FROM python:3.13-alpine AS builder

WORKDIR /app

# Install dependencies needed for building wheels
RUN apk add --no-cache gcc musl-dev libffi-dev

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --root-user-action=ignore --prefix=/install -r requirements.txt

# Stage 2: Final minimal image
FROM python:3.13-alpine

WORKDIR /app

# Install tini to handle multiple processes properly
RUN apk add --no-cache tini

# Copy only installed dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy application files
COPY . /app/

# Ensure scripts have execution permission
RUN chmod +x /app/bin/start.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    DOCKER_ENV=true

# Expose Flask port (can be overridden at runtime)
EXPOSE ${PORT:-5000}

# Use tini as the entrypoint to properly handle process signals
ENTRYPOINT ["/sbin/tini", "--"]

# Start both Gunicorn and Celery using start.sh
CMD ["/app/bin/start.sh"]
