# Phase 6, iteration 3 — audit
Summary: 0 blockers, 2 high, 2 medium, 6 low.

Scope: secrets, privacy and dependency licences (PLAN.md Phase 6, audit), plus a check that the Phase 6 fixes work. Audited `main` at d7c6103 (in sync with `origin/main`). No code was changed.

Commands run:
- `cd backend && source .venv/bin/activate && pytest -q`: 821 passed.
- `python scripts/validate_rules.py`: OK. `python scripts/run_eval.py`: events 456/0/0, budgets 30/0/0, constitutions 21/0/0, year plans 233/0/0 (caught/missed/wrongly flagged).
- `cd frontend && npm run build`: built.
- About ten GET requests to https://greenlight--manasman1.replit.app. I did not guess the passcode and did not type any secret.

## Rule check
| Rule id | Matches source? | Note |
|---|---|---|
| (none changed) | n/a | `git diff 15f8b82 HEAD -- rules` is empty. Phase 6 changed no rule file. `validate_rules.py` reports OK for all 289 rules. |

## What passes
- **Secrets in history.** I scanned 196 commits on `main`, `phase-2/event-packet` and both `origin/` branches with `git log --all -p`. I searched for Anthropic, OpenAI, GitHub, AWS, Slack and Google key patterns, private keys, and database URLs that contain a password. The only database URL with credentials is the test fixture `postgres://u:p@h:5432/db`. The only `.env*` file ever committed is `.env.example`, and its values are blank. No `.db` or `.sqlite` file was ever committed. There are no stashes. `.replit` holds no secrets.
- **Built bundle.** The local `frontend/dist` and the live `/assets/index-DSm4cI-M.js` contain no key, no database URL, no `ANTHROPIC` or `VITE_` value and no absolute path. No source maps are produced.
- **Health check.** The live `/api/health` reports `ai_mode` and `database: ok`. It shows no address, user or path. `public_problems` (`backend/app/api/deps.py:7`) removes server paths.
- **Recordings.** All 101 tracked files in `data/ai_recordings/` store the request as document fingerprints. Their `response_text` quotes only the synthetic demo and test data. No email address, phone number or key was found. Every file on disk is tracked, so nothing untracked is waiting to be committed. The folder is git-ignored by default (`.gitignore:22`).
- **Access to stored club data.** The only routes that return stored club data are the USG reviewer routes, which need the passcode (`backend/app/api/usg.py:47-56`, `hmac.compare_digest` on digests). The club status and withdraw routes need the club's token, and only the token's hash is stored (`usg.py:107-115`). Every other route is stateless. Nothing returns the audit log.
- **Uploaded text.** No route writes an upload to disk. The USG send route drops `documents` before storing (`usg.py:83-87`).
- **Phase 6 fixes.** I reverted a224ea8, ed413de, 3589a0f and cd064d4 in a scratch copy (`git archive HEAD`, then `patch -R`). All four tests in `backend/tests/adversarial/test_phase6_iter2_break.py` fail without the fixes and pass with them. The live-mode replay (`backend/app/ai/client.py:126-131`) is covered by `tests/unit/test_ai_client.py::test_live_mode_replays_a_saved_response_without_calling_the_api`, which uses an SDK client that fails if it is called.
- **Licences.** `LICENSE` is MIT. No dependency is GPL or AGPL.

## Findings

### [high] The live link runs code from before the Phase 6 fixes
Where: live deployment; compare `backend/app/api/health.py` (commit 5f4a4c4) and `backend/app/site.py:33` (commit cd064d4).
Problem: The live site does not match `main`. Its `/api/health` has no `database_kind` field, which was added in 5f4a4c4. `/assets/does-not-exist-x.js` returns `200 text/html`; after cd064d4 it should be a 404. So the live site also lacks:
- the refusal of a second USG approval (a224ea8),
- quote reading in a worker thread (ed413de),
- the `init_db` retry (3589a0f).

We also cannot tell from `/health` whether the live site uses Postgres or a SQLite file that a redeploy erases.
Expected: the exit criteria are judged on the live link, so it should run the code being closed.
Reproduce:
1. `curl -s https://greenlight--manasman1.replit.app/api/health`. The JSON has no `database_kind` key.
2. `curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://greenlight--manasman1.replit.app/assets/does-not-exist-x.js` prints `200 text/html; charset=utf-8`.

Why it matters: the iteration 2 fixes protect the demo (one visitor stalling the others, a blank page after a redeploy, an instance that fails to start) but they are not live.
Suggested fix: redeploy from `main`. Confirm that `/api/health` shows `"database_kind": "postgresql"` and the missing-asset request returns 404. Then rerun the demo journey three times.

