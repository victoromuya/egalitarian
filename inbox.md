# Inbox — last session recap

Read this first when picking work back up. Written at the end of the session that built the backend models, auth, enrollment, and exam grading.

## What was done

1. **Database models created** for all apps — `Course`/`Enrollment` (courses), `Event`/`EventRegistration` (events), `Exam`/`Question`/`Choice`/`Submission`/`Answer`/`Certificate` (exams), `Profile` (accounts), `Notification` (core). Migrations generated and applied against `db.sqlite3`.
2. **Sample data seeded via data migrations** (not just hardcoded in views anymore) — `courses/migrations/0002_seed_courses.py`, `events/migrations/0002_seed_events.py`, `exams/migrations/0002_seed_exam.py` (seeds one real exam, on the "Web Development with Django" course only — other courses have no `Exam` row yet).
3. **Real login/register/logout wired up** in `accounts/views.py` — `authenticate()`/`login()`, `User.objects.create_user()` with password validation, duplicate-username check. `Profile` auto-created via a `post_save` signal (`accounts/signals.py`), registered in `accounts/apps.py`.
4. **Real course enrollment lifecycle** — `courses/views.py enroll()` creates real `Enrollment` rows, redirects to a WhatsApp deep link (`settings.WHATSAPP_NUMBER`, currently a placeholder `2348000000000` — needs the real number) for paid courses, auto-marks free courses paid.
5. **Events views** also switched from hardcoded dicts to the real `Event`/`EventRegistration` models, including hard-cutoff capacity enforcement and the same WhatsApp-redirect pattern for paid events.
6. **`core/views.py`** — `home()`, `dashboard()`, `notifications()` now query real `Course`/`Event`/`Enrollment`/`Notification` models instead of hardcoded lists.
7. **Exam paid-access gating** — `exams/views.py` checks `Enrollment.is_paid` server-side before rendering `exam_take`/accepting `submit_exam`; unpaid users are redirected to the course detail page with a message. Verified live: unpaid → 302 redirect away from exam; paid → exam renders.
8. **Real exam submission + auto-grading + certificates** — added `submit_exam` view that grades MCQ answers against `Choice.is_correct`, creates `Submission`+`Answer` rows, computes a percentage score, and on a pass calls `exams/certificates.py` (`reportlab`-based, added to `requirements.txt`) to generate and attach a PDF `Certificate`. Also fires an in-app `Notification` on both pass and fail. `exam_take.html` was converted from a JS-only "redirect on click" mock into a real `<form method="post">` that POSTs answers; the countdown timer now auto-submits the real form on expiry instead of just navigating to the result page.
9. Verified end-to-end via live HTTP calls (not just `manage.py check`): register → login → enroll (free + paid) → WhatsApp redirect → manually toggle `is_paid` → gate exam access → submit real answers → confirm `Submission.score == 100`, `passed == True`, and a `Certificate` PDF file was actually written to `media/certificates/`.
10. **`CLAUDE.md` design log updated**: admins (`is_staff`) now act as instructors for course/event content authoring (per your explicit instruction) — this does **not** reintroduce human exam grading; auto-grading is unchanged. No new `Instructor` model was created, just a permission note on the existing admin role.

## Known issue — RESOLVED (2026-07-06)

The missing "Download Certificate PDF" link was root-caused and fixed. The single-attempt case actually rendered fine on a fresh request (`hasattr` was not the culprit; the original live-page failure was most likely a stale dev-server process). The real, reproducible bug: `exam_result()` and `certificate_download()` looked for a certificate **only on the latest submission**, so any failed retake after a pass made the earned certificate vanish from the result page and 404 the download URL. Fixed by adding `_get_certificate_or_none(user, exam)` in `exams/views.py`, which queries `Certificate` across all of the user's submissions for the exam; both views now use it, and `exam_result.html` also shows the download link on the failed-retake branch when a certificate exists. Verified via test client: pass page shows link; failed-retake page shows fail UI + link; download returns 200 `application/pdf`.

