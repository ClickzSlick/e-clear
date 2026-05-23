# Use a slim Python base — smaller than the default image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first
# This layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Copy static files if they exist inside app/
# (index.html is served from app/static/)

# Copy data files — this is the large layer
COPY data/ ./data/

# Copy env example (not the real .env — that's injected at runtime)
# We do NOT copy .env into the image for security

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]