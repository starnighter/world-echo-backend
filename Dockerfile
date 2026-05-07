FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir "setuptools>=68" wheel \
    && pip install --no-cache-dir --no-build-isolation ".[essentia]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
