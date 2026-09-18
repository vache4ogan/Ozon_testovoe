FROM python:3.10-slim

# Install system dependencies (zbar, opencv requirements)
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
# Ultralytics, opencv, pyzbar, etc.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY configs/ configs/
COPY app/ app/
COPY training/ training/
COPY tests/ tests/

# Set Python path so module imports work correctly
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Command to run the pipeline
CMD ["python", "-m", "app.pipeline", "--config", "configs/system.yaml"]
