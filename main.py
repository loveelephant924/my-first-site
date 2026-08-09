"""Wellness Coaching 個人網站 + 訪客留言板。

只用 Python 標準函式庫，沒有任何外部相依套件：
  - http.server  提供靜態檔案與 JSON API
  - sqlite3      留言持久化

環境變數：
  PORT        監聽埠號，預設 8080（Zeabur 會自動注入）
  DB_PATH     SQLite 檔案位置，預設 ./data/guestbook.db
"""

import json
import os
import re
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "data", "guestbook.db"))
PORT = int(os.environ.get("PORT", "8080"))

# 留言限制
NAME_MAX = 20
MESSAGE_MAX = 200
LIST_LIMIT = 100

# 每個 IP 在 RATE_WINDOW 秒內最多送出 RATE_MAX 則留言
RATE_MAX = 5
RATE_WINDOW = 600

_rate_lock = threading.Lock()
_rate_log = {}

# 靜態檔案白名單，避免任意路徑讀取
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/photo.jpg": ("photo.jpg", "image/jpeg"),
}

# 控制字元（換行、Tab 以外）一律去除
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                message    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    print("[db] ready at %s" % DB_PATH, flush=True)


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def clean(raw, limit):
    """去除控制字元、壓縮空白、截斷長度。"""
    if not isinstance(raw, str):
        return ""
    text = _CONTROL_CHARS.sub("", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def rate_limited(ip):
    now = time.time()
    with _rate_lock:
        hits = _rate_log.setdefault(ip, deque())
        while hits and now - hits[0] > RATE_WINDOW:
            hits.popleft()
        if len(hits) >= RATE_MAX:
            return True
        hits.append(now)
        # 避免長時間執行後字典無限成長
        if len(_rate_log) > 5000:
            for key in [k for k, v in _rate_log.items() if not v]:
                del _rate_log[key]
        return False


def list_messages():
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, message, created_at"
            " FROM messages ORDER BY id DESC LIMIT ?",
            (LIST_LIMIT,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_message(name, message):
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (name, message, created_at) VALUES (?, ?, ?)",
            (name, message, created),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id, "name": name, "message": message, "created_at": created}


class Handler(BaseHTTPRequestHandler):
    server_version = "WellnessCoaching"

    def log_message(self, fmt, *args):
        print("[http] %s - %s" % (self.address_string(), fmt % args), flush=True)

    def client_ip(self):
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/api/messages":
            try:
                self.send_json(200, {"messages": list_messages()})
            except Exception as exc:  # noqa: BLE001
                print("[error] list: %r" % exc, flush=True)
                self.send_json(500, {"error": "server_error"})
            return

        if path == "/healthz":
            self.send_json(200, {"ok": True})
            return

        entry = STATIC_FILES.get(path)
        if not entry:
            self.send_error(404, "Not Found")
            return

        filename, content_type = entry
        full = os.path.join(BASE_DIR, filename)
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except OSError:
            self.send_error(404, "Not Found")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path.split("?")[0] != "/api/messages":
            self.send_error(404, "Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 10_000:
            self.send_json(400, {"error": "bad_request"})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"error": "invalid_json"})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "invalid_json"})
            return

        # 蜜罐欄位：真人看不到也不會填，機器人常常會
        if clean(payload.get("website", ""), 50):
            self.send_json(200, {"ok": True})
            return

        name = clean(payload.get("name", ""), NAME_MAX)
        message = clean(payload.get("message", ""), MESSAGE_MAX)
        if not name or not message:
            self.send_json(400, {"error": "empty"})
            return

        if rate_limited(self.client_ip()):
            self.send_json(429, {"error": "rate_limited"})
            return

        try:
            created = add_message(name, message)
        except Exception as exc:  # noqa: BLE001
            print("[error] insert: %r" % exc, flush=True)
            self.send_json(500, {"error": "server_error"})
            return

        self.send_json(201, created)


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("[boot] listening on 0.0.0.0:%d" % PORT, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
