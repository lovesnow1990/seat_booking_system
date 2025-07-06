# seat_booking_system

## 專案簡介
本專案為前後端分離的座位預約系統，後端採用 Django + DRF，前端採用 Vue.js，支援多座位鎖定、訂單管理，並可用 Docker 一鍵部署。

## 專案結構

- backend：Django (Python)
- frontend：Vue.js (seat-booking-frontend)
- Redis：座位鎖定快取
- PostgreSQL：預設資料庫（可依需求調整）

## 快速開始（Docker Compose）

### 1. 建立 .env 檔（可選）
於專案根目錄建立 `.env`，設定環境變數，例如：

```
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=False
DB_NAME=seatdb
DB_USER=seatuser
DB_PASSWORD=seatpass
DB_HOST=db
DB_PORT=5432
REDIS_HOST=redis
REDIS_PORT=6379
```

### 2. Build 與啟動所有服務

```powershell
docker compose up --build -d
```

啟動後，服務對應 port：
- 前端：http://localhost/
- 後端 API：http://localhost:8000/
- Redis: 6379
- PostgreSQL: 5432

### 3. 初始化資料庫（第一次啟動）

```powershell
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### 4. 測試 API & 前端

- 前端：瀏覽 http://localhost/
- 後端 API：可用 Postman 或 curl 測試 http://localhost:8000/api/

### 5. 查看 Log

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

### 6. 關閉所有服務

```powershell
docker compose down
```

## 進階

- 如需自訂資料庫、Redis、環境變數，請修改 docker-compose.yml 或 .env
- 若需本地開發，請分別於 backend、frontend 目錄下啟動開發伺服器
- 其他部署細節請參考各 Dockerfile

---
如有問題，歡迎提 issue 或討論！