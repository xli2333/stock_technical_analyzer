# Base image with Python 3.12
FROM python:3.12-slim

# Install system dependencies
# - fonts-wqy-microhei: Chinese font for PDF generation
# - gcc, libc-dev: Build tools for some python packages if wheels are missing
# - libta-lib0: Run-time TA-Lib dependency (optional if using manylinux wheels, but safe to have)
RUN apt-get update && apt-get install -y \
    fonts-wqy-microhei \
    fontconfig \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port (Render sets the PORT env var, default is 10000)
EXPOSE 10000

# Run the application with Gunicorn
# Listen on 0.0.0.0 with the port defined in environment variable
# Increase timeout to 120s to allow for slow data fetching
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 120 web_app:app
