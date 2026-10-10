# Egalitarian Computers — Project CLAUDE.md

Django-based edutech platform for Egalitarian Computers (Tech E / Tech Egalitarian), Lagos, Nigeria. Courses, seminars/bootcamps, auto-graded exams, and certificates for students.

## Tech stack

- **Backend:** Django (server-rendered templates, MVT pattern) — no DRF/REST API layer, no separate frontend framework
- **Frontend:** Django Template Language (DTL) for all pages. TypeScript reserved strictly for client-side interactivity (exam countdown timer, auto-submit, question-flag UI, form validation) — not a SPA, not used for page structure/routing
- **Styling:** Single hand-written `static/css/main.css` (~550 lines), CSS custom properties as design tokens, no CSS framework (no Bootstrap/Tailwind)
- **Static files:** WhiteNoise (`whitenoise` in requirements) with a tolerant compressed-manifest storage (`egalitarian_platform/storage.py`); `collectstatic` required at deploy time. Media (`/media/`) is intentionally not URL-routed — certificate PDFs are served only through the ownership-checking `exams.views.certificate_download` view
- **Settings:** env-driven (`DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `WHATSAPP_NUMBER` — see `.env.example`); dev works with no env vars, prod requires `DJANGO_DEBUG=False` + a real secret key, and HTTPS hardening then applies automatically
- **Database:** SQLite (`db.sqlite3`) for development. Real models now exist for every app (`Course`/`Enrollment`, `Event`/`EventRegistration`, `Exam`/`Question`/`Choice`/`Submission`/`Answer`/`Certificate`, `Profile`, `Notification`) — sample data lives in data migrations (`*/migrations/0002_seed_*.py`), not hardcoded in `views.py` anymore
- **Auth:** Django's built-in session-based auth (`User` model, `@login_required`, `authenticate()`/`login()`/`logout()`). No JWT. No separate `Instructor` model — admins (`is_staff`) get course/event authoring permission instead. Real login/register are wired up (`accounts/views.py`), `Profile` auto-created via a `post_save` signal (`accounts/signals.py`)
- **PDF certificates:** `reportlab` (added to `requirements.txt`) — generation logic in `exams/certificates.py`
- **Payments:** no gateway integration. Manual reconciliation via WhatsApp redirect (`settings.WHATSAPP_NUMBER` — real number `2348124411984` set as the default, env-overridable) + admin flips an `is_paid` boolean in Django admin

## Why this stack (rejected alternatives)

**Rejected: decoupled Django REST API + React/Next.js SPA.**
Chosen instead: Django server-rendered templates.

- **SEO is a hard client requirement.** Server-rendered HTML gives full control over meta tags/semantic structure/sitemaps and doesn't depend on Googlebot executing JS to see content. An SPA would ship a near-empty HTML shell to crawlers.
- **Django admin gives the client free content management** without building a custom CMS.
- **Session auth avoids JWT/refresh-token complexity** entirely.
- **No CORS, no separate deploy pipeline** — appropriate for a volunteer project with no dedicated DevOps budget.
- Trade-off accepted: less rich client-side interactivity. TypeScript is deliberately scoped to a few isolated widgets (timer, form validation) rather than powering the whole UI.

## Project layout

```
egalitarian_platform/   Django project config (settings.py, root urls.py, wsgi/asgi)
core/                   home, about, contact, dashboard, notifications
courses/                course list/detail/enroll
events/                 event list/detail/register (fully independent subsystem)
accounts/               login, register, logout, profile
exams/                  exam_take, exam_result (MCQ, auto-graded)
templates/              project-level template dir, templates/base.html is the master layout
static/css/main.css     entire design system
```

Design principle: each app is a self-contained subsystem. `events/` in particular has **zero foreign keys** into `courses`/`accounts` — it's independently buildable/deployable. Future features (e.g. an `lms/` app) should follow the same pattern: new app with FKs pointing *into* existing models, without modifying those models.

**Current build stage:** feature-complete and production-hardened — models, auth, enrollment, payment gating, exam grading, certificates, notifications, Django admin (incl. the "Content Managers" permission group), env-driven settings, HTTPS hardening, and WhiteNoise static serving are all built and verified. The only remaining blocker before launch is picking a host + setting up backups (roadmap item 11); the client's logo asset (`static/images/logo.png`) is also still pending. `inbox.md` (same directory) holds the detailed session log and task queue.

## Design decisions (why, not just what)

### Student portal update (October 2026)
- Course categories are database records (`courses.Category`) editable in admin, with names, display order, and protected deletion when courses use them. Course.category is a foreign key. Migration 0006 preserves the previous category assignments and grants Content Managers category permissions. Catalogue and homepage filters, homepage learning-path links, and footer category links read the same records. Homepage All shows every course; category filtering has no three-card cap.
- Student login uses email and password via `accounts.backends.EmailBackend` with case-insensitive matching. Django admin retains its staff username login. Registration and profile changes require valid, unique emails; admin user forms validate duplicates. Migration `accounts.0003_unique_login_email` adds a case-insensitive unique index for nonblank emails while preserving existing accounts. Login honors safe local `next` redirects for protected pages.
- Exam pages use `static/css/exam.css` and `static/js/exam.js` for responsive questions, accessible radio groups, answered/flagged navigation, and results. Opening a ready exam creates or resumes an in-progress submission; its server timestamp sets the deadline, so refresh cannot reset the timer. Answers autosave to the login-, payment-, ownership-, CSRF-, and deadline-protected save endpoint. Expired submissions grade previously saved answers; repeated submission does not create another result or certificate. Incomplete exam configurations show an unavailable state and do not start an attempt.
- The admin dashboard follows the supplied `admin-page.png` concept: blue framing, a white sidebar with permission-aware model navigation, pastel metric cards, a seven-day registration chart, payment-status ring, recent registrations, exam results, upload actions, and recent admin activity. Charts use database records and Africa/Lagos calendar dates; no illustrative metrics are presented as real data.
- Admin is now mounted only at `/secret-admin-page/`; `/admin/` is removed. The custom `EgalitarianAdminSite` provides permission-aware live dashboard counts and upload shortcuts. Branded admin templates and `static/css/admin-workspace.css` style the dashboard, login, forms, and lists while retaining Django admin controls and theme switching.
- Course enrollment requires login and an explicit POST confirmation; visiting the enrollment page does not register the student.
- The profile is the student portal, listing enrolled courses, all uploaded course materials, admin-uploaded certificates, and existing exam certificates.
- Materials are available immediately after enrollment, including pending-payment enrollments, per the updated client requirement. Exam access still requires confirmed payment. This supersedes the older all-content payment gate below.
- Admins upload `CourseMaterial` files on the course admin page and a `CourseCertificate` on the student's enrollment admin page (or through the dedicated lists). Certificates are tied to one enrollment; no exam submission is required for uploaded certificates.
- Content Managers have upload/edit/delete permissions for these two new models. Downloads enforce enrollment or ownership server-side; `/media/` remains private.
- Apply course migrations 0004 and 0005 on deployment. Include `media/course_uploads/` in backups along with generated certificates.

### Accounts / Auth
- Single `User`/`Student` model — no separate `Instructor` model/table.
- **Update:** Django admins (`is_staff`/`is_superuser`) act as instructors for content management — an admin can create/upload `Course` and `Event` records (via Django admin and/or dedicated admin-only views). This is a permission granted to the existing admin role, not a new `Instructor` model or a grading role.
- **Still true, unchanged:** exams remain fully auto-graded — admin/instructor capability is scoped to *authoring course and event content*, not to grading or reviewing exam submissions. No human-in-the-loop grading step exists anywhere.
- Events are entirely decoupled from the `User`/`Student` model for registration purposes (see below) — the admin-uploads-events capability is a separate, one-directional relationship (admin → creates Event), not a link between `EventRegistration` and `User`.

### Courses / Enrollment
- `Course.price` is database-backed and editable by admins at any time. Nonnegative values are required; 0 means free. Public pages read the current price, and edits preserve existing enrollment payment confirmations.
- `Enrollment.is_paid` is set once at creation: `True` if `course.price == 0`, else `False` pending manual payment confirmation.
- `is_paid` is **one binary gate on all course content** (not per-feature). Unpaid = syllabus/description only, no exam, no future LMS content.
- **Critical, not-yet-built requirement:** access control must be enforced at the **view/permission level**, never by hiding UI. A student can hit an exam URL directly regardless of what's shown in templates — every relevant view must explicitly check `enrollment.is_paid` server-side.

### Exam subsystem
- MCQ only — no free-text/essay questions. `Exam` → `Question` → `Choice` → `Submission` (one row per attempt, full history kept) → `Answer`.
- **Fully auto-graded on submit, no human review step anywhere.** (Rejected: a `submitted → under_review → graded` state machine with an instructor grading queue — dropped once client confirmed pure MCQ/auto-grading. Note: admins do have course/event *authoring* permission — see Accounts/Auth — but grading itself has no human step.)
- Flagging a question is session-scoped UX only (lets a student skip and revisit before final submit) — not a grading signal, since there's no instructor to flag *for*. `Answer.is_flagged_by_student` kept for potential future "show my flagged answers" review UI, not currently used.
- Timer is per-exam (`Exam.duration_minutes`), auto-submits on expiry, unanswered = wrong, no partial credit/grace period.
- No auto-submit just because all questions are answered — student must explicitly click submit.

### Certificates
- Auto-generated PDF when `score >= exam.passing_score`, no human approval step.
- Explicitly excluded per client confirmation: no verification ID/QR code, no sequential certificate numbering.
- **Downloads are owner-gated:** PDFs live under `MEDIA_ROOT` but `/media/` is not URL-routed anywhere — the only way to fetch a certificate is `exams.views.certificate_download` (`@login_required`, filters by `request.user`). Never re-add a public `static(MEDIA_URL, ...)` route; it would make certificates fetchable by guessable URL.

### Events / Seminars / Bootcamps
- **Fully independent subsystem** — no FKs into `Course`, `Enrollment`, or `User`. Explicit client principle: "Events are independent from the students and courses."
- **No account required** to view or register for an event, ever (this flip-flopped across the design conversation — three different answers were given before landing here; treat this as final).
- `EventRegistration` captures `full_name`/`email`/`phone` directly — no link to `User` even if the registrant happens to also be a logged-in student.
- Consequence (intentional, not a gap): event registrants can't get in-app notifications, since notifications are tied to `User` accounts.
- `Event.capacity` and `Event.price` are set at creation and remain immutable. Course prices are editable independently.
- Capacity behavior: **hard cutoff**, no waitlist.
- Paid events use the same manual boolean-flip pattern as course payments. (Rejected: a per-registration unique access-code/unlock system — dropped once confirmed events follow the same simple boolean pattern as courses.)

### Payment (applies to both Enrollment and EventRegistration)
- Fully manual: click Pay → redirected to WhatsApp number → manual payment off-platform → admin manually matches the conversation to the record (by account for `Enrollment`, by name/email/phone for `EventRegistration`) → admin flips `is_paid` in Django admin.
- `is_paid` lives on the specific payable record, **never** on the user/profile — a student can have independent payment states across multiple enrollments simultaneously.
- Explicitly out of scope: any payment gateway, webhooks, automated email/SMS confirmation (not funded for this build tier).

### Notifications
- In-app, DB-backed (`Notification(user, message, is_read, created_at, link)`), students only.
- Also uses browser `Notification.requestPermission()` JS API — fires only while the tab is open. **Not** the Web Push API (no service worker/VAPID/offline delivery). Must communicate to client: this is not a reliable "ping me even when the site is closed" system.

### LMS (deferred)
- Explicitly deferred to a future standalone `lms/` app once the core platform ships.
- Deferral is safe because Django apps can add new models (`Module`, `Lesson`) with FKs into the existing `Course` model without altering `Course` itself — confirmed `Course` doesn't hardcode content into a flat field that would block this.
- Not yet designed: video hosting/storage, lesson sequencing, completion tracking, "verification processes" (mentioned in original brief, undefined — needs its own discovery pass).

## Roadmap / what's left to build

1. ✅ **Database models** — done, see Tech stack above
2. ✅ **Wire up real auth** — done (`accounts/views.py`)
3. ✅ **Real enrollment** — done (`courses/views.py enroll()`)
4. ✅ **Payment → WhatsApp redirect** — done (`courses/views.py`, `events/views.py`)
5. ✅ **Paid-access gate on exams** — done, verified live (`exams/views.py`)
6. ✅ **Auto-grading on submit** — done (`exams/views.py submit_exam()`)
7. ✅ **Certificate PDF generation** — done (`exams/certificates.py`); the result-page download-link bug is resolved (see `inbox.md`), and downloads are owner-gated (see Certificates above)
8. ✅ **In-app notifications** — done ("mark all as read" wired, enrollment/payment signals in `courses/signals.py`)
9. ✅ **Django admin registration** — done. All five apps' `admin.py` implemented (immutability readonly rules, `is_paid` list_editable, exam inlines, read-only `Submission`/`Answer`/`Certificate`). "Admins act as instructors" is enforced via the **"Content Managers" auth group** created in `core/migrations/0002_content_managers_group.py`: authoring perms on `Course`/`Event`/`Exam`/`Question`/`Choice`, change-only on `Enrollment`/`EventRegistration` (the `is_paid` flip), view-only on submissions/certificates, no deletes on courses/events. New admins need `is_staff` + membership in this group (`is_staff` alone shows an empty admin).
10. **Hardening todo:**
    - Event price/capacity immutability remains enforced in `Event.save()` and admin. Course prices are editable per the updated client requirement, with nonnegative validation.
    - Exam authoring ergonomics — editing choices requires drilling into each Question separately (Django has no native nested inlines). Acceptable for now; if the client complains, add `django-nested-admin` rather than building custom views.
11. **Production readiness:**
    - ✅ Settings/security — done. `settings.py` is env-driven (`DJANGO_DEBUG`, `DJANGO_SECRET_KEY` — required in prod, dev fallback otherwise; `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, comma-separated; see `.env.example`). HTTPS hardening auto-applies whenever DEBUG is off: `SECURE_SSL_REDIRECT`, secure session/CSRF cookies, 1-year HSTS (includeSubDomains + preload — **verify HTTPS on the real domain before sending traffic; HSTS is sticky in browsers**), `SECURE_PROXY_SSL_HEADER` for PaaS/nginx TLS termination. `check --deploy` passes clean. ✅ Real `WHATSAPP_NUMBER` (`2348124411984`) set. Real contact info (address / +234 (812) 441 1984 / contactegalitarian@gmail.com) is live in the footer and contact page.
    - ✅ Static & media — done. WhiteNoise serves hashed/compressed statics via `egalitarian_platform/storage.py TolerantManifestStaticFilesStorage` (tolerant because templates reference a not-yet-supplied `static/images/logo.png` with an `onerror` fallback — drop in the client's logo when it arrives). **Run `manage.py collectstatic` at deploy time.** `/media/` is deliberately not routed at all — certificate PDFs are only reachable through the ownership-checking `certificate_download` view; a public media route would make them guessable.
    - ❌ Serving & backups (last blocking item): gunicorn behind nginx or a PaaS (Railway/Render/Fly). Automated backups of the DB and `media/certificates/`.
12. **(Future, separate phase) LMS app** — `lms/` with `Module`/`Lesson` models FK'd into `Course`

Full session-by-session detail (what was done, what broke, what's queued next) lives in `inbox.md`, not here — this file stays a stable reference; `inbox.md` is the rotating handoff note.

## Running the project

```
source venv/bin/activate && python manage.py runserver
```
