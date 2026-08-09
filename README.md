# my-first-site

黃大象 — Doula・身心靈健康分享 個人自我介紹網頁。

🌐 **線上網址：** https://loveelephant924.github.io/my-first-site/

## 內容

單頁式靜態網站，莫蘭迪奶茶杏色系設計，包含：

- Hero — Wellness Coaching 形象照與簡介
- 關於我
- 女性 Wellness 陪跑
- Doula 孕產陪跑
- 人際關係陪跑
- 支持工作者陪跑
- Wellness 理念
- 聯絡方式
- **Wellness 測驗** — 側邊抽屜式互動測驗，六題自我覺察問卷，依分數給出對應的陪跑建議

## 檔案

| 檔案 | 說明 |
|---|---|
| `index.html` | 完整網頁，CSS、JS 與形象照（base64）皆已內嵌 |
| `main.py` | HTTP 伺服器：提供靜態檔案 + 留言板 API，只用 Python 標準函式庫 |
| `photo.jpg` | 形象照的網頁優化版備份（533×800） |
| `zbpack.json` | Zeabur 啟動指令設定 |

## 留言板 API

| 方法 | 路徑 | 說明 |
|---|---|---|
| `GET` | `/api/messages` | 取回最新 100 則留言（新到舊） |
| `POST` | `/api/messages` | 新增留言，body 為 `{"name": "...", "message": "..."}` |
| `GET` | `/healthz` | 健康檢查 |

資料存於 SQLite，`messages` 資料表。

**防濫用措施**：名字上限 20 字、留言上限 200 字；同一 IP 每 10 分鐘最多 5 則；
隱藏的蜜罐欄位攔截機器人；所有查詢使用參數化語法；前端一律以 `textContent`
渲染，訪客輸入不會被當成 HTML 執行。

## 本機執行

```bash
python3 main.py            # 預設 http://localhost:8080
PORT=3000 python3 main.py  # 自訂埠號
```

不需要安裝任何套件。資料庫會自動建立於 `data/guestbook.db`。

## 部署（Zeabur）

環境變數：

| 變數 | 預設 | 說明 |
|---|---|---|
| `PORT` | `8080` | Zeabur 會自動注入 |
| `DB_PATH` | `./data/guestbook.db` | SQLite 檔案位置 |

⚠️ **必須掛載持久化 Volume 到 `/app/data`**，否則每次重新部署留言都會消失。
