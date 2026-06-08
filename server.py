#!/usr/bin/env python3
"""
FROST PoC Server

Serves the attack page with COOP/COEP headers so the browser
grants high-resolution timers to the origin (FROST paper §4).

Headers sent:
  Cross-Origin-Opener-Policy: same-origin
  Cross-Origin-Embedder-Policy: require-corp
"""

import argparse
import http.server
import os
import sys
from socketserver import ThreadingMixIn

DIR = os.path.dirname(os.path.abspath(__file__))


class FROSTHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}\n")


class ThreadedHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description="FROST PoC Server")
    parser.add_argument("--port", type=int, default=8443, help="Port (default: 8443)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    args = parser.parse_args()

    httpd = ThreadedHTTPServer((args.host, args.port), FROSTHandler)
    print(f"[+] FROST PoC running at http://{args.host}:{args.port}/poc.html")
    print(f"[+] COOP: same-origin | COEP: require-corp")
    print(f"[+] Threaded server ready (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Stopped")
        httpd.server_close()


if __name__ == "__main__":
    main()
