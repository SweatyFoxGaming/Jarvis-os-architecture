FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libportaudio2 \
    portaudio19-dev \
    espeak \
    git \
    && rm -rf /var/lib/apt/lists/*

# Allow git to work inside the container when /app is mounted from host
RUN git config --global --add safe.directory /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["python3", "-m", "src.api"]
