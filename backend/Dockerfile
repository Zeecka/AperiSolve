FROM alpine:3.12

ARG EXIFTOOL_VERSION=12.51

RUN apk update \
&& apk add build-base gcc musl-dev make openssl git wget jpeg-dev zlib-dev p7zip ruby ruby-etc perl \
&& apk add --virtual .build-dependencies ruby-dev

#
# Python
#
RUN echo "**** install Python ****" \
&& apk add python3-dev \
&& if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python ; fi \
&& echo "**** install pip ****" \
&& python3 -m ensurepip \
&& rm -r /usr/lib/python*/ensurepip \
&& pip3 install --upgrade pip setuptools wheel \
&& if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi

#
# ZSteg
#
RUN echo "**** install zsteg ****" \
&& gem install zsteg

#
# Steghide
#
RUN echo "**** install Steghide ****" \
&& apk add steghide --update-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/ --allow-untrusted

#
# Outguess
#
RUN echo "**** install Outguess ****" \
&& cd /tmp \
&& git clone https://github.com/crorvick/outguess.git \
&& cd outguess \
&& ./configure \
&& make && make install -i

#
# ExifTool
#
RUN echo "**** install ExifTools ****" \
&& cd /tmp \
&& wget https://exiftool.org/Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz \
&& tar -zxvf Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz \
&& cd Image-ExifTool-${EXIFTOOL_VERSION} \
&& perl Makefile.PL \
&& make test && make install

#
# Binwalk
#
RUN echo "**** install Binwalk ****" \
&& cd /tmp \
&& git clone https://github.com/ReFirmLabs/binwalk.git \
&& cd binwalk \
&& python3 setup.py install

#
# Foremost
#
RUN echo "**** install Foremost ****" \
&& cd /tmp \
&& git clone https://github.com/jonstewart/foremost.git \
&& cd foremost \
&& make && make install

#
# PCRT
#
RUN echo "**** install PCRT ****" \
&& cd /usr/bin \
&& wget https://raw.githubusercontent.com/Zeecka/PCRT/AperiSolve/PCRT.py \
&& mv PCRT.py PCRT \
&& chmod +x PCRT

#
# PngCheck
#
RUN echo "**** install PngCheck ****" \
&& cd /tmp \
&& wget http://libpng.org/pub/png/src/pngcheck-3.0.3.zip \
&& unzip pngcheck-3.0.3.zip \
&& mv Makefile.unx Makefile \
&& make \
&& mv pngcheck /usr/bin/

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ./start.sh
