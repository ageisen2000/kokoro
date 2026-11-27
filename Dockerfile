# syntax=docker/dockerfile:1
#
# Custom kokoro image for Home Assistant — built from the official Python base.
#
# Baseline components (all publicly available): the public Kokoro-82M model
# files baked in with checksum verification, plus the public kokoro-onnx /
# wyoming / numpy packages. No third-party container image is used as a base.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Baked, checksum-verified Kokoro-82M model + voices (public weights).
ADD --checksum=sha256:7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5 \
      https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx \
      /app/kokoro-v1.0.onnx
ADD --checksum=sha256:bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d \
      https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin \
      /app/voices-v1.0.bin

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/

LABEL org.opencontainers.image.title="kokoro" \
      org.opencontainers.image.description="Home Assistant Wyoming-protocol TTS server (Kokoro-82M) with NVIDIA CUDA" \
      org.opencontainers.image.source="https://github.com/ageisen2000/kokoro" \
      org.opencontainers.image.vendor="ageisen2000" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="python:3.12-slim"

EXPOSE 10210

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD /usr/local/bin/python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('127.0.0.1',10210)); s.close()" || exit 1

ENTRYPOINT ["/usr/local/bin/python3", "main.py"]
CMD ["--uri", "tcp://0.0.0.0:10210"]
