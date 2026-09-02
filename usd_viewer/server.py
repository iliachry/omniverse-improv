"""
Standalone Local Web Server for OpenUSD 3D Visualizer.
Serves the interactive Three.js 3D viewport, USD Outliner, and Stage APIs.
"""

import http.server
import json
import os
import socketserver
import sys
import urllib.parse
from typing import List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from usd_parser import parse_usd_stage

PORT = 8088
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def find_usd_files(base_dir: str) -> List[dict]:
    """Find all .usd, .usda, and .usdc files in the workspace."""
    usd_files = []
    for root, dirs, files in os.walk(base_dir):
        # Skip .venv, .git, etc.
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__"]
        for file in files:
            if file.endswith((".usda", ".usd", ".usdc")):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
                usd_files.append({
                    "name": file,
                    "relPath": rel_path,
                    "fullPath": full_path,
                    "size": os.path.getsize(full_path)
                })
    return usd_files


class USDViewerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/stages":
            stages = find_usd_files(WORKSPACE_DIR)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(stages).encode("utf-8"))
            return

        elif path == "/api/stage":
            rel_or_full = query.get("path", [""])[0]
            if not rel_or_full:
                self.send_error(400, "Missing 'path' query parameter")
                return

            # Resolve path
            if not os.path.isabs(rel_or_full):
                target_path = os.path.normpath(os.path.join(WORKSPACE_DIR, rel_or_or_rel := rel_or_full))
            else:
                target_path = os.path.normpath(rel_or_full)

            if not os.path.exists(target_path):
                self.send_error(404, f"Stage file not found: {rel_or_full}")
                return

            try:
                stage_data = parse_usd_stage(target_path)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(stage_data).encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Error parsing USD stage: {str(e)}")
            return

        return super().do_GET()


def run_server(port: int = PORT):
    os.makedirs(STATIC_DIR, exist_ok=True)
    with socketserver.TCPServer(("", port), USDViewerHandler) as httpd:
        print(f"[*] OpenUSD 3D Visualizer server running at: http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Shutting down server...")


if __name__ == "__main__":
    run_server()
