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

CMD ["bash", "-c", "redis-server & gunicorn -w 4 -b 0.0.0.0:5000 aperisolve.wsgi:application"]
