

from __future__ import annotations

import math
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


def email_path(email: str) -> str:

    if not email or not email.strip():
        raise ValueError("Set REGISTRATION_EMAIL to your registration email.")
    return "/" + re.sub(r"[^A-Za-z0-9]", "_", email)


def lcm_response(query: str) -> str:

    params = parse_qs(query, keep_blank_values=True)
    values = []
    for name in ("x", "y"):
        items = params.get(name, [])
        if len(items) != 1 or re.fullmatch(r"[0-9]+", items[0]) is None:
            return "NaN"
        values.append(int(items[0]))

    x, y = values
                                                               
    if x == 0 or y == 0:
        return "0"
    return str((x // math.gcd(x, y)) * y)


def create_server(email: str, host: str = "127.0.0.1", port: int = 8080):

    route = email_path(email)
                                                                            
                                                                    
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status: int, body: str, allow: bool = False):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            if allow:
                self.send_header("Allow", "GET")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def do_GET(self):
            try:
                request = urlsplit(self.path)
            except ValueError:
                self.reply(400, "NaN")
                return
            if request.path != route:
                self.reply(404, "Not found")
                return
            self.reply(200, lcm_response(request.query))

        def method_not_allowed(self):
            self.reply(405, "Method not allowed", allow=True)

        do_HEAD = method_not_allowed
        do_POST = method_not_allowed
        do_PUT = method_not_allowed
        do_PATCH = method_not_allowed
        do_DELETE = method_not_allowed

    return ThreadingHTTPServer((host, port), Handler)


def main():
    email = os.environ.get("REGISTRATION_EMAIL", "")
    try:
        server = create_server(
            email,
            os.environ.get("HOST", "0.0.0.0"),
            int(os.environ.get("PORT", "8080")),
        )
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Listening on port {server.server_port}; route: {email_path(email)}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