## Task queue (tracked in the session's TaskList, ids stable across this file)

- [x] #1 Design and create DB models
- [x] #2 Wire up real login/register/logout
- [x] #3 Implement real course enrollment lifecycle
- [x] #4 Add paid-access gating on course content and exams — done; the certificate-link display bug that was holding this open is resolved (see above)
- [x] #5 Implement exam auto-grading and PDF certificate generation — done. Cleanup pass over `exams/views.py`/`certificates.py` completed 2026-07-06: extracted `_get_paid_enrollment_or_none`/`_latest_submission`/`_get_certificate_or_none` helpers, deduped the payment-gate message, fixed an N+1 in `exam_result()` (`select_related('selected_choice')`), replaced hardcoded notification links with `reverse()`, deduped the pass/fail `Notification` creation, and in `certificates.py` switched `update_or_create(defaults={})` → `get_or_create` and now delete the old PDF before regenerating (no more orphaned files on retakes). Verified via test client: take/result/download all 200, link renders, PDF served.
- [x] #6 Wire up in-app notifications — done 2026-07-06. "Mark all as read" is now a real POST form → `core/views.py mark_all_notifications_read()` (`@require_POST`, redirects back to notifications). Added `courses/signals.py` (wired in `courses/apps.py ready()`): notification on enrollment creation (free = full-access message, paid = pay-via-WhatsApp message) and on `is_paid` flipping False→True (detected via `pre_save` diff, so it also fires when an admin flips it in Django admin — no view dependency, no duplicate on redundant saves). Event registrations intentionally get no notifications (no `User` link, per design). Verified via test client: POST 302 + unread→0, GET 405, enrollment/payment signals create the right messages.
- [x] #7 Register models in Django admin, add admin course/event authoring — done 2026-07-06. All five apps' `admin.py` filled in. Design decisions: (a) "admins are instructors" implemented as plain Django admin registration — `Course`/`Event` fully authorable (slug prepopulated from title, `created_by` auto-set to the logged-in admin on create); (b) immutability enforced: `Course.price` and `Event.price`/`capacity` are readonly on the change form (editable only at creation), per CLAUDE.md; (c) payment confirmation workflow: `Enrollment` and `EventRegistration` changelists have `is_paid` as `list_editable` with filters/search (by username/email for enrollments, name/email/phone for event registrations), add-permission disabled since those rows are created by the site; (d) exam authoring via `Question` inline on `Exam` + `Choice` inline on `Question`; (e) `Submission`/`Answer`/`Certificate` are strictly read-only in admin (no add/change) — preserves "no human grading step"; (f) `Profile` inlined on the stock `UserAdmin`; `Notification` registered read/write for support use. Verified via test client as a superuser: all changelists 200, flipping `is_paid` from the enrollment changelist 302-saves AND fires the payment-confirmed notification signal from #6, price renders readonly on an existing course.
- [x] #8 Create a "My Courses" page — done 2026-07-06. `courses/views.py my_courses()` (login-required) at `/courses/mine/` (URL placed *before* the `<slug>` pattern so "mine" isn't captured as a course slug), template `templates/courses/my_courses.html` reusing the dashboard-grid/sidebar layout with "My Courses" active. Per enrollment it shows paid/pending tag, category/level/enroll date, exam attempt count, and state-dependent actions: unpaid → "Complete Payment" (enroll page), paid+certificate → result + PDF download links, paid+exam untaken → "Take Exam", taken-not-passed → "Last Result" + "Retake", paid course with no exam → "No exam yet" tag. The dashboard sidebar's "My Courses" link (previously pointing at the public catalogue) now points here. Verified via test client across all five states incl. anonymous → 302 login redirect.

## Session 2026-07-13 — staff admin permissions fixed

**Problem:** non-superuser staff couldn't edit anything in Django admin. Cause: `is_staff` only grants *login* to `/admin/`; every model still needs explicit per-model permissions, which non-superusers don't get by default.

