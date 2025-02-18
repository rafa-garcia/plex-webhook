bind = "0.0.0.0:5000"
workers = 1
timeout = 30  # Allow more time for slow IMDb responses
loglevel = "info"  # Change to debug mode for more details
errorlog = "-"  # Log errors to stdout (Docker logs)
accesslog = "-"  # Log access requests to stdout
