FROM alpine:3.10
ARG EXIFTOOL_VERSION=11.93

#
# ZSteg
#

RUN apk update \
&& apk add build-base \
           ruby \
           ruby-etc \
&& apk add --virtual .build-dependencies \
           ruby-dev \
&& gem install zsteg --no-ri --no-rdoc


#
# Steghide
#

RUN apk add steghide --update-cache --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/ --allow-untrusted \
&& apk add p7zip

#
# ExifTool
#

RUN apk add --no-cache perl make openssl wget
RUN cd /tmp \
    && wget https://exiftool.org/Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz \
    && tar -zxvf Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz \
    && cd Image-ExifTool-${EXIFTOOL_VERSION} \
    && perl Makefile.PL \
    && make test \
    && make install \
    && cd .. \
    && rm -rf Image-ExifTool-${EXIFTOOL_VERSION}


#
# Flask
#


RUN echo "**** install Python ****" && \
    apk add --no-cache python3-dev && \
    if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python ; fi && \
    \
    echo "**** install pip ****" && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools wheel && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi

RUN apk add --no-cache gcc musl-dev jpeg-dev zlib-dev

#
# Binwalk
#

RUN apk add git
RUN cd /tmp && git clone https://github.com/ReFirmLabs/binwalk.git && cd binwalk && python3 setup.py install


WORKDIR /opt/aperisolve

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./app.py" ]
