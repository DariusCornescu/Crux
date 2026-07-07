# Hosting + OpenRouter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **No git:** This project is not under version control (user chose scp-based deploy). There are no `git commit` steps. Each task ends with a **Checkpoint** — run the test suite to confirm nothing broke.

**Goal:** Route Claude calls through a pluggable LLM provider (OpenRouter default, Anthropic optional) and add the files needed to host the Dockerized backend on a DigitalOcean Droplet behind HTTPS.

**Architecture:** A thin `app/llm.py` module exposes `complete()` + `is_configured()`; the two existing call sites (`report_generator`, `chat_service`) call it instead of the Anthropic SDK directly. Deployment adds a Caddy reverse-proxy service (auto TLS) via a `docker-compose.prod.yml` overlay, leaving local dev unchanged.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, `openai` SDK (OpenRouter), `anthropic` SDK, Docker Compose, Caddy.

Spec: `docs/superpowers/specs/2026-07-05-hosting-and-openrouter-design.md`

All backend paths are relative to `backend-fastapi/`. Run tests from `backend-fastapi/` with `python -m pytest`.

---

## File Structure

- Create: `backend-fastapi/app/llm.py` — provider dispatch (`complete`, `is_configured`)
- Modify: `backend-fastapi/app/config.py` — add provider settings, fix model ID
- Modify: `backend-fastapi/app/report_generator.py` — call `llm.complete`
- Modify: `backend-fastapi/app/chat_service.py` — call `llm.complete`
- Modify: `backend-fastapi/requirements.txt` — add `openai`
- Modify: `backend-fastapi/.env`, `backend-fastapi/.env.example` — provider vars
- Modify: `backend-fastapi/tests/conftest.py` — pin `OPENROUTER_API_KEY=""`
- Create: `backend-fastapi/tests/test_llm.py` — provider dispatch tests
- Create: `backend-fastapi/Caddyfile` — reverse proxy + TLS
- Create: `backend-fastapi/docker-compose.prod.yml` — prod overlay (Caddy)
- Create: `backend-fastapi/docs/DEPLOY.md` — runbook
- Modify: `android-native/app/src/main/java/com/darius/crux/network/ApiConfig.kt`
- Modify: `android-native/app/src/main/AndroidManifest.xml` — drop cleartext

---

## Task 1: Add provider settings to config

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Add the new settings fields**

In `app/config.py`, inside the `Settings` class, replace the line
`anthropic_model: str = "claude-sonnet-5"` and add the OpenRouter/provider
fields. The `anthropic` block becomes:

```python
    llm_provider: str = "openrouter"  # "openrouter" | "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.6"

    fcm_service_account_json_path: str = ""
```

(Delete the old `anthropic_api_key`/`anthropic_model` lines you are replacing so
there are no duplicates; keep every other field unchanged.)

- [ ] **Step 2: Verify it imports**

Run: `python -c "from app.config import get_settings; s=get_settings(); print(s.llm_provider, s.anthropic_model, s.openrouter_model)"`
Expected: `openrouter claude-sonnet-4-6 anthropic/claude-sonnet-4.6`

- [ ] **Step 3: Checkpoint**

Run: `python -m pytest -q`
Expected: PASS (same as before — no behavior change yet).

---

## Task 2: Create the `llm` module (TDD)

**Files:**
- Create: `app/llm.py`
- Create: `tests/test_llm.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Pin OpenRouter key empty in the test env**

In `tests/conftest.py`, directly below the line
`os.environ["ANTHROPIC_API_KEY"] = ""`, add:

```python
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["LLM_PROVIDER"] = "openrouter"
```

This keeps tests in deterministic offline mode even if the developer's `.env`
has a real key (os.environ overrides the `.env` file in pydantic-settings).

- [ ] **Step 2: Write the failing tests**

Create `tests/test_llm.py`:

```python
"""Provider dispatch for app.llm. No network — SDK clients are monkeypatched."""
from app import llm
from app.config import get_settings


