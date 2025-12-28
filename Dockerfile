FROM python:3.14-slim AS build

WORKDIR /

# Install build tools and dependencies


RUN apt-get update && apt-get install -y --no-install-recommends \
    wget default-jre ruby \
    bzip2 xz-utils gzip lzip lzma lzop tar unzip p7zip-full squashfs-tools \
    file qpdf cpio arj cabextract sharutils lz4 ccache mtd-utils \
    python3-lxml upx-ucl zlib1g-dev liblzma-dev \
    binwalk foremost exiftool steghide binutils outguess pngcheck \
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

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--capture-output", "aperisolve.wsgi:application"]