### [high] The USG step of the demo journey is closed on the live link
Where: `backend/app/api/usg.py:47-52`; `docs/PROGRESS.md:13,128`.
Problem: `USG_REVIEWER_KEY` is not set on the deployment, so every reviewer route answers 503. The 2:25 step of PROJECT_CONTEXT section 11 (queue, drafted denial reason, "why applications fail" chart) cannot run on the live link. This was found in iteration 1 (H1) and is still open.
Reproduce: `curl -s -w "\n%{http_code}\n" https://greenlight--manasman1.replit.app/api/usg/queue` returns `{"detail":{"message":"The USG screen is not set up on this server (USG_REVIEWER_KEY)."}}` with status 503.
Why it matters: the first exit criterion (the full demo journey on the live link) cannot pass.
Suggested fix: a person adds a passcode of at least 12 characters to Replit secrets and redeploys. It must not be any value already in the repository (`test-reviewer-passcode`, `break-passcode-123`, `break-passcode-phase6`, `verify-passcode-123`, `wrong-passcode-123`, or the values in the untracked `.claude/launch.json`).

### [medium] Any visitor can make unlimited paid Claude calls on the live key
Where: `backend/app/api/money.py:102-160` (`/money/read`: up to 10 files of 20 MB plus pasted text, one model call per document), `/money/fund`, `/money/draft`, `/events/parse`, `/plans/read-events`, `/constitution/check`, `/gap/email`; `backend/app/ai/client.py:131-134`.
Problem: The live site runs `AI_MODE=live` (see `/api/health`). Any input without a recording goes to the Claude API on the team's key. No route has a per-client limit, a global daily budget, or an automatic switch to recorded mode. The no-rate-limit issue was noted as low in Phase 2 when the API was local only; it now costs money.
Expected: a public, anonymous site using a paid key limits how much one visitor can spend.
Reproduce: read the routes above. None has a limiter (`grep -rniE "rate.?limit|throttl" backend/app` finds only the `RateLimitError` handling). Do not run this against the live site.
Why it matters: someone could run up the key's bill or exhaust its rate limit during judging. Once the key is rate-limited, the demo depends entirely on the recorded fallback.
Suggested fix: add a small in-process limit per client IP and a global daily cap on live calls. Past the cap, answer the same way as a missing recording (yellow, "type the lines in"). Or set `AI_MODE=recorded` on the live site after judging.

### [medium] The audit log keeps every anonymous visitor's document quotes indefinitely, and nothing is marked personal
Where: `backend/app/ai/client.py:66-77` (`audit_payload` keeps `evidence`); `backend/app/services/quote_intake.py:167-169,227`; `backend/app/api/recognition.py:46-55`; `backend/app/services/event_intake.py:153`; `backend/app/services/fund_reading.py:55`; `backend/app/services/application_draft.py:72`; `backend/app/services/gap_email.py:76`.
Problem: Every AI output is written to `audit_log` with `club_id=None`. That includes the `evidence` field, which quotes up to 300 characters of the uploaded quote, invoice, constitution or event text. On the live site this is one shared production database for all anonymous visitors, with no retention or deletion. The `PERSONAL` blanking in `app/ai/schemas.py` exists but blanks nothing: `grep -rn "PERSONAL\]" backend/app` finds only the docstring at `app/ai/schemas.py:39`. A vendor invoice or quote with a "Bill to" name, phone number or email is therefore stored verbatim.
Expected: PROJECT_CONTEXT section 9 says "Only public rules and files the officer uploads. No student records. Traveller details are not stored", and "A club's data is private to the club". The code's own docstring says the log is "private to the club", but these rows belong to no club.
Reproduce: with `AI_MODE=recorded`, POST `/money/read` with pasted text whose recording includes `evidence`, then `SELECT payload FROM audit_log WHERE subject_type='quote_document'`. The `output.documents[].lines[].evidence` (or equivalent) holds the document's words.
Why it matters: personal details from uploads build up in a database that no club owns and nobody purges. No route exposes them now, but a database leak or a later admin view would.
Suggested fix: for rows with no club, store only the request key, model, task and a hash of the output, not `evidence`. Or mark the evidence fields `PERSONAL`, or add a retention purge (for example 7 days) to start-up.

### [low] The API documentation is public on the live site
Where: `backend/app/site.py:41` turns off docs only on the outer app; `backend/app/main.py:50-54` keeps FastAPI's defaults on the mounted API.
Problem: `/api/docs` and `/api/openapi.json` return 200 on the live link and list every route, including the USG reviewer routes and their header. This is probably not what `docs_url=None` on the site was meant to achieve.
Reproduce: `curl -s -o /dev/null -w "%{http_code}\n" https://greenlight--manasman1.replit.app/api/openapi.json` prints 200.
Suggested fix: when `--site` is used (or `APP_ENV=production`), create the API with `docs_url=None, redoc_url=None, openapi_url=None`. Add a test that `/api/openapi.json` returns 404 from `create_site`.

