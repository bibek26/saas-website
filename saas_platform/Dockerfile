# Use an official Python runtime as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project
COPY . .

# Collect static files (for production)
RUN python manage.py collectstatic --noinput

# Expose the port your app will run on
EXPOSE 8000

# Run the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]