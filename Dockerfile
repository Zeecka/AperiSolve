FROM python:3.14-slim AS build

WORKDIR /

# Install build tools and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    default-jdk \
    ruby \
    zip \
    7zip

# Install steganography and forensics tools
RUN apt-get update && apt-get install -y \
    binwalk \
    foremost \
    exiftool \
    steghide \
    binutils \
    outguess \
    pngcheck \
    && gem install zsteg

# Install OpenStego
RUN wget https://github.com/syvaidya/openstego/releases/download/openstego-0.8.6/openstego_0.8.6-1_all.deb -O /tmp/openstego.deb && \
    dpkg -i /tmp/openstego.deb && \
    rm /tmp/openstego.deb

# Copy application
COPY aperisolve/ /aperisolve/

RUN mkdir -p /data

# Install Python dependencies
RUN pip install --no-cache-dir -r /aperisolve/requirements.txt

ENV PYTHONUNBUFFERED=1

# Auto clean after build
RUN apt-get remove -y wget && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

CMD ["sh", "-c", "rm -rf /aperisolve/results/* && gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - --log-level info --capture-output aperisolve.wsgi:application"]
