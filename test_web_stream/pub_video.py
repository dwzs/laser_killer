#!/usr/bin/env python3
"""HTTP/MJPEG 摄像头推流（局域网可访问，尽量简洁）"""

import argparse
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import cv2

CAP = None
JPEG_QUALITY = 80


INDEX_HTML = b"""<!doctype html><html><body style="margin:0;background:#111;display:grid;place-items:center;height:100vh">
<img src="/stream.mjpg" style="max-width:100vw;max-height:100vh">
</body></html>"""


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(INDEX_HTML)))
            self.end_headers()
            self.wfile.write(INDEX_HTML)
            return

        if self.path != "/stream.mjpg":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        params = [int(cv2.IMWRITE_JPEG_QUALITY), int(JPEG_QUALITY)]
        try:
            while True:
                ok, frame = CAP.read()
                if not ok:
                    time.sleep(0.05)
                    continue
                ok, buf = cv2.imencode(".jpg", frame, params)
                if not ok:
                    continue
                jpg = buf.tobytes()
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                self.wfile.write(jpg)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError):
            return


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--cam", type=int, default=1)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--quality", type=int, default=80)
    args = p.parse_args()

    global CAP, JPEG_QUALITY
    JPEG_QUALITY = max(1, min(100, args.quality))

    CAP = cv2.VideoCapture(args.cam)
    CAP.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    CAP.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not CAP.isOpened():
        print(f"无法打开摄像头: {args.cam}")
        return 1

    srv = Server((args.host, args.port), Handler)
    print(f"已启动: http://{args.host}:{args.port}/  (本机可用 127.0.0.1)")
    print("按 Ctrl+C 退出")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
        CAP.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
