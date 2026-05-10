FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "setuptools>=68" wheel \
    && pip install --no-cache-dir --no-build-isolation ".[essentia]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
