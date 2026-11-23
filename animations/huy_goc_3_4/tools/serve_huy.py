"""Local demo server with correct JavaScript/WASM MIME types on Windows."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.mjs': 'text/javascript', '.wasm': 'application/wasm'}

    def log_message(self, *args):
        pass


def server(port=0):
    return ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(ROOT)))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8785)
    args = p.parse_args()
    app = server(args.port)
    print(f'http://127.0.0.1:{app.server_port}/preview.html', flush=True)
    app.serve_forever()
