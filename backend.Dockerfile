# =============================================================================
# backend.Dockerfile — Python / Flask API
#
# Builds a production-ready container that runs the Flask app via Gunicorn.
# Gunicorn is a proper WSGI server (not Flask's built-in dev server), making
# it suitable for real traffic.
#
# Build context expected layout:
#   backend/
#     app.py            ← Flask application entry point
#     requirements.txt  ← Python dependencies
#     backend.Dockerfile
# =============================================================================

# Use the official slim Python 3.12 image as the base.
# "slim" strips optional OS packages, keeping the image ~50% smaller than the
# full "python:3.12" image without sacrificing anything we need.
FROM python:3.12-slim

# Set the working directory inside the container.
# All subsequent COPY, RUN, and CMD instructions operate relative to this path.
WORKDIR /app

# Copy requirements.txt first — before copying app.py.
# Docker builds each instruction as a cached layer. Because requirements.txt
# changes less often than app.py, this order means "pip install" is only re-run
# when requirements.txt actually changes, saving minutes on most rebuilds.
COPY requirements.txt .

# Install Python dependencies.
# "--no-cache-dir" tells pip not to store the download cache inside the image,
# which keeps the image size smaller.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application into the container.
# Placed AFTER pip install so a code-only change doesn't trigger a full reinstall.
COPY app.py .

# Document that the container listens on port 8080.
# EXPOSE is informational only — it does not publish the port to the host.
# The actual port mapping is done in docker-compose.yml (ports: "8080:8080").
EXPOSE 8080

# Start the Flask app using Gunicorn (production WSGI server).
#   --bind 0.0.0.0:8080   listen on all interfaces inside the container
#   --workers 2           two worker processes to handle concurrent requests
#   --timeout 60          kill a worker if it takes more than 60s to respond
#   app:app               module name : Flask application variable name
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "app:app"]
