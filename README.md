# Exam Timetable Management System (Python / Flask)

A basic exam timetable system where an **admin** creates/edits/cancels exams
for a specific academic year + section, and **students** can only ever see
exams matching their own year and section.

Built with Python's standard library + Flask, SQLite, and PyJWT — no
external database server or paid services required.

## Tech Stack

| Layer     | Choice                                             |
|-----------|-----------------------------------------------------|
| Backend   | Python 3 + Flask                                    |
| Database  | SQLite (via stdlib `sqlite3`)                       |
| Auth      | JWT (PyJWT), PBKDF2-SHA256 password hashing (stdlib) |
| Testing   | `unittest` (18 tests, see `tests/test_app.py`)      |

SQLite was chosen over Postgres/MySQL because the spec explicitly limits
scope (no room allocation, clash detection, invigilation, etc.) — a
single-file database keeps local setup and hosting to one process, with
no separate DB service to provision. All SQL lives in `database.py` /
`models/`, so swapping to Postgres later is a contained change.

## Project Structure

```
exam_system/
├── app.py                  # Flask app factory + entrypoint
├── config.py                # Env-var driven configuration
├── database.py               # SQLite connection + schema (init_db)
├── auth.py                  # JWT issuing + @require_auth decorator
├── validators.py             # Business-rule validation (shared by routes)
├── models/
│   ├── exam.py               # Exam CRUD + the year/section filter query
│   └── student.py            # Student profile + password hashing
├── routes/
│   ├── auth_routes.py         # /api/auth/* (admin + student login/register)
│   ├── admin_routes.py         # /api/admin/exams/* (CRUD)
│   └── student_routes.py       # /api/student/* (profile + timetable)
├── tests/test_app.py           # Automated tests incl. required edge cases
├── seed.py                   # Optional: seeds sample students + exams
├── requirements.txt
└── .env.example
```

## Setup Instructions

```bash
cd exam_system
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then edit JWT_SECRET / ADMIN_PASSWORD etc.

python app.py                   # runs on http://localhost:5000
```

Optional — seed a couple of sample students and exams to try immediately:

```bash
python seed.py
```

Run the tests:

```bash
python -m unittest tests.test_app -v
```

Production (e.g. Render/Railway):

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Environment Variables

| Variable            | Purpose                                              | Default                |
|---------------------|-------------------------------------------------------|-------------------------|
| `JWT_SECRET`        | Secret used to sign JWTs — **change in production**   | `dev-secret-change-me`  |
| `JWT_EXPIRES_MINUTES` | Token lifetime in minutes                            | `120`                   |
| `DATABASE_PATH`     | Path to the SQLite file (auto-created)                 | `exam_timetable.db`     |
| `ADMIN_EMAIL`       | Bootstrap admin login email                            | `admin@example.com`     |
| `ADMIN_PASSWORD`    | Bootstrap admin login password                         | `admin123`              |
| `PORT`              | Server port                                            | `5000`                  |
| `FLASK_DEBUG`       | Enable Flask debug mode (`true`/`false`)               | `false`                 |

There is a single bootstrap admin account (no admin-registration
endpoint) — this matches the "basic" scope of the assessment, which does
not call for multi-admin/role management.

## Data Model / Schema

**students**

| column         | type    | notes                        |
|----------------|---------|-------------------------------|
| id             | INTEGER | PK, autoincrement             |
| name           | TEXT    | required                      |
| email          | TEXT    | required, unique              |
| password_hash  | TEXT    | PBKDF2-SHA256, salted          |
| academic_year  | TEXT    | required                      |
| section        | TEXT    | required                      |
| created_at     | TEXT    | ISO timestamp                 |

**exams**

| column         | type    | notes                              |
|----------------|---------|--------------------------------------|
| id             | INTEGER | PK, autoincrement                    |
| subject        | TEXT    | required                             |
| academic_year  | TEXT    | required                             |
| section        | TEXT    | required                             |
| exam_date      | TEXT    | `YYYY-MM-DD`, required               |
| start_time     | TEXT    | `HH:MM` (24h), required              |
| end_time       | TEXT    | `HH:MM` (24h), required, > start_time |
| is_cancelled   | INTEGER | 0/1, soft-delete flag                 |
| created_at / updated_at | TEXT | ISO timestamps                  |

An index on `(academic_year, section)` backs the student timetable query.

## API Endpoints

All request/response bodies are JSON. Protected routes require
`Authorization: Bearer <token>`.

### Auth

