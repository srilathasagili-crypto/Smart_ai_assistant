# 🤖 Intelligent AI Assistant

A tool-calling AI assistant built with **LangGraph**, **LangChain**, **Groq**, and **Streamlit** —
with web/news search, calendar, PDF analysis, long-term memory, reminders, and voice input/output.

## Features

| Category | What it does |
|---|---|
| 💬 Conversation | Groq (`llama-3.3-70b-versatile`) with full tool-calling, per-thread history |
| 🧮 Calculator | Safe arithmetic evaluation |
| 🌤️ Weather | Current conditions via OpenWeatherMap |
| 📧 Email | Send via Gmail, with attachments and address validation |
| 📰 News | Topic search and top headlines via NewsAPI |
| 🔎 Web search | Tavily (if configured) or free DuckDuckGo fallback, with source links |
| 📅 Calendar | Create / list today's / delete Google Calendar events |
| 📄 PDF analysis | Upload a PDF, ask questions, summarize, extract key info |
| 🧠 Long-term memory | Remembers your name, preferences, and favourite technologies across sessions |
| ⏰ Reminders | Create / list / delete reminders, notified as a banner when due |
| 🎤 Voice | Speech-to-text (Groq Whisper) and text-to-speech (gTTS) |

## Project structure

```
app.py                     # Streamlit UI — session state, sidebar, chat loop
graph/
  builder.py                 # LangGraph StateGraph wiring (unchanged shape: chat <-> tools)
  config.py                   # Env var loading with graceful optional-key handling + validate_config()
  llm.py                        # Groq LLM factory
  logger.py                      # Central logger factory used across the whole app
  nodes.py                        # chat_node (system prompt + LLM) and tool_node (ToolNode)
  state.py                         # AssistantState: messages, user_id, pdf_context
memory/
  chat_history.py             # SqliteSaver checkpointer — per-thread conversation memory
  user_profile.py               # Persistent name/preferences store, keyed by user_id
  reminders.py                    # Persistent reminder store
mcp_server/
  server.py                    # Exposes stateless tools over MCP (folder renamed from
                                # "mcp" to avoid colliding with the real "mcp" PyPI
                                # package — the Model Context Protocol SDK that
                                # fastmcp itself depends on)
tools/
  calculator.py, weather.py, gmail.py    # existing tools (gmail.py extended)
  news.py, web_search.py, calendar_tool.py   # new tools
  pdf_extract.py, pdf_tools.py                # PDF text extraction + Q&A/summary tools
  reminders_tool.py, memory_tool.py             # reminder + long-term memory tools
ui/
  components.py               # Sidebar rendering helpers (tool/memory status, theme)
```

## Installation

```bash
git clone https://github.com/srilathasagili-crypto/Intelligent-AI-Assistant.git
cd Intelligent-AI-Assistant
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with your keys (see below)
streamlit run app.py
```

## API setup guide

Only `GROQ_API_KEY` is required. Every other integration is optional — if a key is
missing, that feature shows as disabled (⚪) in the sidebar and the rest of the app
keeps working normally.

| Key | Where to get it | Required? |
|---|---|---|
| `GROQ_API_KEY` | https://console.groq.com | **Yes** |
| `OPENWEATHER_API_KEY` | https://openweathermap.org/api | No |
| `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` | Gmail → Google Account → Security → App passwords | No |
| `NEWS_API_KEY` | https://newsapi.org (free tier: 500 req/day) | No |
| `TAVILY_API_KEY` | https://tavily.com (optional — falls back to free DuckDuckGo search) | No |
| `GOOGLE_CALENDAR_CREDENTIALS_PATH` | See "Calendar setup" below | No |

### Calendar setup (optional)

1. Google Cloud Console → enable the **Google Calendar API**.
2. Create an OAuth Client ID (type: **Desktop app**) → download as `credentials.json`.
3. Set `GOOGLE_CALENDAR_CREDENTIALS_PATH` to that file's path.
4. Run the app **locally** once and use a calendar tool — a browser window opens for
   one-time consent, and a `token.json` is cached for reuse.
5. For a deployed instance (Streamlit Cloud / HF Spaces — no local browser available),
   generate `token.json` locally first, then include it as a deploy-time secret/asset.
   `credentials.json` and `token.json` are gitignored — never commit them.

## Feature documentation

- **Long-term memory**: enter your name in the sidebar — it becomes your memory key.
  Tell the assistant a preference ("I love Python") and it saves it via `remember_user_info`;
  ask "what do you remember about me?" to trigger `recall_user_info`. Facts are injected
  into the system prompt automatically on every turn.
- **PDF analysis**: upload a PDF in the sidebar. Text is extracted and stored in the
  conversation's state (not sent to the model until you ask about it) — then ask questions,
  or say "summarize this PDF" / "extract key info from this PDF."
- **Reminders**: "remind me to submit the report at 6pm today." Since Streamlit apps only
  run while the page is open (no background server on the free tiers), reminders are
  checked and shown as a banner each time the app reruns — not a true push notification.
