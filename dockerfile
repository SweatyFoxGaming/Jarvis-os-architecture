FROM python:3.11-slim

# Install only essential packages, no build tools unless needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libportaudio2 \
    portaudio19-dev \
    espeak \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Allow git to work inside the container
RUN git config --global --add safe.directory /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["python3", "-m", "src.api"]
