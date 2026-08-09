/**
 * 留言板 API — Cloudflare Pages Function
 *
 * 路由：/api/messages
 *   GET   取回最新留言（新到舊）
 *   POST  新增一則留言
 *
 * 需要的繫結：
 *   DB       D1 資料庫（D1 底層就是 SQLite）
 *   IP_SALT  可選，雜湊 IP 用的鹽值；未設定時使用預設值
 */

const NAME_MAX = 20;
const MESSAGE_MAX = 200;
const LIST_LIMIT = 100;

// 同一位訪客在 RATE_WINDOW_MS 內最多送出 RATE_MAX 則
const RATE_MAX = 5;
const RATE_WINDOW_MS = 10 * 60 * 1000;

// 控制字元（換行、Tab 以外）一律去除
const CONTROL_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;

function clean(raw, limit) {
  if (typeof raw !== "string") return "";
  return raw.replace(CONTROL_CHARS, "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

/**
 * 只儲存 IP 的雜湊值，不儲存 IP 本身。
 * 速率限制照常運作，但資料庫裡不會留下可識別訪客的個資。
 */
async function hashIp(ip, salt) {
  const bytes = new TextEncoder().encode(`${salt}:${ip}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function onRequestGet({ env }) {
  try {
    const { results } = await env.DB.prepare(
      "SELECT id, name, message, created_at FROM messages ORDER BY id DESC LIMIT ?"
    )
      .bind(LIST_LIMIT)
      .all();
    return json({ messages: results ?? [] });
  } catch (err) {
    console.error("list failed:", err);
    return json({ error: "server_error" }, 500);
  }
}

export async function onRequestPost({ request, env }) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: "invalid_json" }, 400);
  }
  if (!payload || typeof payload !== "object") {
    return json({ error: "invalid_json" }, 400);
  }

  // 蜜罐欄位：真人看不到也不會填，機器人常常會
  if (clean(payload.website, 50)) {
    return json({ ok: true });
  }

  const name = clean(payload.name, NAME_MAX);
  const message = clean(payload.message, MESSAGE_MAX);
  if (!name || !message) {
    return json({ error: "empty" }, 400);
  }

  const ip = request.headers.get("CF-Connecting-IP") || "0.0.0.0";
  const ipHash = await hashIp(ip, env.IP_SALT || "wellness-coaching");
  const since = new Date(Date.now() - RATE_WINDOW_MS).toISOString();

  try {
    const recent = await env.DB.prepare(
      "SELECT COUNT(*) AS n FROM messages WHERE ip_hash = ? AND created_at > ?"
    )
      .bind(ipHash, since)
      .first();
    if (recent && recent.n >= RATE_MAX) {
      return json({ error: "rate_limited" }, 429);
    }

    const createdAt = new Date().toISOString();
    const res = await env.DB.prepare(
      "INSERT INTO messages (name, message, created_at, ip_hash) VALUES (?, ?, ?, ?)"
    )
      .bind(name, message, createdAt, ipHash)
      .run();

    return json(
      { id: res.meta.last_row_id, name, message, created_at: createdAt },
      201
    );
  } catch (err) {
    console.error("insert failed:", err);
    return json({ error: "server_error" }, 500);
  }
}
