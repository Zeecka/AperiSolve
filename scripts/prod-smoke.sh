#!/bin/sh
# Post-deploy smoke test of a running Aperi'Solve instance.
#
#   scripts/prod-smoke.sh <version> [base-url]
#
# Checks, in order:
#   1. the home page shows "v.<version>";
#   2. MCP `initialize` on /mcp answers with serverInfo.version == <version>;
#   3. a fresh random PNG goes through /upload -> /status -> /result.
# The whole set is retried 3 times, 60 s apart: Cloudflare in front of prod
# has been seen to drop connections for minutes at a time, and one failed
# curl is not a down site. Exit 0 only if every check passed in one attempt.
set -u

VERSION=${1:?usage: prod-smoke.sh <version> [base-url]}
BASE=${2:-https://www.aperisolve.com}
TRIES=${SMOKE_TRIES:-3}
WAIT=${SMOKE_WAIT:-60}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/prod-smoke.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM

c() { curl -4 -sS -m 30 -A curl/8.5.0 "$@"; }

check_home() {
    c "$BASE/" -o "$WORK/home.html" || return 1
    if grep -q "v\.$VERSION\b" "$WORK/home.html"; then
        echo "ok   home shows v.$VERSION"
    else
        echo "FAIL home shows $(grep -o 'v\.[0-9][0-9.]*' "$WORK/home.html" | head -1), want v.$VERSION"
        return 1
    fi
}

check_mcp() {
    c -X POST "$BASE/mcp" \
        -H 'Content-Type: application/json' \
        -H 'Accept: application/json, text/event-stream' \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"prod-smoke","version":"0"}}}' \
        -o "$WORK/mcp.txt" -w '%{http_code}' >"$WORK/mcp.code" || return 1
    python3 - "$WORK/mcp.txt" "$(cat "$WORK/mcp.code")" "$VERSION" <<'PY'
import json, sys
body, code, want = open(sys.argv[1]).read(), sys.argv[2], sys.argv[3]
data = next((l[5:] for l in body.splitlines() if l.startswith("data:")), body)
try:
    got = json.loads(data)["result"]["serverInfo"]["version"]
except Exception:
    got = None
if code == "200" and got == want:
    print(f"ok   mcp initialize 200, serverInfo.version {got}")
else:
    print(f"FAIL mcp initialize HTTP {code}, serverInfo.version {got!r}, want {want}")
    sys.exit(1)
PY
}

check_analysis() {
    # Random pixels so the submission hash is new and the workers really run.
    python3 - "$WORK/smoke.png" <<'PY'
import os, struct, sys, zlib
w = h = 32
raw = b"".join(b"\x00" + os.urandom(w * 3) for _ in range(h))
def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
open(sys.argv[1], "wb").write(png)
PY
    hash=$(c -F "image=@$WORK/smoke.png" -F deep=false "$BASE/upload" |
        python3 -c 'import json,sys; print(json.load(sys.stdin)["submission_hash"])' 2>/dev/null) || hash=
    [ -n "$hash" ] || { echo "FAIL upload returned no submission_hash"; return 1; }
    status=
    for _ in $(seq 1 36); do
        status=$(c "$BASE/status/$hash" |
            python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null)
        [ "$status" = completed ] || [ "$status" = error ] && break
        sleep 5
    done
    [ "$status" = completed ] || { echo "FAIL analysis $hash status $status"; return 1; }
    code=$(c "$BASE/result/$hash" -o "$WORK/result.json" -w '%{http_code}')
    n=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get("results", d)))' \
        "$WORK/result.json" 2>/dev/null) || n=0
    if [ "$code" = 200 ] && [ "$n" -gt 0 ]; then
        echo "ok   analysis $hash completed, /result 200 with $n analyzers"
    else
        echo "FAIL analysis $hash /result HTTP $code, $n analyzers"
        return 1
    fi
}

i=1
while :; do
    echo "== attempt $i/$TRIES against $BASE for $VERSION"
    if check_home && check_mcp && check_analysis; then
        echo "PASS"
        exit 0
    fi
    [ "$i" -ge "$TRIES" ] && break
    i=$((i + 1))
    sleep "$WAIT"
done
echo "FAILED after $TRIES attempts"
exit 1