- **Voice**: toggle "🎤 Voice mode" in the sidebar. Speak instead of typing (transcribed via
  Groq's hosted Whisper); replies are also read aloud.

## Deployment

### Streamlit Community Cloud
1. Push to GitHub (make sure `myenv/`/`.venv/` is **not** committed — see Project cleanup).
2. https://share.streamlit.io → New app → this repo, branch `main`, file `app.py`.
3. Settings → Secrets → paste the contents of `.streamlit/secrets.toml.example`, filled in.
4. Deploy. Note: SQLite-based memory resets on redeploy (expected on free hosting).

### Hugging Face Spaces
- **Streamlit SDK (simplest)**: new Space → SDK `Streamlit` → push the repo as-is →
  add the same keys under Space **Settings → Repository secrets** (read as env vars,
  which `graph/config.py` already supports).
- **Docker (if you hit audio codec issues with voice)**:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 8501
  CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
  ```

## Project cleanup notes

- ⚠️ **`myenv/` (the local virtual environment) was previously committed to git — 508MB,
  22,500+ files.** Remove it from tracking:
  ```bash
  git rm -r --cached myenv
  git commit -m "Remove committed virtualenv"
  ```
  (`.gitignore` now excludes `myenv/`, `venv/`, `.venv/` so this won't happen again.)
- `credentials.json`, `token.json`, and `*.sqlite` are now gitignored too.

## Screenshots

_Add screenshots here after your first deploy:_

- Chat view with tool status sidebar
- PDF upload + Q&A
- Voice mode in action

## Testing checklist

- [ ] App starts with only `GROQ_API_KEY` set — sidebar shows other tools as ⚪ disabled, no crash
- [ ] Calculator, weather (if key set) still work as before
- [ ] Send an email (if configured) — with and without an attachment
- [ ] Send an email to an invalid address — get a clear validation message, no crash
- [ ] Ask a news question (if `NEWS_API_KEY` set) and a general knowledge question (web search)
- [ ] Create, list, and delete a calendar event (if configured)
- [ ] Upload a PDF, ask a question about it, ask for a summary
- [ ] Upload a scanned/image-only PDF — should show a friendly "no text found" message, not crash
- [ ] State your name and a preference, refresh the page, re-enter the same name — memory persists
- [ ] Create a reminder with a due time in the past — banner appears on next rerun
- [ ] Toggle voice mode, speak a question, hear the reply read back
- [ ] Turn off internet / revoke a key mid-conversation — assistant reports the error, app doesn't crash
- [ ] Click "Clear chat" — history resets, new thread starts

## Deployment checklist

- [ ] `myenv/` removed from git tracking
- [ ] `.env` / `.streamlit/secrets.toml` are NOT committed
- [ ] `requirements.txt` installs cleanly in a fresh venv
- [ ] All required secrets set on the hosting platform
- [ ] App boots and responds to a first message post-deploy
- [ ] Confirm SQLite-based memory reset behavior is acceptable for your use case (or move to a hosted DB)

## Suggested future improvements

- Replace `SqliteSaver`/local SQLite stores with a hosted DB (Supabase/Postgres) for memory
  that survives redeploys.
- Real authentication (Google OAuth / `streamlit-authenticator`) instead of a typed name,
  for a trustworthy `user_id`.
- Chunk + embed long PDFs (vector search) instead of full-text stuffing, for large documents.
- True reminder notifications via an external cron job calling a webhook/email, since
  Streamlit has no background scheduler on free tiers.
- Conversation summarization node to keep long chat histories within token budget.
- Swap Gmail SMTP app-password auth for the Gmail API + OAuth for per-user sending.

## Going public: multi-user setup (auth, rate limits, usage tracking)

This app now supports multiple simultaneous users safely. Summary of what changed
and what you need to configure — full details in the chat writeup that shipped
with this update, but the short version:

1. **Sign-in is required.** `auth/authentication.py` uses Streamlit's native
   `st.login()` (Google OAuth). Until you add an `[auth]` block to
   `secrets.toml`, the app runs in an insecure "dev mode" (type-a-name) instead
   of crashing — don't ship dev mode publicly.
2. **Rate limits** (`security/rate_limiter.py`): per-user burst limit
   (`RATE_LIMIT_PER_MINUTE`, default 6) and daily budget
   (`DAILY_REQUEST_LIMIT`, `DAILY_TOKEN_LIMIT`), enforced before every LLM call.
3. **Usage tracking** (`security/usage_tracker.py`): every Groq response's real
   token counts are logged per user, shown live in the sidebar.
4. **Gmail / Calendar are admin-only.** They act on your single shared account —
   set `ADMIN_EMAILS` in secrets, everyone else gets a polite refusal instead of
   being able to send email "as you" or edit your calendar.
5. **Storage**: `security/db.py` uses local SQLite under `./data/app.db` by
   default. On Streamlit Community Cloud this directory is wiped on every
   reboot/redeploy — fine for testing, but swap it for managed Postgres
   (Supabase/Neon/Railway) before relying on it for real usage data.

See `.streamlit/secrets.toml.example` for every new config key.

