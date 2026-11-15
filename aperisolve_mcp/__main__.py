"""Entry point: ``python -m aperisolve_mcp`` (hosted) or ``--stdio`` (local).

One server, two transports:

* no flag — Streamable HTTP on ``0.0.0.0:5001`` at ``/mcp``. This is what the
  ``mcp`` compose service runs; nginx proxies ``/mcp/`` to it (docs/deploy.md).
  Binding all interfaces is required inside a container; the published port is
  loopback-only on the host.
* ``--stdio`` — the same tools over stdin/stdout, for a self-hoster or a local
  client that would rather launch the process than expose a port.
"""

from __future__ import annotations

import argparse
import logging

from aperisolve.config import MAX_CONTENT_LENGTH

from . import env_int, env_str
from .server import build_server

DEFAULT_HOST = "0.0.0.0"  # noqa: S104 -- in-container bind; compose publishes 127.0.0.1:5001 only
DEFAULT_PORT = 5001
DEFAULT_PATH = "/mcp"

# Room for the JSON-RPC envelope around an `analyze` call: base64 inflates the
# file by 4/3, and the SDK's own 4 MiB default would reject a legal upload on
# an instance whose MAX_CONTENT_LENGTH is 3 MiB (the .env.example value).
_ENVELOPE_SLACK = 64 * 1024


def max_request_body_size() -> int:
    """Streamable-HTTP body cap, derived from the instance's upload limit."""
    return max(4 * 1024 * 1024, MAX_CONTENT_LENGTH // 3 * 4 + _ENVELOPE_SLACK)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        prog="python -m aperisolve_mcp",
        description="MCP server over the Aperi'Solve HTTP API.",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="serve on stdin/stdout instead of Streamable HTTP",
    )
    parser.add_argument("--host", default=env_str("MCP_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=env_int("MCP_PORT", DEFAULT_PORT))
    parser.add_argument("--path", default=env_str("MCP_PATH", DEFAULT_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the server on the transport selected by the command line."""
    args = _parse_args(argv)
    # stdio speaks JSON-RPC on stdout: logging must go to stderr, which is
    # logging's default stream, so only the level is set here.
    logging.basicConfig(level=env_str("MCP_LOG_LEVEL", "INFO").upper())
    mcp = build_server()
    if args.stdio:
        mcp.run("stdio")
    else:
        # DNS-rebinding protection stays off (the SDK default when no
        # TransportSecuritySettings is passed): the hosted endpoint is public
        # and anonymous behind nginx, which already fixes the Host it forwards,
        # and there is no browser-held credential for a rebind to steal.
        mcp.run(
            "streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path=args.path,
            max_request_body_size=max_request_body_size(),
        )


if __name__ == "__main__":
    main()
