#!/bin/sh
# Allow-list exactly the Sentry ingest host parsed from SENTRY_DSN, then run
# tinyproxy in the foreground (-d) so it stays PID 1. An empty/unset DSN
# leaves the filter list empty -- FilterDefaultDeny in tinyproxy.conf then
# denies every request, so a misconfiguration fails closed, not open.
set -eu

FILTER_FILE=/tmp/sentry-filter.list
: > "$FILTER_FILE"

if [ -n "${SENTRY_DSN:-}" ]; then
    host=$(printf '%s' "$SENTRY_DSN" | sed -n 's#^https\?://[^@/]*@\([^/]*\).*#\1#p')
    if [ -n "$host" ]; then
        printf '%s\n' "$host" >> "$FILTER_FILE"
    fi
fi

exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf
