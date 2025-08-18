# Dockerfile
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Run app
# CMD ["gunicorn", "Ecommerce.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD ["gunicorn", "Ecommerce.wsgi:application", "--bind", "0.0.0.0:8000"]
