"""GitHub contribution sync — coding treated as another discipline.

No OAuth. With a personal-access token we read the canonical contribution
calendar via the GraphQL contributionsCollection (exact per-day counts, incl.
private contributions if the token allows). Without a token we approximate from
the public events REST feed (recent public activity only). Either way we store
per-day counts in daily_contributions; `source` records which path produced them.
Best-effort like spotify/ReccoBeats — an HTTP failure degrades to zero rows and
never crashes the beat or the endpoint.
"""
import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import DailyContribution, OAuthToken

logger = logging.getLogger(__name__)

PROVIDER = "github"
WINDOW_DAYS = 371  # ~53 weeks — the GitHub contribution-calendar span
_EVENTS_MAX_PAGES = 3  # public feed caps at ~300 events

_GRAPHQL = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def _fetch_graphql(base_url: str, login: str, token: str,
                   since: datetime, until: datetime) -> dict[date, int]:
    resp = httpx.post(
        f"{base_url}/graphql",
        headers={"Authorization": f"bearer {token}"},
        json={"query": _GRAPHQL, "variables": {
            "login": login, "from": since.isoformat(), "to": until.isoformat()}},
        timeout=30,
    )
    resp.raise_for_status()
    weeks = (resp.json()["data"]["user"]["contributionsCollection"]
             ["contributionCalendar"]["weeks"])
    counts: dict[date, int] = {}
    for wk in weeks:
        for d in wk["contributionDays"]:
            counts[date.fromisoformat(d["date"])] = int(d["contributionCount"])
    return counts


def _fetch_public_events(base_url: str, login: str, since: datetime) -> dict[date, int]:
    counts: Counter = Counter()
    for page in range(1, _EVENTS_MAX_PAGES + 1):
        resp = httpx.get(
            f"{base_url}/users/{login}/events/public",
            params={"per_page": 100, "page": page},
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for ev in batch:
            created = ev.get("created_at")
            if not created:
                continue
            day = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
            if day >= since.date():
                counts[day] += 1
        if len(batch) < 100:
            break
    return dict(counts)


def sync(db: Session) -> int:
    s = get_settings()
    login = s.github_username
    if not login:
        raise RuntimeError("github is not configured (GITHUB_USERNAME)")

    until = datetime.now(timezone.utc)
    since = until - timedelta(days=WINDOW_DAYS)
    source = "graphql" if s.github_token else "events"
    try:
        if s.github_token:
            counts = _fetch_graphql(s.github_api_base_url, login, s.github_token, since, until)
        else:
            counts = _fetch_public_events(s.github_api_base_url, login, since)
    except Exception as e:  # best-effort: degrade, do not crash the beat/endpoint
        logger.warning("github sync failed (%s): %s", source, e)
        counts = {}

    updated = 0
    for day, count in counts.items():
        row = db.scalar(select(DailyContribution).where(DailyContribution.day == day))
        if row is None:
            db.add(DailyContribution(day=day, count=count, source=source))
        else:
            row.count = count
            row.source = source
        updated += 1

    token = db.scalar(select(OAuthToken).where(OAuthToken.provider == PROVIDER))
    if token is None:
        token = OAuthToken(provider=PROVIDER, access_token="github")  # connection registry row
        db.add(token)
    token.athlete_id = login
    token.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("github sync: %d days (%s)", updated, source)
    return updated
