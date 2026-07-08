# Design: Chat v2 (clear history + streaming) · Report graphs · PB purge

Date: 2026-07-08. Approved by Darius ("looks perfect"). Decision on the PB purge:
keep "former national 60m champion" in LLM prompts, drop only the number.

## Scope

### A. Clear chat history
- Backend: `DELETE /chat/history` in `app/routers/chat.py` → deletes all
  `ChatMessage` rows, returns `{"deleted": <n>}`.
- Android: engraved `CLEAR` label in the chat header; tap 1 → turns `SURE?`
  (GateRed) for ~3s; tap 2 → calls the endpoint, empties the local thread.
  No dialogs (MEET SHEET).

### B. Streaming chat replies
- `app/llm.py`: new `stream(system, messages, max_tokens) -> Iterator[str]`
  yielding text deltas. OpenRouter path: OpenAI SDK `stream=True`, yield
  `chunk.choices[0].delta.content or ""`. Anthropic path:
  `client.messages.stream(...)` → `stream.text_stream`.
- `app/chat_service.py`: `stream_message(db, message) -> Iterator[str]` —
  same context/history assembly as `send_message`; persists the user row up
  front, accumulates yielded tokens, persists the assistant row when the
  stream ends (also on LLM mid-stream failure: persist what arrived +
  "— SIGNAL LOST"). Offline (llm not configured): yield the existing
  deterministic fallback as one chunk.
- `app/routers/chat.py`: `POST /chat/stream` → `StreamingResponse`
  (`media_type="text/event-stream"`), events `data: {"t": "<token>"}\n\n`,
  terminated by `data: [DONE]\n\n`. Existing `POST /chat` stays (compat).
- Android: Retrofit can't SSE — the chat repository uses the shared OkHttp
  client directly (build a Request against `ApiConfig.BASE_URL + "chat/stream"`,
  read the response body line-by-line, parse `data:` lines, ignore keepalives,
  stop on `[DONE]`). `ChatViewModel`: optimistic user row (existing pattern) +
  an assistant row appended immediately and mutated as tokens arrive.
  On any streaming failure BEFORE first token: fall back to the non-streaming
  `POST /chat`. After first token: append "— SIGNAL LOST".

### C. Report graphs
- Backend: `GET /reports/{id}/metrics` (404 unknown id) → for each day of
  `[period_start, period_end]`: `{"day", "km" (aerobic distance sum),
  "vert_m" (loaded elevation sum), "mood_valence" (DailySummary), "sessions"
  (total activity count)}` as `{"days": [...]}`. Computed from Activities +
  DailySummary, so it works for all past reports.
- Android: `ReportDetailScreen` gains a `WEEK IN NUMBERS` section between the
  header and the markdown body: three Canvas mini-charts in house style (like
  `MoodTrace`, no chart library): KM/day bars (Steel), VERT/day bars (Scree),
  MOOD line (Ink); null/zero days = gaps; each chart ~48dp tall with an
  engraved label + max-value annotation. Hidden if the metrics call fails.

### D. Forget 6.91
- `app/chat_service.py` SYSTEM_PROMPT + `app/report_generator.py` prompt:
  "(PB 6.91)" removed; identity text stays.
- `app/schemas.py::GateBlock`: `pb` field removed entirely; demo payload in
  `app/routers/dashboard.py` loses `pb=6.91`; `tests/test_dashboard.py`
  updated (assert `"pb" not in d["gate"]`).
- Android: `pb` removed from `GateBlockDTO`/`GateBlock` model and
  `SampleData.kt` (nothing renders it since Dashboard v2).

## Testing
Backend TDD: delete-history endpoint; stream endpoint offline (SSE lines parse,
`[DONE]` terminal, both rows persisted after consumption); `llm.stream` mocked
generator → tokens relayed in order; metrics endpoint shape/404/day-alignment;
PB purge assertions. Android: `assembleDebug` gate.

## Rollout
Merge → droplet pull + compose up → rebuild APK → adb install → verify:
stream a chat reply on the phone, CLEAR works, a report shows charts, chat
never mentions 6.91.

## Risks
- SSE through Caddy: Caddy 2 streams responses by default (`flush_interval`
  auto for text/event-stream) — verify live after deploy; if buffered, set
  `flush_interval -1` on the reverse_proxy block.
- OkHttp read timeout on a slow LLM: use a per-call client with
  `readTimeout(120s)` for the stream request only.