def _reload_settings(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


def test_is_configured_openrouter(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-x")
    assert llm.is_configured() is True


def test_is_not_configured_openrouter_without_key(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="")
    assert llm.is_configured() is False


def test_is_configured_anthropic(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-x")
    assert llm.is_configured() is True


def test_complete_openrouter_builds_payload(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="openrouter",
                     OPENROUTER_API_KEY="sk-or-x", OPENROUTER_MODEL="anthropic/claude-sonnet-4.6")
    captured = {}

    class FakeMsg:
        content = "hello from openrouter"

    class FakeChoice:
        message = FakeMsg()

    class FakeResp:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResp()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.chat = FakeChat()

    monkeypatch.setattr(llm, "_openai_client", lambda s: FakeClient(
        api_key=s.openrouter_api_key, base_url="https://openrouter.ai/api/v1"))

    out = llm.complete("SYS", [{"role": "user", "content": "hi"}], max_tokens=42)
    assert out == "hello from openrouter"
    assert captured["model"] == "anthropic/claude-sonnet-4.6"
    assert captured["max_tokens"] == 42
    assert captured["messages"][0] == {"role": "system", "content": "SYS"}
    assert captured["messages"][1] == {"role": "user", "content": "hi"}


def test_complete_dispatches_to_anthropic(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-x")
    monkeypatch.setattr(llm, "_anthropic_complete",
                        lambda s, system, messages, max_tokens: "from anthropic")
    out = llm.complete("SYS", [{"role": "user", "content": "hi"}])
    assert out == "from anthropic"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest tests/test_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm'`.

- [ ] **Step 4: Write `app/llm.py`**

Create `app/llm.py`:

```python
"""LLM provider abstraction (spec 2026-07-05-hosting-and-openrouter-design).

One entry point, complete(), dispatches to OpenRouter (default, OpenAI-compatible)
or the Anthropic SDK based on settings.llm_provider. When the selected provider
has no API key, is_configured() returns False and callers use their existing
deterministic offline fallback.
"""
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def is_configured() -> bool:
    s = get_settings()
    if s.llm_provider == "anthropic":
        return bool(s.anthropic_api_key)
    return bool(s.openrouter_api_key)


def complete(system: str, messages: list[dict], max_tokens: int = 1000) -> str:
    """Return the assistant's text for `system` + `messages` via the configured provider.

    `messages` items are {"role": "user"|"assistant", "content": str}.
    """
    s = get_settings()
    if s.llm_provider == "anthropic":
        return _anthropic_complete(s, system, messages, max_tokens)
    return _openrouter_complete(s, system, messages, max_tokens)


def _openai_client(s):
    from openai import OpenAI

    return OpenAI(api_key=s.openrouter_api_key, base_url=_OPENROUTER_BASE_URL)


def _openrouter_complete(s, system, messages, max_tokens):
    client = _openai_client(s)
    resp = client.chat.completions.create(
        model=s.openrouter_model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, *messages],
    )
    return resp.choices[0].message.content or ""


def _anthropic_complete(s, system, messages, max_tokens):
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    resp = client.messages.create(
        model=s.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in resp.content if block.type == "text")
```

- [ ] **Step 5: Install the openai SDK for local runs**

Run: `python -m pip install "openai>=1.0"`
Expected: installs successfully (also added to requirements.txt in Task 5).

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_llm.py -v`
Expected: PASS (5 passed).

- [ ] **Step 7: Checkpoint**

Run: `python -m pytest -q`
Expected: PASS (whole suite; `get_settings.cache_clear()` in the new tests leaves
a clean cache because conftest re-pins env at import, but if any later test is
sensitive, it already calls `get_settings()` fresh).

---

## Task 3: Refactor report_generator to use `llm`

**Files:**
- Modify: `app/report_generator.py` (`_claude_report` at ~147, gate at ~175)

- [ ] **Step 1: Replace `_claude_report` body**

Replace the whole `_claude_report` function (currently starting `import anthropic`)
with a version that calls `llm.complete`:

```python
def _claude_report(summary: dict) -> tuple[str, dict]:
    text = llm.complete(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(summary)}],
        max_tokens=2000,
    )

    highlights: dict = {}
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            highlights = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("report highlights block was not valid JSON")
        text = text[: match.start()].rstrip()
    return text, highlights
```

- [ ] **Step 2: Update the gate in `generate_weekly_report`**

In `generate_weekly_report`, change:

```python
    if get_settings().anthropic_api_key:
        body, highlights = _claude_report(summary)
    else:
        body, highlights = _fallback_report(summary)
```

to:

```python
    if llm.is_configured():
        body, highlights = _claude_report(summary)
    else:
        body, highlights = _fallback_report(summary)
```

- [ ] **Step 3: Add the import**

At the top of `app/report_generator.py`, add `from app import llm` alongside the
existing imports. `get_settings` may now be unused — if so, remove its import to
keep the file clean; if other code in the file still uses it, leave it.

- [ ] **Step 4: Checkpoint**

Run: `python -m pytest tests/test_reports.py -q`
Expected: PASS (tests run in offline mode → `_fallback_report`, unchanged).

---

## Task 4: Refactor chat_service to use `llm`

**Files:**
- Modify: `app/chat_service.py` (`_claude_reply` at ~95, gate at ~122)

- [ ] **Step 1: Replace `_claude_reply` body**

Replace the whole `_claude_reply` function (currently starting `import anthropic`)
with:

```python
def _claude_reply(context: dict, history: list[ChatMessage], message: str) -> str:
    messages = [
        {"role": "user" if m.role == "user" else "assistant", "content": m.content}
        for m in history
    ]
    messages.append({"role": "user", "content": message})
    return llm.complete(
        system=SYSTEM_PROMPT + json.dumps(context),
        messages=messages,
        max_tokens=1000,
    )
```

- [ ] **Step 2: Update the gate in `send_message`**

In `send_message`, change `if get_settings().anthropic_api_key:` to
`if llm.is_configured():`. Leave the surrounding `try/except` (which stores the
failure string as the reply) exactly as-is.

- [ ] **Step 3: Add the import**

At the top of `app/chat_service.py`, add `from app import llm`. Remove the now-unused
`get_settings` import only if nothing else in the file references it.

- [ ] **Step 4: Checkpoint**

Run: `python -m pytest tests/test_chat.py -q`
Expected: PASS (offline mode → `_fallback_reply`, still returns "OFFLINE MODE").

---

## Task 5: Dependencies and env files

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `.env`

- [ ] **Step 1: Add openai to requirements**

In `requirements.txt`, add a line after `anthropic>=0.40`:

```
openai>=1.0
```

- [ ] **Step 2: Update `.env.example`**

In `.env.example`, replace the `# Claude API` block with a provider block:

```
# LLM provider — "openrouter" (default) or "anthropic"
LLM_PROVIDER=openrouter

# OpenRouter (https://openrouter.ai/keys). Model slug must match OpenRouter's
# catalog exactly, e.g. anthropic/claude-sonnet-4.6
OPENROUTER_API_KEY=
OPENROUTER_MODEL=anthropic/claude-sonnet-4.6

# Anthropic direct (used only when LLM_PROVIDER=anthropic)
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6
```

- [ ] **Step 3: Mirror the block into `.env`**

Apply the same block to `.env`, preserving any real values already present
(leave `OPENROUTER_API_KEY=` empty until the user provides a key).

- [ ] **Step 4: Checkpoint**

Run: `python -m pytest -q`
Expected: PASS (full suite).

---

## Task 6: Production compose overlay + Caddy

**Files:**
- Create: `Caddyfile`
- Create: `docker-compose.prod.yml`

- [ ] **Step 1: Create the Caddyfile**

Create `backend-fastapi/Caddyfile`. Replace `your-domain.example` with the real
domain at deploy time (documented in DEPLOY.md):

```
your-domain.example {
    reverse_proxy api:8000
}
```

- [ ] **Step 2: Create the prod overlay**

Create `backend-fastapi/docker-compose.prod.yml`:

```yaml
# Production overlay. Use with:
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# Adds Caddy (auto HTTPS) in front of the API and stops publishing the API port
# directly to the host — only Caddy exposes 80/443.
services:
  api:
    ports: !reset []

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api

volumes:
  caddy_data:
  caddy_config:
```

- [ ] **Step 3: Validate the merged compose config**

Run: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet && echo VALID`
Expected: `VALID` (the `!reset` tag requires Docker Compose v2.24+; if it errors,
replace `ports: !reset []` with an override that maps to loopback only:
`ports: ["127.0.0.1:8000:8000"]`).

---

## Task 7: Deploy runbook

**Files:**
- Create: `docs/DEPLOY.md`

- [ ] **Step 1: Write DEPLOY.md**

Create `backend-fastapi/docs/DEPLOY.md`:

```markdown
# Deploying Crux to a DigitalOcean Droplet

The backend is Dockerized. Production runs the same compose stack plus a Caddy
reverse proxy that terminates HTTPS with an automatic Let's Encrypt certificate.
No git is used — code is copied to the Droplet with `scp`.

## Prerequisites
- A domain you control.
- A DigitalOcean account.

## 1. Create the Droplet
- Create a Droplet: Ubuntu LTS, Basic plan (1 GB+ RAM is enough), add your SSH key.
- Note its public IP.

## 2. Point DNS at the Droplet
- Add an `A` record: `your-domain -> <droplet IP>`.
- Wait until `ping your-domain` resolves to the IP (Caddy needs this before it
  can issue a certificate).

## 3. Install Docker on the Droplet
SSH in (`ssh root@<droplet IP>`), then:
```
curl -fsSL https://get.docker.com | sh
```
This installs Docker Engine + the Compose plugin.

## 4. Copy the backend to the Droplet
From your PC, in `PersonalApp/`:
```
scp -r backend-fastapi root@<droplet IP>:/srv/crux
```

## 5. Create secrets on the Droplet
On the Droplet, in `/srv/crux`:
- Create `.env` (copy from `.env.example`) and fill in real values:
  - `OPENROUTER_API_KEY=<your key>`
  - `POSTGRES_PASSWORD=<a strong password>`
  - Strava/Spotify client IDs + secrets
  - `FCM_SERVICE_ACCOUNT_JSON_PATH=/srv/secrets/fcm-service-account.json`
- Create `secrets/fcm-service-account.json` (paste the Firebase key) if using push.

## 6. Set the real domain
Edit `Caddyfile` and replace `your-domain.example` with your domain.

## 7. Launch
```
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Caddy fetches the TLS cert automatically on first start (needs ports 80/443 open).

## 8. Verify
```
curl https://your-domain/healthz
```
Expected: `{"status":"ok"}`.

## 9. Update OAuth redirect URIs
In the Strava and Spotify developer dashboards, change the redirect URIs to:
- `https://your-domain/integrations/strava/callback`
- `https://your-domain/integrations/spotify/callback`
Also update `STRAVA_REDIRECT_URI` / `SPOTIFY_REDIRECT_URI` in `.env` to match, then
`docker compose ... up -d` again.

## 10. Firewall
Allow only ports 22, 80, 443 (DigitalOcean Cloud Firewall or `ufw`). Postgres and
Redis stay internal to the compose network — never publish them.

## Updating later
Re-`scp` the changed files and run the compose up command again.
```

---

## Task 8: Point the Android app at HTTPS

**Files:**
- Modify: `android-native/app/src/main/java/com/darius/crux/network/ApiConfig.kt`
- Modify: `android-native/app/src/main/AndroidManifest.xml`

> Do this task only after the backend is deployed and reachable at the domain.

- [ ] **Step 1: Update the base URL**

In `ApiConfig.kt`, set (replace with the real domain):

```kotlin
object ApiConfig {
    // Production backend behind HTTPS.
    // Local dev alternatives: emulator "http://10.0.2.2:8000/",
    // LAN device "http://<pc-lan-ip>:8000/".
    const val BASE_URL = "https://your-domain.example/"
}
```

- [ ] **Step 2: Remove the cleartext flag**

In `AndroidManifest.xml`, delete the line
`android:usesCleartextTraffic="true"` from the `<application>` element (and the
preceding `usesCleartextTraffic` comment). HTTPS no longer needs it.

- [ ] **Step 3: Rebuild and install**

Run (from `android-native/`):
```
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```
Expected: `Success`.

- [ ] **Step 4: Verify on device**

Launch the app; the dashboard should load real data over HTTPS (no "ACQUIRING
SIGNAL…" hang). Confirm with backend logs on the Droplet showing incoming
requests.

---

## Self-Review notes
- Spec Section A (provider abstraction) → Tasks 1–5. Section B (deploy) → Tasks 6–8.
- Deterministic fallback preserved: gates now use `llm.is_configured()`; offline
  tests (`test_chat`, `test_reports`) stay green because no provider key is set in
  the test env (Task 2 Step 1).
- Invalid `claude-sonnet-5` model ID fixed in Task 1.
- Method names consistent across tasks: `llm.complete`, `llm.is_configured`,
  `llm._openai_client`, `llm._openrouter_complete`, `llm._anthropic_complete`.
- OpenRouter model-slug exactness flagged in `.env.example` (Task 5) and DEPLOY.md.
