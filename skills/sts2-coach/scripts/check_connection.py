#!/usr/bin/env python3
"""Print whether the SLAI mod's HTTP server is reachable."""

from __future__ import annotations

import argparse
import sys

import _lib


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=_lib.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=_lib.DEFAULT_PORT)
    args = parser.parse_args()

    result = _lib.check_connection(host=args.host, port=args.port)
    _lib.emit_json(result)
    return 0 if result.get("connected") else 1


if __name__ == "__main__":
    sys.exit(main())
