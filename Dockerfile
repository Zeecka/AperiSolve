FROM alpine:3.10
ARG EXIFTOOL_VERSION=11.93


RUN apk update \
&& apk add build-base gcc musl-dev make openssl git wget jpeg-dev zlib-dev p7zip ruby ruby-etc perl \
&& apk add --virtual .build-dependencies ruby-dev


#
# Flask
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
&& gem install zsteg --no-ri --no-rdoc

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
# Aperi'Solve
#
RUN echo "**** install Aperi'Solve ****" \
&& cd /opt \
&& git clone https://github.com/Zeecka/AperiSolve.git \
&& cd AperiSolve/data \
&& pip install --no-cache-dir -r requirements.txt


WORKDIR /opt/AperiSolve/data
CMD [ "python", "./app.py" ]
