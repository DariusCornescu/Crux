# Repo playbook — sequential PRs + DigitalOcean

The local history is already built as a stack of branches, one per PR, each
test-green. Your job: push them in order and merge each PR before opening the
next. **Merge with "Create a merge commit" (or "Rebase and merge") — NOT
"Squash"**, otherwise every later PR will show duplicate diffs.

## 0. One-time
```bash
# Create an empty repo on GitHub (e.g. DariusCornescu/Splitrail) — no README.
cd PersonalApp
git remote add origin git@github.com:DariusCornescu/Splitrail.git
```

## 1. Push the vision (this is your "first batch")
```bash
git push -u origin main
```

## 2. PRs, in this exact order
For each branch: push → open PR against `main` → merge → next.

```bash
git push -u origin feat/backend-skeleton      # PR 1: base skeletons
git push -u origin feat/strava-sync           # PR 2
git push -u origin feat/spotify-mood          # PR 3
git push -u origin feat/weekly-reports        # PR 4
git push -u origin feat/chat                  # PR 5
git push -u origin feat/push-notifications    # PR 6
git push -u origin feat/llm-provider-openrouter  # PR 7
git push -u origin feat/production-deploy     # PR 8  <- connect DO after merging this
git push -u origin feat/voice-logs            # PR 9
git push -u origin feat/report-correlations   # PR 10
git push -u origin feat/interference-coaching # PR 11
git push -u origin feat/audio-priming         # PR 12
git push -u origin feat/pacing-model          # PR 13
```
Each PR's description can be its commit message (`git log -1 <branch>`).
Because branches are stacked, GitHub shows only the new diff once the previous
PR is merged. You can push them all upfront; just MERGE in order.

## 3. Connect DigitalOcean App Platform (after merging feat/production-deploy)
1. Edit `.do/app.yaml`: set `repo:` to your actual GitHub repo (TODO(repo)).
2. DO console → Apps → Create App → "Import from spec" (or
   `doctl apps create --spec .do/app.yaml`). Authorize GitHub access.
3. Add encrypted app-level env vars: `LLM_PROVIDER=openrouter`,
   `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=anthropic/claude-sonnet-4.6`,
   Strava/Spotify credentials + redirect URIs pointing at the app's
   `https://<app>.ondigitalocean.app/integrations/<provider>/callback`.
4. First deploy runs migrations automatically (`RUN_MIGRATIONS=true`).
   Verify: `https://<app>.ondigitalocean.app/healthz` → `{"status":"ok"}`.
5. From then on, every merged PR to main auto-deploys — you'll literally watch
   the app grow PR by PR if you connect DO before merging PRs 9-13.
   Scope note: App Platform spec runs the API + managed Postgres only; Celery
   worker/beat need the Droplet path (docs/DEPLOY.md) or extra DO components.
6. Update Android `ApiConfig.BASE_URL` to the app URL, rebuild the APK.

## Never commit
`.env`, `backend-fastapi/secrets/` (your real FCM key lives there — it is
gitignored at both levels; keep it that way), `local.properties`.
