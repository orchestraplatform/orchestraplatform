#!/usr/bin/env python3
"""Serve OpenAPI schema file via HTTP."""

import json
import http.server
import socketserver
import sys
from pathlib import Path

class SchemaHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/openapi.json':
            if Path('openapi.json').exists():
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open('openapi.json', 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, 'Schema file not found. Run: just generate-schema')
        else:
            self.send_error(404, 'Only /openapi.json is available')

def serve_schema(port: int = 8001):
    """Serve OpenAPI schema on specified port."""
    with socketserver.TCPServer(('', port), SchemaHandler) as httpd:
        print(f'Serving schema at http://localhost:{port}/openapi.json')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nSchema server stopped')

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    serve_schema(port)
