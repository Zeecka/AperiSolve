# ==========================
# Stage 1 : Builder (download OpenStego)
# ==========================
FROM python:3.14-slim AS builder

# Install wget only to download OpenStego
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget git build-essential golang-go \
    && rm -rf /var/lib/apt/lists/*

# Download OpenStego
RUN wget https://github.com/syvaidya/openstego/releases/download/openstego-0.8.6/openstego_0.8.6-1_all.deb \
    -O /tmp/openstego.deb

# Clone and build jsteg from source
RUN git clone https://github.com/lukechampine/jsteg.git /tmp/jsteg
RUN cd /tmp/jsteg && \
    go build -o /usr/local/bin/jsteg ./cmd/jsteg && \
    rm -rf /tmp/jsteg

# Builder stage - add after other tool compilations
RUN git clone https://github.com/h3xx/jphs.git /tmp/jphs
RUN cd /tmp/jphs/jpeg-8a && ./configure && make
RUN cd /tmp/jphs && sed -i 's/open(seekfilename,O_WRONLY|O_TRUNC|O_CREAT)/open(seekfilename,O_WRONLY|O_TRUNC|O_CREAT, 0644)/' jpseek.c
RUN cd /tmp/jphs \
    && sed -i 's/^LIBS = .*/JPEG_OBJS = $(filter-out jpeg-8a\/cjpeg.o jpeg-8a\/djpeg.o jpeg-8a\/jpegtran.o jpeg-8a\/rdjpgcom.o jpeg-8a\/wrjpgcom.o,$(wildcard jpeg-8a\/\*.o))/' Makefile \
    && sed -i 's/^LDFLAGS = .*/LDFLAGS =/' Makefile \
    && sed -i 's/^jphide: \(.*\)$/jphide: \1 $(JPEG_OBJS)/' Makefile \
    && sed -i 's/^jpseek: \(.*\)$/jpseek: \1 $(JPEG_OBJS)/' Makefile
RUN cd /tmp/jphs && make all
RUN cd /tmp/jphs && cp jphide jpseek /usr/local/bin/
RUN rm -rf /tmp/jphs

# ==========================
# Stage 2 : Image runtime minimale
# ==========================
FROM python:3.14-slim

WORKDIR /app

# Install runtime + stego tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    expect \
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
    graphicsmagick \
    graphicsmagick-imagemagick-compat \
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

# Copy jphide and jsteg binaries
COPY --from=builder /usr/local/bin/jphide /usr/local/bin/jphide
COPY --from=builder /usr/local/bin/jpseek /usr/local/bin/jpseek
COPY --from=builder /usr/local/bin/jsteg /usr/local/bin/jsteg

# Commande de lancement
CMD gunicorn -w ${WEB_WORKERS:-8} -b 0.0.0.0:5000 --access-logfile - --error-logfile - --log-level info --capture-output aperisolve.utils.wsgi:application
