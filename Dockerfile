FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=models/product_category_classifier.keras \
    METADATA_PATH=models/model_metadata.json

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir python-multipart

RUN adduser --disabled-password --gecos '' appuser

COPY ./app /app/app
COPY ./models /app/models

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Perintah yang dijalankan ketika container hidup
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