| Method | Path                       | Auth | Description                     |
|--------|-----------------------------|------|-----------------------------------|
| POST   | `/api/auth/admin/login`      | —    | `{email, password}` → admin token |
| POST   | `/api/auth/student/register` | —    | Create a student profile → token  |
| POST   | `/api/auth/student/login`    | —    | `{email, password}` → student token |

### Admin — Exam CRUD (`role: admin`)

| Method | Path                          | Description                                   |
|--------|---------------------------------|-------------------------------------------------|
| POST   | `/api/admin/exams`               | Create an exam                                  |
| GET    | `/api/admin/exams`                | List all exams (`?include_cancelled=false` to hide cancelled) |
| GET    | `/api/admin/exams/<id>`            | Get one exam                                    |
| PUT    | `/api/admin/exams/<id>`             | Edit an exam (partial updates supported)         |
| DELETE | `/api/admin/exams/<id>`              | Cancel an exam (soft-delete). `?hard=true` permanently deletes it instead |

### Student (`role: student`)

| Method | Path                     | Description                                                        |
|--------|----------------------------|------------------------------------------------------------------------|
| GET    | `/api/student/me`           | Own profile                                                            |
| GET    | `/api/student/timetable`     | Exams filtered to the *authenticated* student's own year + section only |

### Misc

| Method | Path           | Description        |
|--------|-----------------|----------------------|
| GET    | `/api/health`    | Liveness check       |

## Architecture & Design Choices

- **Filtering happens server-side, from the token — never from query
  params.** `GET /api/student/timetable` reads `academic_year`/`section`
  only from the authenticated student's stored profile (embedded in the
  JWT and re-confirmed against the DB). Any `?academic_year=`/`?section=`
  query parameters a client sends are read but deliberately ignored. This
  is the direct fix for the "student manipulates API parameters" edge
  case, and `test_student_cannot_override_section_via_query_params`
  proves it.
- **Soft-delete for cancellation.** The spec calls the delete action
  "cancel", so `DELETE /api/admin/exams/<id>` sets `is_cancelled=1` by
  default (auditable, reversible via a future "reinstate" endpoint) and
  cancelled exams are excluded from student timetables. `?hard=true` is
  available for admins who want a real delete.
- **Validation is centralized** in `validators.py` so the same rules
  (all fields mandatory, valid date/time formats, `end_time > start_time`)
  apply to both `POST` (full payload) and `PUT` (partial payload, merged
  against the existing record before the time-order check — see
  `test_update_exam_partial_time_change_revalidated`).
  This is what correctly rejects the edge case of changing just one of
  the two times into an invalid order.
- **State transitions for an exam:** `created → edited (any number of
  times) → cancelled` (or `deleted` via the hard-delete option).
  There is no "un-cancel" transition in this basic scope, matching the
  spec's minimal state model.
- **Auth:** stateless JWTs (`role: admin | student`) rather than server
  sessions, so the API can scale horizontally without a shared session
  store — appropriate for a small hosted demo (Render/Railway/Vercel).
  Passwords are hashed with salted PBKDF2-SHA256 (stdlib `hashlib`, no
  extra dependency) rather than stored in plaintext.
- **Edge cases handled explicitly** (see `tests/test_app.py` for the
  corresponding automated test):
  - Missing/blank required fields on create → `400` with a per-field error map.
  - `end_time <= start_time` (including on partial updates) → `400`.
  - Student profile missing `academic_year`/`section` → `422` at login and at timetable fetch, rather than silently returning wrong data.
  - No exams for a section → `200` with an empty list and `count: 0`, not an error.
  - Student attempting to pass another section via query params → ignored, own profile always wins.
  - Wrong-role access to admin routes → `403`; missing/expired/invalid token → `401`.

## Test Credentials (after running `python seed.py`)

| Role    | Email               | Password    | Year / Section |
|---------|----------------------|--------------|------------------|
| Admin   | `admin@example.com`   | `admin123`   | —                 |
| Student | `asha@example.com`     | `student123` | 2nd Year - A       |
| Student | `rohan@example.com`     | `student123` | 2nd Year - B       |

Log in as `asha@example.com` and hit `GET /api/student/timetable` — she
will only see the "Data Structures" exam (Section A), never the
"Operating Systems" exam (Section B), even if you try to override the
section via query parameters.

## Deploying a Live Demo

Any Python-friendly host works (Render, Railway, Fly.io):

1. Push this folder to a GitHub repo.
2. Set the environment variables from `.env.example` in the host's dashboard.
3. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. SQLite's file lives on the container's disk — fine for a demo; for a
   persistent production deployment, mount a volume for `DATABASE_PATH`
   or swap `database.py` for a managed Postgres connection.
