"""
Standalone Local Web Server for OpenUSD 3D Visualizer and Synthetic Data Dashboard.
Serves the interactive Three.js 3D viewport, USD Outliner, Live PBR Editor, and SDG APIs.
"""

import http.server
import json
import mimetypes
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
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
SDG_DIR = os.path.join(WORKSPACE_DIR, "replicator", "_sdg_output")


def find_usd_files(base_dir: str) -> List[dict]:
    """Find all .usd, .usda, and .usdc files in the workspace."""
    usd_files = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "__pycache__" and d != "kit-app-template"]
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

            if not os.path.isabs(rel_or_full):
                target_path = os.path.normpath(os.path.join(WORKSPACE_DIR, rel_or_full))
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

        elif path == "/api/sdg":
            # Return dataset annotations if available
            annotations_path = os.path.join(SDG_DIR, "dataset_annotations.json")
            if os.path.exists(annotations_path):
                with open(annotations_path, "r") as f:
                    data = json.load(f)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"totalFrames": 0, "frames": []}).encode("utf-8"))
            return

        elif path.startswith("/sdg_media/"):
            filename = path[len("/sdg_media/"):]
            file_path = os.path.join(SDG_DIR, filename)
            if os.path.exists(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "SDG media file not found")
                return

        return super().do_GET()


def run_server(port: int = PORT):
    os.makedirs(STATIC_DIR, exist_ok=True)
    with socketserver.TCPServer(("", port), USDViewerHandler) as httpd:
        print(f"[*] OpenUSD 3D Studio & SDG Dashboard running at: http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Shutting down server...")


if __name__ == "__main__":
    run_server()
