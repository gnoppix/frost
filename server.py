#-------------------------------------------------------------------------------
# Name: Gnoppix Linux - Services
# Architecture: all
# Date: 2002-2006 by Gnoppix Linux
# Author: Andreas Mueller
# Website: https://www.gnoppix.com
# Licence: Business Source License (BSL / BUSL)
#-------------------------------------------------------------------------------
#!/usr/bin/env python3
"""
FROST PoC Server

Serves the attack page with COOP/COEP headers for high-resolution timers.
Based on the FROST paper requirements (Section 4):
  - Cross-Origin-Opener-Policy: same-origin
  - Cross-Origin-Embedder-Policy: require-corp

Usage:
  python server.py [--port PORT] [--host HOST]
"""

import argparse
import http.server
import os
import sys

PORT = 8443
HOST = "0.0.0.0"
DIR = os.path.dirname(os.path.abspath(__file__))


class FROSTHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def end_headers(self):
        # COOP/COEP headers for cross-origin isolation → high-res timers
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        # Prevent caching of measurement data
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}\n")


def main():
    parser = argparse.ArgumentParser(description="FROST PoC Server")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    parser.add_argument("--host", default=HOST, help=f"Bind address (default: {HOST})")
    args = parser.parse_args()

    httpd = http.server.HTTPServer((args.host, args.port), FROSTHandler)
    print(f"[+] FROST PoC server running at http://{args.host}:{args.port}/poc.html")
    print(f"[+] COOP: same-origin | COEP: require-corp (high-res timers enabled)")
    print(f"[+] Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Server stopped")
        httpd.server_close()


if __name__ == "__main__":
    main()
