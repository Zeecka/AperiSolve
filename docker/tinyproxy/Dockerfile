# Minimal forward proxy for the Sentry SDK only (ZEL-442, decision D1).
#
# worker/cron sit on the `backend` network (internal: true, no egress) and
# reach this proxy to keep Sentry reporting; this service straddles
# `frontend`+`backend` and is the only thing in the stack allowed to dial out,
# and only to the Sentry ingest host parsed from SENTRY_DSN at startup
# (entrypoint.sh). A popped analyzer tool in worker therefore has no route to
# the internet at all, even through this proxy.
FROM alpine:3.21

## The tinyproxy package provisions its own "tinyproxy" user/group.
RUN apk add --no-cache tinyproxy

COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && chown tinyproxy:tinyproxy /etc/tinyproxy/tinyproxy.conf

USER tinyproxy
EXPOSE 8888
ENTRYPOINT ["/entrypoint.sh"]
