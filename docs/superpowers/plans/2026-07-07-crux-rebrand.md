# Crux Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full rebrand Splitrail → Crux: user-facing strings, docs, Android package `com.darius.splitrail → com.darius.crux`, infra identifiers, and the GitHub repo.

**Architecture:** Three phased rename passes (backend → Android → docs/repo), each with a hard verification gate before the next: pytest suite, `gradlew assembleDebug`, then a repo-wide `rg -i splitrail` sweep. Case-sensitive scripted replacement (`Splitrail→Crux`, `splitrail→crux`, `SPLITRAIL→CRUX`) plus `git mv` for the package dir and three class files so history follows.

**Tech Stack:** PowerShell 7 for scripted replaces, git/gh, pytest, Gradle.

**Spec:** `docs/superpowers/specs/2026-07-07-crux-rebrand-design.md`

**Branch:** `feat/rebrand-crux` (already created; spec committed).

**Global exclusions — never touch:** `.git/`, `.claude/` (worktrees), `backend-fastapi/.pytest_cache/`, `__pycache__/`, `android-native/.gradle/`, `android-native/**/build/`, and the two rebrand docs themselves (`docs/superpowers/specs/2026-07-07-crux-rebrand-design.md`, `docs/superpowers/plans/2026-07-07-crux-rebrand.md`) — replacing "Splitrail" inside them would destroy their meaning.

---

### Task 1: Backend rename (infra identifiers + user-facing strings)

**Files:**
- Modify: `backend-fastapi/docker-compose.yml` (POSTGRES_USER/PASSWORD/DB, pg_isready)
- Modify: `backend-fastapi/.env.example` (DATABASE_URL, POSTGRES_PASSWORD)
- Modify: `backend-fastapi/app/config.py` (database_url default)
- Modify: `backend-fastapi/app/main.py:29` (`FastAPI(title="Splitrail API", ...)`)
- Modify: `backend-fastapi/app/chat_service.py:24` (system prompt)
- Modify: `backend-fastapi/app/report_generator.py:25` (system prompt)
- Modify: `backend-fastapi/app/push.py:42` (`SPLITRAIL — WEEKLY REPORT`)
- Modify: `backend-fastapi/app/routers/integrations.py:78,112` ("return to Splitrail")
- Modify: `backend-fastapi/app/workers/celery_app.py:8` (`Celery("splitrail", ...)`)
- Modify: `backend-fastapi/app/calendar_sync.py:30` (`_SUBJECT_SALT`)
- Modify: `backend-fastapi/tests/conftest.py:11` (test DB path)
- Modify: `backend-fastapi/docs/DEPLOY.md` (title + paths)

- [ ] **Step 1: Scripted case-sensitive replace across backend-fastapi**

```powershell
$files = Get-ChildItem backend-fastapi -Recurse -File -Include *.py,*.yml,*.md,*.example |
  Where-Object { $_.FullName -notmatch '\\(\.pytest_cache|__pycache__)\\' }
foreach ($f in $files) {
  $t = Get-Content $f.FullName -Raw
  $n = $t -creplace 'Splitrail','Crux' -creplace 'splitrail','crux' -creplace 'SPLITRAIL','CRUX'
  if ($n -ne $t) { Set-Content $f.FullName $n -NoNewline }
}
```

- [ ] **Step 2: Verify zero remaining references in backend**

Run: `rg -i splitrail backend-fastapi --glob '!.pytest_cache/**'`
Expected: no output (exit code 1).

Spot-check the salt landed as versioned: `rg 'crux-calendar-v1' backend-fastapi/app/calendar_sync.py` → 1 hit.

- [ ] **Step 3: Run the backend test suite**

Run: `cd backend-fastapi && python -m pytest -q`
Expected: all tests PASS (the drift-guard test in `tests/test_migrations.py` included — the rename touches no models, so no migration is needed).

- [ ] **Step 4: Note on local Docker volume (no action in repo)**

If a local dev `pgdata` volume exists from previous runs, the renamed `POSTGRES_USER/DB` won't re-init it. Dev-only data: `cd backend-fastapi && docker compose down -v` next time compose is used. Do NOT run this as part of the plan — just be aware.

- [ ] **Step 5: Commit**

```powershell
git add backend-fastapi
git commit -m "refactor: rename backend Splitrail -> Crux (strings, infra ids, salt, test db)"
```

---

### Task 2: Android package + class rename

**Files:**
- Move: `android-native/app/src/main/java/com/darius/splitrail/` → `.../com/darius/crux/` (git mv, whole tree)
- Move: `SplitrailApp.kt` → `CruxApp.kt`, `network/SplitrailApi.kt` → `network/CruxApi.kt`, `push/SplitrailMessagingService.kt` → `push/CruxMessagingService.kt`
- Modify: all `.kt` files under the moved tree (package/import/class refs)
- Modify: `android-native/app/build.gradle.kts:10,14` (namespace, applicationId)
- Modify: `android-native/settings.gradle.kts:16` (rootProject.name)
- Modify: `android-native/app/src/main/AndroidManifest.xml:8,13,17,26` (.SplitrailApp, Theme.Splitrail ×2, .push.SplitrailMessagingService)
- Modify: `android-native/app/src/main/res/values/strings.xml:3` (app_name)
- Modify: `android-native/app/src/main/res/values/themes.xml:3` (Theme.Splitrail)

- [ ] **Step 1: git mv the package directory and the three class files**

