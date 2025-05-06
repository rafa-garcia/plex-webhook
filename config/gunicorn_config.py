from config import settings

# Bind to the port from environment variable
bind = f"0.0.0.0:{settings.PORT}"

# Worker configuration
workers = 1  # Single worker since we use Celery for background tasks
worker_class = "sync"
timeout = 30  # Allow more time for slow IMDb responses

# Logging configuration
loglevel = "info"  # Change to debug for more details
errorlog = "-"  # Log errors to stdout (Docker logs)
accesslog = "-"  # Log access requests to stdout

# Security settings
limit_request_line = 4094  # Limit request line size
limit_request_fields = 100  # Limit number of header fields
limit_request_field_size = 8190  # Limit header field sizes