**Fix:** `core/migrations/0002_content_managers_group.py` — data migration creating a **"Content Managers"** group (recreates itself on any fresh DB; reversible). Permissions encode the design rules:
- `Course`/`Event`/`Exam`/`Question`/`Choice`: add + change + view (authoring) — no delete on `Course`/`Event`
- `Enrollment`/`EventRegistration`: change + view only (enough to flip `is_paid`, can't create/delete)
- `Submission`/`Certificate`: view only — enforces "no human grading" at the permission level
- `Notification`: view only

Existing staff user `prest626` was added to the group. **New admins = check `is_staff` + add to "Content Managers"** — no per-user permission picking. Verified via test client with a throwaway staff user: admin index / course edit / event add all 200 with Save button, no delete link, submissions read-only. CLAUDE.md roadmap synced to reality (items 8/9 marked done; new hardening + production sections added).

## Task queue — next up

- [x] #9 **Guard immutability server-side, not just in admin** — done 2026-07-13. `Course.save()` now refuses `price` changes and `Event.save()` refuses `price`/`capacity` changes on existing rows: each compares the in-memory value against the current DB row and raises `ValueError` on a mismatch; all other field edits pass through. Verified live against the dev DB (mutations raise, description edits still save). Known gap (acceptable): `queryset.update()` bypasses `save()`, but admin already marks those fields readonly, so the two layers cover each other.
- [ ] #10 **Exam authoring ergonomics.** Editing choices requires drilling into each Question separately (Django has no native nested inlines). Acceptable for now; if the client complains, add `django-nested-admin` later rather than building custom views.
- [x] #11 Update CLAUDE.md/inbox.md so the roadmap reflects reality — done this session (2026-07-13).

### Production readiness (blocking before launch)

- [x] #12 **Settings/security** — done 2026-07-13. `settings.py` is env-driven via `os.environ`: `DJANGO_DEBUG` (defaults True for dev), `DJANGO_SECRET_KEY` (dev fallback key allowed only when DEBUG is on; hard `RuntimeError` if missing in prod), `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` (comma-separated). Template documented in `.env.example`.
- [x] #13 **HTTPS hardening** — done 2026-07-13. Applied automatically whenever DEBUG is off: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS (1 year, includeSubDomains, preload), plus `SECURE_PROXY_SSL_HEADER` for TLS-terminating proxies/PaaS. Verified: `manage.py check` clean in dev mode AND `manage.py check --deploy` clean (0 issues) with prod env vars set. Note: HSTS preload at a full year is set from day one — make sure HTTPS works before pointing real traffic at it, since HSTS is sticky in visitors' browsers.
- [x] #14 **Set the real `WHATSAPP_NUMBER`** — done 2026-07-13. Default in `settings.py` is now the real number `2348124411984` (still overridable via the `WHATSAPP_NUMBER` env var).
- [x] #15 **Static & media** — done 2026-07-13. (a) **Closed the certificate URL hole:** removed `static(MEDIA_URL, ...)` from `egalitarian_platform/urls.py` — nothing serves `/media/` anymore, in dev or prod. The ownership-checking `@login_required certificate_download` view (which already existed and filters `Certificate` by `request.user`) is now the *only* way to fetch a PDF. No template referenced `pdf_file.url`, so nothing else broke. (b) **WhiteNoise** (`whitenoise==6.12.0` in requirements): middleware added right after `SecurityMiddleware`; staticfiles storage set to `egalitarian_platform/storage.py TolerantManifestStaticFilesStorage` — WhiteNoise's compressed-manifest storage with a graceful fallback for `images/logo.png`, which templates reference (with an `onerror` hide) but which doesn't exist yet; strict manifest storage 500'd every page until the client's logo asset arrives. `collectstatic` must run at deploy time. Verified in prod mode (`DJANGO_DEBUG=False`): home 200 with hashed `main.<hash>.css` served by WhiteNoise (200), raw `/media/certificates/...` URL 404s, http→https 301; owner cert download 200 `application/pdf`, non-owner 404; dev mode unchanged (home/css 200).
- [ ] #16 **Serving & backups:** gunicorn behind nginx or a PaaS (Railway/Render/Fly); automated backups of the DB and `media/certificates/`.

## Session 2026-07-13 (later) — immutability guards + real contact info

1. **Task #9 done** — server-side immutability guards on `Course.save()`/`Event.save()` (details in the task queue above).
2. **Real contact info applied site-wide** (client-confirmed):
   - Address: No. 24, Oyekola Shopping Complex, Jakande Gate, Oke-Afa Isolo, Lagos — was already correct in `templates/base.html` (footer) and `templates/core/contact.html`, no change needed.
   - Phone: display reformatted to `+234 (812) 441 1984` in footer + contact page; `tel:+2348124411984` links were already correct.
   - Email: `info@egalitariancomputers.com` → `contactegalitarian@gmail.com` (display text + `mailto:` links, footer + contact page).
   - WhatsApp: `WHATSAPP_NUMBER` default in `settings.py` changed from placeholder `2348000000000` to `2348124411984` (same number as the phone line, which the contact page labels "Phone / WhatsApp") — closes task #14.
   - Verified by grep: no occurrences of the old email/phone/placeholder remain anywhere in templates or settings.

## Session 2026-07-13 (evening) — production hardening (#12/#13/#15)

1. **Env-driven settings (#12)** — `DJANGO_DEBUG` / `DJANGO_SECRET_KEY` / `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` (+ `WHATSAPP_NUMBER`), documented in `.env.example`. Dev needs no env vars; prod refuses to boot without a real secret key.
2. **HTTPS hardening (#13)** — auto-applies when DEBUG is off (SSL redirect, secure cookies, 1-year HSTS with includeSubDomains+preload, proxy SSL header). `check --deploy` clean in prod mode.
3. **Static & media (#15)** — WhiteNoise + closed the certificate-URL hole (details in the task queue above). New file: `egalitarian_platform/storage.py`. **Deploy-time requirement: run `manage.py collectstatic`.**
4. **Bug surfaced by strict manifest storage:** templates reference `static/images/logo.png` but the file doesn't exist (`static/images/` is empty; templates hide the broken img via `onerror`). Strict storage 500'd every prod page render — hence the tolerant storage subclass. **Still need the client's real logo dropped at `static/images/logo.png`.**
5. **CLAUDE.md synced** — tech stack (WhiteNoise/settings bullets), Certificates section (owner-gated downloads, never re-add a public media route), roadmap items 7/11 updated. Only remaining launch blocker: #16 hosting + backups.

## Loose ends / things to decide next session

- **#16 is the last blocking task:** pick a host (gunicorn behind nginx, or a PaaS — Railway/Render/Fly suits a volunteer project) and set up automated backups of `db.sqlite3` and `media/certificates/`.
- **Logo asset missing:** `static/images/logo.png` referenced by base/login/register templates doesn't exist — get the file from the client. Works fine without it (onerror hides it), but it's the visible brand gap.
- **HSTS caution:** preload + 1-year max-age ship with DEBUG off — confirm HTTPS works on the real domain *before* pointing traffic at it; HSTS is sticky in visitors' browsers.
- Only one `Course` (`web-development-django`) has a seeded `Exam`. Fine for dev/testing, but every other course currently has no exam — expected/normal, not a bug, since exams are added per-course by an admin.
- `db.sqlite3` and various `__pycache__` files show as modified/untracked in git status — normal side effect of running migrations and the dev server, not something to "fix," but worth being aware of before any `git add -A`. Consider adding `__pycache__/`, `staticfiles/`, `media/`, and `.env` to `.gitignore` before the first real commit.
- Nothing has been committed — all changes across the 2026-07-13 sessions are local/uncommitted pending your review.