```powershell
git mv android-native/app/src/main/java/com/darius/splitrail android-native/app/src/main/java/com/darius/crux
git mv android-native/app/src/main/java/com/darius/crux/SplitrailApp.kt android-native/app/src/main/java/com/darius/crux/CruxApp.kt
git mv android-native/app/src/main/java/com/darius/crux/network/SplitrailApi.kt android-native/app/src/main/java/com/darius/crux/network/CruxApi.kt
git mv android-native/app/src/main/java/com/darius/crux/push/SplitrailMessagingService.kt android-native/app/src/main/java/com/darius/crux/push/CruxMessagingService.kt
```

- [ ] **Step 2: Scripted case-sensitive replace across android-native text files**

Covers `package`/`import` lines, `namespace`/`applicationId`, `rootProject.name`, class names (`SplitrailApp→CruxApp`, `SplitrailApi→CruxApi`, `SplitrailMessagingService→CruxMessagingService`, `SplitrailTheme→CruxTheme`, `SplitrailTypography→CruxTypography`), `Theme.Splitrail→Theme.Crux`, and `app_name`.

```powershell
$files = Get-ChildItem android-native -Recurse -File -Include *.kt,*.kts,*.xml |
  Where-Object { $_.FullName -notmatch '\\(\.gradle|build)\\' }
foreach ($f in $files) {
  $t = Get-Content $f.FullName -Raw
  $n = $t -creplace 'Splitrail','Crux' -creplace 'splitrail','crux'
  if ($n -ne $t) { Set-Content $f.FullName $n -NoNewline }
}
```

- [ ] **Step 3: Verify zero remaining references + package/dir consistency**

Run: `rg -i splitrail android-native --glob '!.gradle/**' --glob '!**/build/**'`
Expected: no output.

Run: `rg --files-without-match 'package com\.darius\.crux' android-native/app/src/main/java --glob '*.kt'`
Expected: no output (every Kotlin file declares the new package).

- [ ] **Step 4: Build the debug APK**

Run: `cd android-native && .\gradlew.bat assembleDebug`
Expected: `BUILD SUCCESSFUL`. (First run may download Gradle — allow several minutes.)

- [ ] **Step 5: Commit**

```powershell
git add -A android-native
git commit -m "refactor: rename Android package com.darius.splitrail -> com.darius.crux, classes Splitrail* -> Crux*"
```

---

### Task 3: Docs + DO app spec

**Files:**
- Modify: `README.md` (title + descriptions)
- Modify: `docs/DESIGN.md`, `docs/PROGRESS.md`, `docs/BACKLOG.md`, `docs/REPO-PLAYBOOK.md`, `docs/superpowers/MORNING-CHECKLIST.md`
- Modify: `docs/superpowers/specs/*.md`, `docs/superpowers/plans/*.md` — EXCEPT the two `2026-07-07-crux-rebrand*` files
- Modify: `.do/app.yaml:10,15,16` (`name: splitrail`, repo comment, `repo: DariusCornescu/Splitrail` → `DariusCornescu/Crux`)

- [ ] **Step 1: Scripted replace across docs + app.yaml**

```powershell
$files = @(Get-Item README.md, .do/app.yaml) +
  (Get-ChildItem docs -Recurse -File -Include *.md |
   Where-Object { $_.Name -notmatch '2026-07-07-crux-rebrand' })
foreach ($f in $files) {
  $t = Get-Content $f.FullName -Raw
  $n = $t -creplace 'Splitrail','Crux' -creplace 'splitrail','crux' -creplace 'SPLITRAIL','CRUX'
  if ($n -ne $t) { Set-Content $f.FullName $n -NoNewline }
}
```

- [ ] **Step 2: Repo-wide final sweep**

Run:
```powershell
rg -i splitrail --glob '!.claude/**' --glob '!docs/superpowers/specs/2026-07-07-crux-rebrand-design.md' --glob '!docs/superpowers/plans/2026-07-07-crux-rebrand.md' --glob '!backend-fastapi/.pytest_cache/**' --glob '!android-native/.gradle/**' --glob '!android-native/**/build/**'
```
Expected: no output. Any hit = a missed file; fix it with the same three-way case replace and re-run.

- [ ] **Step 3: Commit**

```powershell
git add README.md docs .do
git commit -m "docs: rename Splitrail -> Crux across docs and DO app spec"
```

---

### Task 4: GitHub repo rename

**Files:** none (remote operation + local remote URL).

- [ ] **Step 1: Rename the GitHub repo**

Run: `gh repo rename Crux`
Expected: confirmation that `DariusCornescu/Splitrail` → `DariusCornescu/Crux`; `gh` updates the local `origin` remote automatically. GitHub keeps a redirect from the old URL.

- [ ] **Step 2: Verify the remote**

Run: `git remote -v`
Expected: `origin  https://github.com/DariusCornescu/Crux.git` (fetch/push). If it still shows Splitrail: `git remote set-url origin https://github.com/DariusCornescu/Crux.git`.

- [ ] **Step 3: Note the manual leftover (no action)**

The local working folder `C:\Users\dariu\Documents\GithubRepos\Splitrail` stays as-is; renaming it mid-session breaks tool paths. User renames it to `Crux` after the branch merges (documented in the spec, out of automation scope).

---

## Verification summary (gates in order)

1. Task 1 → `python -m pytest -q` green.
2. Task 2 → `gradlew.bat assembleDebug` BUILD SUCCESSFUL.
3. Task 3 → repo-wide `rg -i splitrail` sweep empty (with documented exclusions).
4. Task 4 → `git remote -v` points at `Crux`.
