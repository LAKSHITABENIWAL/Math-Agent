FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# copy only requirements first for caching
COPY requirements.txt /app/requirements.txt

# small system deps often needed (git for some pip installs, build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git curl && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt && \
    apt-get purge -y --auto-remove build-essential && \
    rm -rf /var/lib/apt/lists/*

# copy the app code
COPY . /app

# Expose the port Uvicorn will use
EXPOSE 5000

# Run uvicorn on FastAPI app (adjust module:app if needed)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
