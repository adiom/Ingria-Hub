# AGENTS.md

Russian-language project. Python FastAPI backend + plain static HTML/JS frontend. No package/lint/test tooling is configured — do not assume pytest, ruff, or a frontend build step.

## Run

```bash
pip install -r requirements.txt          # backend deps
./run.sh                                 # kills whatever holds port 31337, then starts uvicorn --reload
```

- `./run.sh` frees port **31337** (`lsof -ti tcp:31337 | kill -9`) before starting uvicorn, so a stale server won't cause `[Errno 48] Address already in use`. Extra args are forwarded; override with `PORT=... HOST=... ./run.sh`.
- Do not free the port from inside `main.py`: with `--reload` uvicorn binds the socket in the parent process *before* importing the app, so an in-app startup hook is too late (and would kill the reloader).
- `python main.py` runs uvicorn on **port 8000**, but the README and every `test_*.py` / `telegram_bot.py` expect **31337**. Use `./run.sh` above to match.
- `python live.py --user-id 1` (live audio/video) needs extra deps **not** in requirements.txt: `pip install google-genai opencv-python pyaudio pillow mss` (`mss` for `--mode screen`).
- `python telegram_bot.py` uses its own SQLite `ingria.db`, not the server's DB.

## Tests

There is no test runner. `test_*.py` are manual scripts: most `requests.get(...)` against `http://localhost:31337` or direct-DB scripts, so a server (or DB) must already be running. Several only print status text (e.g. `test_memory_ui_fix.py`, `test_audio_*.py`). `python test.py` is a standalone Gemini API-key check, unrelated to the rest. Run a single script directly: `python test_blockchain.py`.

Exception: `source venv/bin/activate` then `python test_blockchain_integrity.py` runs standalone `unittest` regression checks using SQLAlchemy and in-memory SQLite. No running server, API keys, or working database are needed.

## Config & secrets (already hardcoded — do not expand)

- `main.py` requires `GOOGLE_API_KEY` from a `.env` (gitignored; no `.env.example` exists).
- PostgreSQL URL is hardcoded in `main.py`, `live.py`, `migrate_db.py`, `migrate_blockchain.py`; `check_memories.py` uses a **different/typo host** (`10.0.0.105`). Google API keys are hardcoded in `live.py`, `live_tools.py`, `test.py`.
- Do not commit new secrets or echo existing ones. Prefer env vars for any new code.

## Architecture

- Entrypoints are root-level: `main.py` (HTTP API + WebSocket), `live.py` (Gemini Live audio/video), `live_tools.py`, `telegram_bot.py`.
- `db.py` = SQLAlchemy models (`Memory`, `IngriaRequest`, `User`, `File`, `IngriaError`). No Alembic; schemas are created via `Base.metadata.create_all` at import plus raw `ALTER` scripts `migrate_db.py` / `migrate_blockchain.py`.
- `memory_service.py` persists memories by parsing a `memory:` section from the model's reply (`extract_memory_from_response`). The system prompt in `main.py`/`live.py` *requires* the model to end every answer with `memory:`; keep that invariant if you edit prompts.
- `blockchain_service.py` is an integrity chain, not a real chain: `hash = sha256(memory_text + previous_hash + created_at.isoformat())`. Creation selects the predecessor with `id < memory_id`; verification checks links against adjacent rows ordered by ID, and repair rebuilds links/hashes sequentially from the genesis hash. Repair uses current contents and cannot recover deleted/modified text. Detecting tail deletion or a full rewrite requires an independently stored checkpoint.
- Frontend: static files in `frontend/`, served both at `/static` and via explicit routes `/ui`, `/memories-ui`, `/blockchain-ui` that read the HTML file. `frontend/app.js` connects to `/ws/stream_gemini`.
- `/ws/stream_gemini` references a module-global `ingr_model` that is never defined → it is broken at runtime. Also note the two Gemini SDKs are mixed on purpose: legacy `google-generativeai` (global `genai.configure`, model `gemini-2.5-flash`) vs new `google-genai` (`from google import genai`, live model). Don't swap them.
- `live_3d.tsx` (root) is a stray Lit component, not part of the static frontend; it imports missing `./utils` and `./visual-3d`. `package.json` only pulls TypeScript. There is nothing to build.
