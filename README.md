# Plex Webhook

A Flask-based webhook service that automatically updates Plex movie labels using IMDb keywords when new movies are added to your library.

## Features

- Automatically fetches IMDb keywords for new movies
- Updates Plex labels in the background using Celery
- RESTful API with standardized responses and prefixed endpoints
- Supports manual label updates via API
- Rate limiting for IMDb requests
- Comprehensive error handling and logging
- Docker support with environment variable configuration

## Configuration

The service is configured using environment variables. Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

### Required Environment Variables

- `PLEX_TOKEN`: Your Plex authentication token (required)
  - To find your token, see: [Finding your Plex auth token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

### Optional Environment Variables

- `PORT`: The port to run the webhook service on (default: 5000)
- `PLEX_URL`: Your Plex server URL (default: http://localhost:32400)
- `CELERY_BROKER_URL`: Redis URL for Celery broker (default: redis://localhost:6379/0)

## Docker Usage

1. Create your `.env` file with the required configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

2. Build and run with Docker:
   ```bash
   docker build -t plex-webhook .
   docker run -d \
     --env-file .env \
     -p 5000:5000 \
     --name plex-webhook \
     plex-webhook
   ```

### Docker Environment Variables

In addition to the standard environment variables, when running in Docker you can configure:

- `CELERY_BROKER_HOST`: Redis host (default: localhost)
- `CELERY_BROKER_PORT`: Redis port (default: 6379)

Examples:

Custom port:
```bash
docker run -d \
  --env-file .env \
  -e PORT=8080 \
  -p 8080:8080 \
  plex-webhook
```

Custom Redis connection:
```bash
docker run -d \
  --env-file .env \
  -e CELERY_BROKER_HOST=redis.example.com \
  -e CELERY_BROKER_PORT=6380 \
  -p 5000:5000 \
  plex-webhook
```

Note: When changing the port, make sure to match the container's exposed port (-p flag) with the PORT environment variable.

### Docker Image Details

The Docker image is optimized for minimal size:
- Multi-stage build process
- Uses Alpine Linux base image
- Includes only necessary runtime dependencies
- Proper process management with tini
- Built-in health checks for Redis

3. The webhook will be available at `http://your-server:5000/api/plex-webhook`

## API Endpoints

### POST /api/plex-webhook
Handles Plex webhook events for new movies. Configure this URL in your Plex settings.

### POST /api/update-labels/{rating_key}
Manually trigger label updates for a specific movie.

Request body:
```json
{
    "imdb_id": "tt0111161"
}
```

### GET /api/health
Health check endpoint that verifies service status. Returns:
```json
{
    "status": "success",
    "message": "All services operational",
    "timestamp": "2025-02-20T12:19:35.123456Z",
    "services": {
        "celery": {
            "status": "connected",
            "message": "Connected to Redis successfully"
        },
        "plex": {
            "status": "connected",
            "message": "Connected to Plex server successfully"
        }
    }
}
```

The endpoint checks:
- Celery/Redis connection status
- Plex server connectivity and token validity

Returns 200 if all services are healthy, 500 if any service is unhealthy.

## Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run the service:
   ```bash
   python -m src.app
   ```

## Logging

All application logs are written to `logs/app.log` using a rotating file handler:
- Maximum file size: 10MB
- Keeps 5 backup files
- JSON-formatted log entries with timestamps
- Includes structured data for better debugging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

Example log entry:
```json
{
    "event": "health_check",
    "timestamp": "2025-02-20T12:48:12.123456Z",
    "data": {
        "status": "healthy",
        "services": {
            "celery": {"status": "connected"},
            "plex": {"status": "connected"}
        }
    }
}
```

## Testing

The project includes comprehensive test coverage using pytest. To run the tests:

```bash
# From the project root directory, run:
python -m pytest

# For coverage reporting:
python -m pytest --cov=src

# Generate HTML coverage report
python -m pytest --cov=src --cov-report=html
```

Test files are located in the `tests/` directory and mirror the structure of the `src/` directory:
- `test_app.py`: Tests for Flask routes and application logic
- `test_imdb.py`: Tests for IMDb integration
- `test_plex.py`: Tests for Plex API interactions  
- `test_tasks.py`: Tests for Celery tasks
- `test_utils.py`: Tests for utility functions

Tests include:
- Unit tests for individual functions
- Integration tests for module interactions
- Mocking of external services
- Error case testing

## Error Handling

The service includes comprehensive error handling:
- Rate limiting for IMDb requests
- Automatic retries for failed tasks
- Detailed error logging
- Input validation
- Sanitization of metadata
- Standardized error responses across all endpoints

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
