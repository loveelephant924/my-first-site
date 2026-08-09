-- 留言板資料表（Cloudflare D1 / SQLite 通用）
--
-- 套用方式：Cloudflare 後台 → Workers & Pages → D1 → 選資料庫 → Console
-- 把整份內容貼上執行即可。

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL,   -- ISO-8601 UTC，例如 2026-08-09T05:12:33.000Z
    ip_hash    TEXT             -- IP 的 SHA-256 雜湊，僅供速率限制，不存原始 IP
);

-- 依速率限制的查詢條件建立索引
CREATE INDEX IF NOT EXISTS idx_messages_rate ON messages (ip_hash, created_at);
