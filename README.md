# TalkToMe — Language Bot (Matt)

👋 Meet **Matt**, your multilingual AI buddy for real language practice.  
He adapts to your level (A0–C2), style (casual/business), and can chat in **text** or **voice**.  
Also supports a **translator mode** for clean, copy-paste-ready translations.

---

## 🚀 Features
- 🤖 GPT-powered conversations in multiple languages  
- 🎙 Voice mode (TTS with OpenAI)  
- 📝 Text mode with contextual corrections  
- 🔄 Translator mode:
  - One-click on/off (`/translator`, `/translator_off`)
  - Choose direction (UI ↔ Target language)
  - Output: text or voice
  - Style: casual / business
- 💌 Promo codes, onboarding, and daily free message limits  
- 🌐 Deployable to **Render** (FastAPI + Telegram Webhook)

---

## ⚙️ Requirements
- Python **3.11+**  
- All dependencies are listed in [`requirements.txt`](./requirements.txt)

Install them locally:
```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables
All required variables are listed in [`.env.example`](./.env.example).  
Copy it and fill in your real values:

```bash
cp .env.example .env
```

⚠️ Never commit your `.env` with real tokens.

---

## ▶️ Local Development
1. Clone repo:
   ```bash
   git clone https://github.com/kapitan-marona/language-bot.git
   cd language-bot
   ```

2. Create virtual environment and install deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # (Linux/Mac)
   .venv\Scripts\activate      # (Windows)
   pip install -r requirements.txt
   ```

3. Add `.env` file (see `.env.example`).

4. Run locally:
   ```bash
   uvicorn english_bot:app --reload --port 8000
   ```

5. Check health endpoint:
   ```bash
   curl http://localhost:8000/healthz
   # {"ok": true}
   ```

---

## ☁️ Deploy on Render

### 1. Render setup
- Push code to GitHub.  
- In Render Dashboard:
  - Create **Web Service** → link repo.  
  - Runtime: Python  
  - Build command:
    ```bash
    pip install -r requirements.txt
    ```
  - Start command:
    ```bash
    uvicorn english_bot:app --host 0.0.0.0 --port $PORT
    ```
  - Health check path: `/healthz`  
  - Add environment variables from `.env.example`.

### 2. Verify deploy
After deployment:
```bash
curl https://<your-app>.onrender.com/healthz
```
Should return:
```json
{"ok": true}
```

---

## 💡 Developer Notes
- `english_bot.py` — FastAPI app + Telegram webhook entrypoint.  
- `handlers/chat/chat_handler.py` — main logic (sessions, text/voice/translator).  
- `handlers/chat/prompt_templates.py` — all system prompts and rules.  
- Logs use `logger.exception("...", exc_info=True)` for better debugging.  
- Local DB files (e.g. `user_profiles.db`) must be excluded via `.gitignore`.  

---

## 🧭 Roadmap
- [ ] VKontakte integration  
- [ ] More TTS voices  
- [ ] Conversation analytics  
- [ ] Onboarding redesign  

---

## 🐾 Credits
Created by [@marrona](https://t.me/marrona)  
Matt — your multilingual AI sidekick ✨
