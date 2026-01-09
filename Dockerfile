# ==========================
# Stage 1 : Builder (download OpenStego)
# ==========================
FROM python:3.14-slim AS builder

# Install wget only to download OpenStego
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download OpenStego
RUN wget https://github.com/syvaidya/openstego/releases/download/openstego-0.8.6/openstego_0.8.6-1_all.deb \
    -O /tmp/openstego.deb

# ==========================
# Stage 2 : Image runtime minimale
# ==========================
FROM python:3.14-slim

WORKDIR /app

# Install runtime + stego tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre \
    file \
    ruby \
    zip \
    p7zip-full \
    binwalk \
    foremost \
    exiftool \
    steghide \
    binutils \
    outguess \
    pngcheck \
    && gem install zsteg \
    && rm -rf /var/lib/apt/lists/*

# Install OpenStego
COPY --from=builder /tmp/openstego.deb /tmp/openstego.deb
RUN dpkg -i /tmp/openstego.deb || apt-get install -f -y --no-install-recommends \
    && rm -rf /tmp/openstego.deb \
    && rm -rf /var/lib/apt/lists/*

# Copy app
COPY aperisolve/ /app/aperisolve/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/aperisolve/requirements.txt

# Commande de lancement
CMD ["gunicorn", "-w", "8", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "--capture-output", "aperisolve.utils.wsgi:application"]
