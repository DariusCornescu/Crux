# Design: Production hosting + OpenRouter LLM provider

Date: 2026-07-05
Scope: Crux backend (`backend-fastapi/`) + Android app (`android-native/`)

## Goal

Two independent-but-related changes to take Crux from a laptop demo to a
hosted app:

1. **LLM provider switch** — route Claude calls through OpenRouter (default)
   instead of the Anthropic SDK, while keeping Anthropic-direct and the existing
   deterministic offline fallback as options.
2. **Hosting** — run the Dockerized backend on a DigitalOcean Droplet behind
   HTTPS, and point the Android app at the public domain.

Volume is one user (weekly report + occasional chat), so cost is negligible;
the driver is flexibility (many models via one OpenRouter key) and getting the
app off localhost.

## Non-goals

- Multi-user auth (the app is intentionally single-user).
- CI/CD, container registry, or orchestration beyond `docker compose`.
- Managed Postgres/Redis — they stay as containers on the Droplet.
- Rewriting the deterministic fallback logic.

---

## Section A — LLM provider abstraction

### Current state
Two call sites talk to the `anthropic` SDK directly:
- `app/report_generator.py::_claude_report` (`client.messages.create`)
- `app/chat_service.py::_claude_reply` (`client.messages.create`)

Both are guarded by `if get_settings().anthropic_api_key:` and fall back to a
deterministic summary when no key is set. Config lives in `app/config.py`.

Known bug to fix: `config.py` sets `anthropic_model = "claude-sonnet-5"`, which
is **not a valid model ID** and would 400 on a live call.

### New module: `app/llm.py`
Single entry point:

```python
def complete(system: str, messages: list[dict], max_tokens: int = 1000) -> str
```

- `messages` is a list of `{"role": "user"|"assistant", "content": str}`.
- Dispatches on `settings.llm_provider`:
  - `"openrouter"` (default): uses the `openai` SDK with
    `base_url="https://openrouter.ai/api/v1"`, `api_key=settings.openrouter_api_key`,
    `model=settings.openrouter_model`. The `system` string is sent as a leading
    `{"role": "system", ...}` message (OpenAI chat format).
  - `"anthropic"`: uses the existing `anthropic` SDK path with
    `model=settings.anthropic_model`, `system=` param.
- Raises on API error; call sites keep their existing `try/except` that stores
  the failure as the reply.

### "Is a provider configured?" check
Replace the current `if anthropic_api_key:` gate with a helper
`llm.is_configured()` that returns true when the selected provider has its key
set. If not configured → existing deterministic fallback runs unchanged.

### Config additions (`app/config.py`)
```python
llm_provider: str = "openrouter"          # "openrouter" | "anthropic"
openrouter_api_key: str = ""
openrouter_model: str = "anthropic/claude-sonnet-4.6"
anthropic_model: str = "claude-sonnet-4-6"   # fix invalid "claude-sonnet-5"
```

### Other edits
- `report_generator._claude_report` and `chat_service._claude_reply` refactored
  to build the `system` + `messages` and call `llm.complete(...)`.
- `requirements.txt` gains `openai>=1.0`.
- `.env` / `.env.example` gain `LLM_PROVIDER`, `OPENROUTER_API_KEY`,
  `OPENROUTER_MODEL`.

### Behavior matrix
| `LLM_PROVIDER` | key set? | result |
|---|---|---|
| openrouter | yes | OpenRouter chat completion |
| openrouter | no | deterministic fallback (offline mode) |
| anthropic | yes | Anthropic SDK completion |
| anthropic | no | deterministic fallback |

Flipping providers is an env-var change + `docker compose up -d`. No code edits.

---

## Section B — Deployment (DigitalOcean Droplet + HTTPS)

### Topology
- One Ubuntu Droplet (~$6–12/mo) with Docker Engine + Compose plugin.
- Existing `docker-compose.yml` services (`db`, `redis`, `api`, `worker`,
  `beat`) run as-is.
- New **Caddy** reverse-proxy service fronts `api`, terminates TLS, and
  auto-provisions Let's Encrypt certificates for the domain. `api` no longer
  publishes port 8000 to the host in prod — only Caddy exposes 80/443.

### Files
- `docker-compose.prod.yml` — overlay adding the `caddy` service (with
  `caddy_data`/`caddy_config` volumes) and production tweaks: drop the `api`
  host port mapping, ensure `restart: unless-stopped` everywhere. Local dev
  keeps using plain `docker-compose.yml` unchanged.
- `Caddyfile` — minimal:
  ```
  your-domain.example {
      reverse_proxy api:8000
  }
  ```
- `docs/DEPLOY.md` — step-by-step runbook (below).

### DNS
An `A` record `your-domain → <droplet IP>`. Caddy needs the domain resolving to
the box before it can issue a cert.

### Secrets
`.env` and `secrets/` are created directly on the Droplet (scp or paste), never
committed. Production `.env` sets real `OPENROUTER_API_KEY`, Strava/Spotify
creds, and `FCM_SERVICE_ACCOUNT_JSON_PATH=/srv/secrets/fcm-service-account.json`.

### Android app
- `ApiConfig.BASE_URL` → `https://your-domain/`.
- Remove `android:usesCleartextTraffic="true"` from `AndroidManifest.xml` (no
  longer needed once traffic is HTTPS; the manifest comment already anticipates
  this). Rebuild + reinstall the APK.

### DEPLOY.md outline
1. Create Droplet (Ubuntu LTS), add SSH key.
2. Point DNS `A` record at the Droplet IP.
3. SSH in; install Docker Engine + Compose plugin.
4. Copy `backend-fastapi/` to the Droplet (git clone or scp).
5. Create `.env` and `secrets/fcm-service-account.json` on the box.
6. Put the real domain in `Caddyfile`.
7. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
8. Verify `https://your-domain/healthz` returns `{"status":"ok"}`.
9. Update Strava/Spotify OAuth redirect URIs to the `https://your-domain/...`
   callback URLs in their dashboards.
10. Rebuild the Android app against the new base URL.

---

## Risks / notes
- OpenRouter model slugs must match its catalog exactly (e.g.
  `anthropic/claude-sonnet-4.6`); wrong slug → 400. Documented in `.env.example`.
- OAuth redirect URIs are registered per-app on Strava/Spotify — moving to a
  domain requires updating them there (step 9), else the connect flow breaks.
- Advanced Anthropic-native features (prompt caching, adaptive thinking) are not
  used through the OpenRouter path — acceptable for this workload.
- Firewall: open only 22, 80, 443 on the Droplet; Postgres/Redis stay internal
  to the compose network (never published).

## Rollout order
1. Section A (provider switch) — testable locally with an OpenRouter key.
2. Section B (deploy) — depends on nothing in A, but do A first so the deployed
   app already has the provider it needs.
