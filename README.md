# my-first-site

黃大象 — Wellness Coaching 個人網站。

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
| `functions/api/messages.js` | **正式環境**的留言板 API（Cloudflare Pages Function + D1） |
| `main.py` | **本機開發**用伺服器：靜態檔案 + 相同的留言板 API，只用 Python 標準函式庫 |
| `schema.sql` | 資料表定義，套用於 D1 |
| `photo.jpg` | 形象照的網頁優化版備份（533×800） |
| `zbpack.json` | Zeabur 啟動設定（保留備用，見下方說明） |

> ⚠️ **兩份後端實作必須手動保持同步。**
> `functions/api/messages.js`（正式）與 `main.py`（本機）各自實作了同一組 API。
> 之所以保留兩份，是因為 Cloudflare Functions 需要 Node 工具鏈才能在本機執行，
> 而開發機沒有 Node；`main.py` 只靠 Python 標準函式庫就能跑。
> 修改任一邊的驗證規則或資料表結構時，**記得同步另一邊**，
> 兩者的 `schema` 與時間格式（ISO-8601 UTC，結尾 `Z`）目前是一致的。

## 留言板 API

| 方法 | 路徑 | 說明 |
|---|---|---|
| `GET` | `/api/messages` | 取回最新 100 則留言（新到舊） |
| `POST` | `/api/messages` | 新增留言，body 為 `{"name": "...", "message": "..."}` |
| `GET` | `/healthz` | 健康檢查 |

（`/healthz` 僅本機伺服器提供。）

資料存於 SQLite —— 正式環境用 Cloudflare D1，本機用 `data/guestbook.db`。

**防濫用措施**

- 名字上限 20 字、留言上限 200 字，控制字元一律去除
- 同一訪客每 10 分鐘最多 5 則
- 隱藏的蜜罐欄位攔截機器人
- 所有查詢使用參數化語法
- 前端一律以 `textContent` 渲染，訪客輸入不會被當成 HTML 執行
- **只儲存 IP 的 SHA-256 雜湊**，不儲存 IP 本身

留言送出後立即公開顯示，沒有審核流程。

## 本機執行

```bash
python3 main.py            # 預設 http://localhost:8080
PORT=3000 python3 main.py  # 自訂埠號
```

不需要安裝任何套件。資料庫會自動建立於 `data/guestbook.db`。

## 部署（Cloudflare Pages + D1）

1. Cloudflare 後台 → **Workers & Pages → D1** → 建立資料庫，命名 `guestbook`
2. 進入該資料庫的 **Console**，貼上 `schema.sql` 全部內容並執行
3. **Workers & Pages → Create → Pages → 連接 GitHub**，選這個 repo
   - Build command：留空
   - Build output directory：`/`
4. 部署完成後 → **Settings → Functions → D1 database bindings**
   - Variable name：`DB`（必須完全一致，程式碼以此名稱存取）
   - D1 database：`guestbook`
5. （建議）**Settings → Environment variables** 新增 `IP_SALT`，值填任意隨機字串
6. 重新部署一次，讓繫結生效

環境變數：

| 變數 | 預設 | 說明 |
|---|---|---|
| `IP_SALT` | `wellness-coaching` | IP 雜湊的鹽值，建議改成隨機字串 |

## 關於 Zeabur

原本規劃部署於 Zeabur，但六次部署全部在 `checking for banned images` 階段
被拒（`this service is not allowed to deploy on Zeabur`），且在純靜態、
Dockerfile、Python 三種形式與全新專案下結果相同，屬帳號層級限制，非程式碼問題。

`main.py` 與 `zbpack.json` 予以保留：若該限制日後解除，不需修改任何程式碼即可部署。
