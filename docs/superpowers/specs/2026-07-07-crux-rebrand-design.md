# Design: Rebrand Splitrail → Crux (full rebrand)

Date: 2026-07-07

## Summary

Rename the project from **Splitrail** to **Crux**. "Crux" is the pivotal move on
a climb and idiomatically "the thing that matters most" — fitting for an app that
distills many life signals (training, mood, wearables, work/stress) into one
picture. This is a **full rebrand**: user-facing strings, docs, the Android
package `com.darius.splitrail → com.darius.crux`, infra identifiers, and the
GitHub repo/local folder.

Nothing is deployed yet (the DO deploy plan is still pending), so there is no
production database, no committed Firebase config, and no hashed calendar data to
migrate. Renaming infra identifiers now is therefore free of migration risk.

## Scope

### A. Cosmetic (pure string replace)
- Android display name: `android-native/app/src/main/res/values/strings.xml`
  (`app_name`), `android-native/settings.gradle.kts` (`rootProject.name`).
- Backend user-facing strings:
  - `backend-fastapi/app/main.py` — FastAPI `title="Splitrail API"`.
  - `backend-fastapi/app/chat_service.py` — system prompt mentions "Splitrail".
  - `backend-fastapi/app/report_generator.py` — system prompt mentions "Splitrail".
  - `backend-fastapi/app/push.py` — `title="SPLITRAIL — WEEKLY REPORT"`.
  - `backend-fastapi/app/routers/integrations.py` — two "return to Splitrail" notes.
- Docs: `README.md`, `docs/DESIGN.md`, `docs/PROGRESS.md`, `docs/BACKLOG.md`,
  `docs/REPO-PLAYBOOK.md`, `docs/superpowers/MORNING-CHECKLIST.md`,
  `docs/superpowers/specs/*`, `docs/superpowers/plans/*`, `backend-fastapi/docs/DEPLOY.md`.
- `.do/app.yaml` — `name: splitrail`.

### B. Android package rename `com.darius.splitrail → com.darius.crux`
- `git mv` source dir `android-native/app/src/main/java/com/darius/splitrail/`
  → `.../com/darius/crux/` (preserves history).
- Update `package` + `import` statements in every Kotlin file (~50 files).
- `android-native/app/build.gradle.kts` — `namespace` and `applicationId`.
- Class + resource renames:
  - `SplitrailApp` → `CruxApp` (file, class, AndroidManifest `android:name`).
  - `SplitrailApi` → `CruxApi` (file, class, references in RetrofitClient/repos).
  - `SplitrailMessagingService` → `CruxMessagingService` (file, class, manifest).
  - `Theme.Splitrail` → `Theme.Crux` (`themes.xml`, `AndroidManifest.xml`,
    `ui/theme/Theme.kt`).

### C. Infra identifiers (renamed — decision confirmed)
- `backend-fastapi/docker-compose.yml` — `POSTGRES_USER`, `POSTGRES_DB`,
  `POSTGRES_PASSWORD` default, `pg_isready -U` healthcheck.
- `backend-fastapi/.env.example` — `DATABASE_URL`, `POSTGRES_PASSWORD` default.
- `backend-fastapi/app/config.py` — `database_url` default.
- `backend-fastapi/app/workers/celery_app.py` — `Celery("splitrail", ...)`.
- `backend-fastapi/app/calendar_sync.py` — `_SUBJECT_SALT = b"splitrail-calendar-v1:"`
  → `b"crux-calendar-v1:"` (safe: no hashed data exists yet).
- `backend-fastapi/tests/conftest.py` — test DB path `splitrail_test.db`.

### D. Repo + folders
- GitHub repo `DariusCornescu/Splitrail` → `Crux` via `gh repo rename Crux`
  (GitHub keeps a redirect from the old URL).
- `.do/app.yaml` `repo:` field → `DariusCornescu/Crux`.
- Local top-level folder rename is optional/manual (breaks in-flight tool paths);
  left to the user to do after the branch merges. Documented, not automated.

## Out of scope
- Buying/wiring the domain (separate, tracked in the deploy plan; OAuth redirect
  URIs follow the domain, not the app name).
- Setting up Firebase — package id `com.darius.crux` will be registered when FCM
  is wired up (step-7 setup); no `google-services.json` exists to migrate.

## Verification (phased; each gate must pass before the next)
1. **Backend** (cosmetic + infra): `cd backend-fastapi && python -m pytest -q`
   — full suite incl. the migration drift-guard stays green.
2. **Android** (package/dir/class): `cd android-native && ./gradlew assembleDebug`
   — compiles and builds the debug APK.
3. **Docs + repo**: `rg -i splitrail` returns only intentional historical
   mentions (if any); `.do/app.yaml` points at the renamed repo.

## Risks
- **Missed reference in package rename** → compile failure, caught by
  `assembleDebug` gate.
- **Stray lowercase `splitrail`** in infra strings → caught by a final
  `rg -i splitrail` sweep.
- **Repo rename** breaks the local `origin` remote URL; re-point with
  `git remote set-url` after `gh repo rename` (GitHub's redirect also covers it).
