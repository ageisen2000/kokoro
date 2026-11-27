# syntax=docker/dockerfile:1
#
# Custom kokoro image for Home Assistant (Wyoming protocol).
# Baseline: nordwestt/kokoro-wyoming cuda-1.0.2 (pinned by digest),
# which bakes in the Kokoro-82M model + voices and the NVIDIA CUDA runtime.
# We extend that with small operational additions and no source code.

FROM nordwestt/kokoro-wyoming:cuda-1.0.2@sha256:128f9779cd7311382d2c51f1b54d6c50a37a44f831399ed3144cf919348ed961

LABEL org.opencontainers.image.title="kokoro" \
      org.opencontainers.image.description="Home Assistant Wyoming-protocol TTS server (Kokoro-82M) with NVIDIA CUDA" \
      org.opencontainers.image.source="https://github.com/ageisen2000/kokoro" \
      org.opencontainers.image.vendor="ageisen2000" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="nordwestt/kokoro-wyoming:cuda-1.0.2"

EXPOSE 10210

# The base image runs as its default user and binds tcp://0.0.0.0:10210.
# A plain TCP handshake against the listen port is the health signal.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD /usr/bin/python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('127.0.0.1',10210)); s.close()" || exit 1

# Do not override ENTRYPOINT/CMD: the base image runs `/usr/bin/python3 /app/src/main.py`.
# Default args are the base image's own; pass `--uri tcp://0.0.0.0:10210` at runtime.
