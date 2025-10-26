FROM python:3.11-slim AS build

WORKDIR /

# Install dependencies
RUN apt-get update && apt-get install -y \
    zip \
    p7zip-full \
    binwalk \
    foremost \
    exiftool \
    steghide \
    ruby \
    binutils \
    outguess \
    pngcheck \
        redis-server \
    && gem install zsteg \
    && apt-get clean

COPY aperisolve/ /aperisolve/

RUN pip install --no-cache-dir -r /aperisolve/requirements.txt

# Bind to the platform-provided $PORT (fallback 5000 for local runs).
# Reduce worker count by default to fit free-tier memory.
# No redis-server needed; app runs synchronously when REDIS_URL is unset.
CMD ["bash", "-c", "gunicorn -w ${WORKERS:-2} -b 0.0.0.0:${PORT:-5000} aperisolve.wsgi:application"]
