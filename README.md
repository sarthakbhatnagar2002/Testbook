# MCQ Platform

Teachers build question banks and tests; students practise, take timed tests in a
full-screen exam interface, and review results.

**Stack:** React + Vite + TypeScript + Tailwind (`/frontend`) · FastAPI + SQLAlchemy 2 +
Alembic + SQLite (`/backend`) · JWT in an httpOnly cookie · pytest + Vitest

This replaces the original single-codebase Next.js app (see "History" below). The
Next.js app (`app/`, `components/`, `db/`, `lib/`, `scripts/`) has been superseded by
the two folders above and can be removed once you've verified the new stack works for
you.

## Run it

Two terminals.

**Backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # then set SESSION_SECRET (openssl rand -base64 32)
alembic upgrade head            # creates dev.db from the SQLAlchemy models
python seed.py                  # optional demo data
uvicorn app.main:app --reload   # http://localhost:8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL defaults to http://localhost:8000
npm run dev                     # http://localhost:5173
```

Demo logins after seeding (password `password123`): `teacher@example.com`,
`student@example.com`. Signing up as a teacher needs `TEACHER_INVITE_CODE` from
`backend/.env` (delete that line to allow anyone).

## What works

- **Teacher:** create questions (text, subject/topic, rating, up to 6 options, optional
  image links, explanation), build tests with duration, a marking scheme
  (correct / wrong / skipped), an optional start/end availability window, publish or
  unpublish, see attempts and scores per test.
- **Student:** a full-screen timed-test exam interface (palette sidebar, per-question
  stopwatch, mark-for-review, save & next, question-paper/instructions modals, question
  reporting) with a server-side clock, autosave every 5 seconds, resume with the exact
  palette state restored, and a results review with correct answers and explanations.
  A **Tests** page lists upcoming/open tests (with Start/Resume) and previous attempts.
  A **Profile** page shows a performance summary: tests taken, average score, overall
  accuracy, accuracy by subject/topic, recent scores, and a weak-topics list (lowest
  accuracy topics with 5+ answered questions).
- **Difficulty:** based on each student's first answered attempt only. Until a question
  has 10 first attempts it shows the teacher's rating marked "(est.)". Cut-offs: fail
  rate under 30% easy, 30-60% medium, over 60% hard (`backend/app/difficulty.py`).
- **Scoring:** one function (`backend/app/scoring.py`). The marking scheme is copied
  onto each attempt, so editing a test later never changes old scores.
- **Expired attempts:** graded lazily (plus a 30s grace period) from the last autosave
  the next time anyone opens them. No job queue.
- **Role checks on every route:** teachers only read/edit their own questions, tests and
  results; students can't see unpublished tests or another student's attempt.

## Layout

```
backend/app/
  models.py            SQLAlchemy tables (users, questions, options, tests,
                        test_questions, test_attempts, attempts, question_reports)
  scoring.py            marks + timer            (ported from lib/scoring.ts)
  difficulty.py          tiers                     (ported from lib/difficulty.ts)
  attempts_logic.py      grading + counters, transactional (ported from lib/attempts.ts)
  security.py / deps.py  JWT cookie auth, role guards
  routers/                auth, questions, tests, student (attempts/history/reports), profile
  alembic/                migrations
  seed.py                 demo data
  tests/                  pytest (unit + integration + API-level role checks)

frontend/src/
  lib/api.ts              fetch wrapper (credentials: include)
  lib/types.ts             TS types mirroring backend/app/schemas.py
  lib/examStatus.ts        pure palette-tile status derivation (unit tested)
  context/AuthContext.tsx  session state
  pages/student/           Tests, ExamPage (the exam screen), Results, Profile
  pages/teacher/           Questions, NewQuestion, TeacherTests, NewTest, TeacherTestResults
```

Correct answers are never sent to the browser while a question is unanswered or a test
is in progress. API datetimes are stored as naive UTC and serialized with an explicit
UTC offset, so the frontend converts to the user's local timezone with a plain
`new Date(isoString)`.

## Tests

```bash
# Backend: unit (scoring, difficulty) + integration (first-attempt counting, scoring,
# idempotent submit, lazy expiry) + API-level (auth, role checks, full attempt lifecycle)
cd backend && pytest

# Frontend: the palette status-derivation function
cd frontend && npm test
```

38 backend tests and 7 frontend tests pass as of this change.

## Not built yet

Image upload (links only for now), rich text and KaTeX, Ask AI explanations, question
editing, retake limits, rate limiting, question versioning. Bookmarks and the practice
mode/difficulty filters from the original plan were intentionally dropped per the
current scope (see "Decisions" below) — only the single timed-test flow remains.

## Moving to Postgres later

Change `DATABASE_URL` in `backend/.env` to a Postgres URL and rerun
`alembic upgrade head`. The models use plain SQLAlchemy 2 types with no SQLite-specific
features, except: `DateTime` columns are stored and compared as **naive UTC**
throughout the backend (see `backend/app/time_utils.py`) because SQLite has no
timezone-aware storage. Postgres supports `TIMESTAMPTZ` properly, so if you want to use
it, switch the columns to timezone-aware and drop the naive-UTC convention — just make
sure every comparison (`_availability`, `finalize_if_expired`, etc.) stays consistent
about aware vs. naive.

## History

The original brief asked for a single Next.js codebase (App Router, Drizzle ORM,
cookie sessions via `jose`). A later round of changes specified: (1) a full-screen
Testbook-style exam interface, (2) splitting into a React + FastAPI stack, and
(3) trimming student navigation down to just Profile and Tests (dropping Practice,
bookmarks, and difficulty filters for now). This repo now reflects that second round.
