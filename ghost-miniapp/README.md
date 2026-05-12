# GHOST Telegram Mini App

Bu papka GHOST uchun Telegram Mini App va local Windows agentni saqlaydi.

## Tarkib

- `backend/main.py` - FastAPI server, Telegram Mini App clientlari va local agent WebSocket ko'prigi.
- `backend/agent.py` - Windows kompyuterda ishlaydigan local agent.
- `frontend/` - Telegram ichida ochiladigan mobil UI.

## Local test

```bat
cd ghost-miniapp
start.bat
```

Brauzerda ochish:

```text
http://localhost:8000
```

Local brauzer testi uchun `start.bat` avtomatik `GHOST_REQUIRE_TELEGRAM_AUTH=false` qiladi.

## Production env

```env
TELEGRAM_BOT_TOKEN=123456:bot_token
TELEGRAM_OWNER_ID=123456789
TELEGRAM_ALLOWED_IDS=
GHOST_MINIAPP_URL=https://your-app.railway.app
GHOST_REQUIRE_TELEGRAM_AUTH=true
GHOST_AGENT_TOKEN=long_random_secret
```

`GHOST_AGENT_TOKEN` backend va local agent orasidagi WebSocketni himoya qiladi. Productionda uni uzun random qiymatga o'zgartiring va local agent ishga tushayotgan muhitga ham qo'ying.

## Railway

Rootdan deploy qilsangiz `Procfile` va `nixpacks.toml` tayyor:

```text
web: uvicorn backend.main:app --app-dir ghost-miniapp --host 0.0.0.0 --port $PORT
```

`ghost-miniapp` papkasidan alohida deploy qilsangiz shu papkadagi `Procfile` ishlaydi.

## Telegram bot

Root `.env` ichida `GHOST_MINIAPP_URL` production HTTPS URL bo'lsa:

- `/app` buyrug'i Mini App tugmasini yuboradi.
- Bot menu button avtomatik `GHOST` Mini App tugmasiga sozlanadi.
- `/start` javobida Mini App tugmasi chiqadi.

BotFather orqali Main Mini App ham yoqish mumkin: `/mybots` -> Bot Settings -> Configure Mini App.

## Local agent

Backend deploy qilingandan keyin Windows kompyuterda:

```bat
cd ghost-miniapp\backend
set GHOST_BACKEND_URL=https://your-app.railway.app
set GHOST_AGENT_TOKEN=long_random_secret
python agent.py
```

Agent `https://...` URLni avtomatik `wss://.../ws/agent` ga aylantiradi.