### [low] Third-party licence notices are stripped from the shipped bundle
Where: `frontend/dist/assets/index-*.js` and `index-*.css`; `frontend/vite.config.*`; no NOTICE file in the repository.
Problem: The production bundle includes React, React DOM, scheduler, React Router and Tailwind's preflight CSS, all MIT. Minification removes their `@license` and `/*!` headers (`grep -c license dist/assets/*.js` gives 0, and the CSS has no Tailwind header). The MIT licence asks that the copyright and permission notice go with copies, and the deployed site distributes these copies.
Reproduce: `cd frontend && npm run build && grep -c "@license" dist/assets/*.js` prints 0.
Suggested fix: add a `THIRD_PARTY_NOTICES.md` (generated from `node_modules/*/package.json` and `LICENSE` files for the production dependencies) and link it from the README or the About page. Or keep the legal comments in the build.

### [low] Copyleft and attribution dependencies: allowed as used, but not recorded
Where: `backend/requirements.txt:12` (`psycopg[binary]`); installed metadata; `frontend/package-lock.json`.
Problem:
- `psycopg` and `psycopg-binary` 3.3.9 are LGPL-3.0-only. Using them as unmodified, separately installed libraries is fine for an MIT project. The binary wheel also bundles libpq (PostgreSQL licence) and OpenSSL (Apache-2.0).
- `certifi` is MPL-2.0. The dev-only, optional `lightningcss` packages are MPL-2.0. The dev-only `caniuse-lite` is CC-BY-4.0, and its data is not shipped in the bundle.
- None is vendored or modified, so nothing blocks publishing. The README's Licence section does not mention them.

Licence counts:
- Python: everything else is MIT, BSD, Apache-2.0, MIT-0, PSF-2.0 or ISC.
- npm: 141 MIT, 5 ISC, 3 Apache-2.0, 1 BSD-3-Clause, 1 0BSD, 1 BlueOak-1.0.0, 12 MPL-2.0 (lightningcss and its platform builds), 1 CC-BY-4.0.
- No dependency has a missing or unknown licence.

Suggested fix: one line in the README Licence section, or in the notices file above: "psycopg is LGPL-3.0, used unmodified as a separate library; certifi is MPL-2.0".

### [low] Python transitive dependencies are not pinned
Where: `backend/requirements.txt`; `scripts/deploy/build.sh:10-11` installs fresh on every deploy.
Problem: Only top-level packages are pinned. Each redeploy can resolve different versions of anyio, starlette, certifi and others. That can change their licences or behaviour without any change in the repository. `npm ci` uses the lock file, but pip has no equivalent here.
Suggested fix: commit a `requirements.lock` (for example `pip freeze` from a clean venv) and install from it in `build.sh`.

### [low] `.claude/launch.json` is neither ignored nor committed, and holds local passcodes and paths
Where: `/Users/dalvi/Downloads/Projects/greenlight/.claude/launch.json`; `.gitignore:43` ignores only `.claude/settings.local.json`.
Problem: The file is untracked (it appears in `git status`). It contains `USG_REVIEWER_KEY=demo-reviewer-passcode`, `USG_REVIEWER_KEY=local-demo-passcode`, absolute home-directory paths and scratchpad database paths. A `git add -A` at phase close would commit it.
Reproduce: `git check-ignore -v .claude/launch.json` prints nothing; `git status --short` lists it.
Suggested fix: add `.claude/launch.json` to `.gitignore`.

### [low] Quote intake still parses Word files on the event loop; withdrawn and anonymous rows are kept
Where: `backend/app/api/money.py:143` (`_docx_text(data)` runs before `run_in_threadpool`); `backend/app/api/usg.py:128-137`; `backend/app/api/money.py:237-244`.
Problem:
- The ed413de fix moved the model call to a worker thread, but parsing a Word file of up to 20 MB with python-docx still runs on the event loop. A large .docx briefly stalls every other visitor.
- Withdrawing an application keeps its full `request` and `report` (already noted as low in Phase 5).
- `/money/draft/approve`, `/gap/email/approve` and `/handover/approve` accept anonymous, unlimited audit-log writes.

Suggested fix:
- Call `run_in_threadpool(_docx_text, data)`.
- On withdraw, set `request` and `report` to `{}`, keeping only the reference, status and timestamps.
- Cover the approval routes with the limiter from the medium finding above.
