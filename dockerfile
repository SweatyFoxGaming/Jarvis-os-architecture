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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn","src.api:app","--host","0.0.0.0","--port","8000"]
