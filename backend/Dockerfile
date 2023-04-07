FROM debian:bullseye-slim


RUN apt update -y && apt upgrade -y
RUN apt install -y procps gcc make openssl git wget p7zip ruby ruby-etc perl ruby-dev libz-dev
#&& apk add build-base gcc musl-dev make openssl git wget jpeg-dev zlib-dev p7zip ruby ruby-etc perl \
#&& apk add --virtual .build-dependencies ruby-dev

#
# Python
#
RUN echo "**** install Python ****" \
&& apt install python3 python3-pip -y

#
# ZSteg
#
RUN echo "**** install zsteg ****" \
&& gem install zsteg

#
# Steghide
#
RUN echo "**** install Steghide ****" \
&& apt install steghide -y

#
# Outguess
#
RUN echo "**** install Outguess ****" \
&& apt install outguess -y

#
# ExifTool
#
RUN echo "**** install ExifTools ****" \
&& apt install libimage-exiftool-perl -y

#
# Binwalk
#
RUN echo "**** install Binwalk ****" \
&& apt install binwalk -y

#
# Foremost
#
RUN echo "**** install Foremost ****" \
&& apt install foremost -y

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
