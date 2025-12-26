FROM python:3.14-slim AS build

WORKDIR /

# Install dependencies
RUN apt-get update && apt-get install -y \
    zip \
    7zip \
    binwalk \
    foremost \
    exiftool \
    steghide \
    ruby \
    binutils \
    outguess \
    pngcheck \
    && gem install zsteg \
    && apt-get clean

COPY aperisolve/ /aperisolve/

RUN mkdir -p /data

RUN pip install --no-cache-dir -r /aperisolve/requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--capture-output", "aperisolve.wsgi:application"]