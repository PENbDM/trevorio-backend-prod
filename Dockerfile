
FROM python:3.13-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Collect Django static files during image build
RUN DJANGO_SETTINGS_MODULE=trevorio.settings_build \
    python manage.py collectstatic --noinput

# Create a non-root user and grant permissions
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

# Run Django and Celery as a non-root user
USER appuser

EXPOSE 8000

CMD ["gunicorn", "trevorio.asgi:application", "--worker-class", "asgi", "--bind", "0.0.0.0:8000"]
