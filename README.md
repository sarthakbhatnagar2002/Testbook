# QBank

A fixed set of subject-wise MCQ practice question banks (Physics, Chemistry,
Mathematics — pre-seeded, nobody can create more). Pick a bank and practice: pick an
answer, see the correct option and an explanation immediately, then move to the next
question. A profile page tracks what you've solved, where you're weakest, what you're
currently working through, and a GitHub-style heatmap of your daily activity.

**Stack:** React + Vite + TypeScript + Tailwind (`/frontend`) · FastAPI + SQLAlchemy 2 +
Alembic + SQLite (`/backend`) · JWT in an httpOnly cookie · pytest + Vitest

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
python seed.py                  # creates demo@example.com + the 3 subjects (a few sample Qs each)
python bulk_questions.py        # tops each subject up to 100+ questions (safe to re-run; skips dupes)
uvicorn app.main:app --reload   # http://localhost:8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env            # VITE_API_URL defaults to http://localhost:8000
npm run dev                     # http://localhost:5173
```

Demo login after seeding (password `password123`): `demo@example.com`. Anyone can
register — there's a single account type, no roles or invite codes.

## What works

- **Subjects (banks):** a fixed, pre-seeded set — Physics, Chemistry, Mathematics.
  There is no create-subject endpoint or UI; nobody (not even via the API) can add a
  new one. Each subject's card on the Subjects page shows a progress bar
  (solved/total) and accuracy.
- **Questions:** any signed-in user can add a question to an existing subject — text
  with an optional diagram (uploaded from the device, not a URL), 2-6 options each
  with optional text and/or an image (an image-only option with empty text is
  allowed), and an optional explanation shown after answering. You can delete a
  question you created, but not once anyone has attempted it, and not one someone
  else created.
- **Practice:** pick an option, submit, and immediately see whether you were right,
  which option was correct, and the explanation (if the question has one). Next/Previous
  buttons move through the subject's questions in order. Retries are always allowed —
  each attempt is recorded, and a question's status (not attempted / correct /
  incorrect) always reflects your most recent attempt on it.
- **Profile:** total solved, total attempted, overall accuracy, a GitHub-style
  contribution heatmap of correctly-solved questions per day over the last year, a
  "currently solving" card for whichever subject you most recently practiced,
  per-subject progress bars, and a recent-activity feed of your last 15 attempts.

## Content

`backend/bulk_questions.py` adds 100+ original, self-authored MCQs to each subject
(310 total as shipped: 105 Physics, 102 Chemistry, 103 Mathematics) — standard
textbook-level facts and problems, written from scratch, not copied from any book,
exam paper, or question-bank site. It's idempotent: re-running it skips any question
whose exact text already exists in that subject, so it's safe to run again after
adding more questions to the script.

## Layout

```
backend/app/
  models.py            SQLAlchemy tables (users, subjects, questions, options, attempts)
  schemas.py            Pydantic request/response models
  security.py / deps.py JWT cookie auth (single account type, no roles)
  routers/
    auth.py              register / login / logout / me
    subjects.py           list subjects, with per-user progress (no create route)
    questions.py          create / delete a question
    practice.py            list a subject's questions, fetch one to answer, submit an answer
    profile.py             the profile dashboard + GET /profile/activity (daily solve counts)
    uploads.py              image upload for diagrams/options
  alembic/                migrations
  seed.py                 demo user + the 3 subjects with a few sample questions
  bulk_questions.py       idempotent script: tops each subject up to 100+ questions
  tests/                  pytest, one file per router + helpers.py

frontend/src/
  lib/api.ts              fetch wrapper (credentials: include) + image upload helper
  lib/types.ts             TS types mirroring backend/app/schemas.py
  lib/subjectColors.ts     deterministic accent color per subject name
  lib/questionFilter.ts    pure filter for the subject question list (unit tested)
  lib/timeAgo.ts            relative-time formatting for the activity feed (unit tested)
  lib/activityGrid.ts        pure date-count-map -> contribution-grid builder (unit tested)
  components/ActivityHeatmap.tsx  renders the grid from lib/activityGrid.ts
  pages/
    SubjectsPage.tsx         bank cards (read-only list, no creation UI)
    SubjectQuestionsPage.tsx question list with status filter tabs
    PracticeQuestionPage.tsx the answer -> instant feedback -> next flow
    AddQuestionPage.tsx      add a question to a subject
    ProfilePage.tsx           the dashboard described above, including the heatmap
```

Correct answers are never sent to the browser until a question has been answered —
`GET /questions/{id}/practice` omits `is_correct` entirely; it only appears in the
`POST /questions/{id}/answer` response. API datetimes are stored as naive UTC and
serialized with an explicit UTC offset, so the frontend converts to the user's local
timezone with a plain `new Date(isoString)`.

## Tests

```bash
cd backend && pytest    # auth, subjects (no create), questions, practice flow, profile, activity
cd frontend && npm test # questionFilter, timeAgo, and activityGrid pure functions
```

36 backend tests and 18 frontend tests pass as of this change.

## Not built yet

Rich text and KaTeX for formulas, editing an existing question, rate limiting, bulk
import, question versioning, search/sort on the subject question list.

## Moving to Postgres later

Change `DATABASE_URL` in `backend/.env` to a Postgres URL and rerun
`alembic upgrade head`. The models use plain SQLAlchemy 2 types with no SQLite-specific
features, except: `DateTime` columns are stored and compared as **naive UTC**
throughout the backend (see `backend/app/time_utils.py`) because SQLite has no
timezone-aware storage. Postgres supports `TIMESTAMPTZ` properly, so if you want to use
it, switch the columns to timezone-aware and drop the naive-UTC convention. The daily
activity aggregation in `profile.py` uses `func.date(...)`, which works the same way on
Postgres.

## History

This app went through two earlier, substantially different shapes before landing here:
a single-codebase Next.js app with teacher-authored tests, then a React + FastAPI split
with a Testbook-style full-screen timed exam (sections, room keys, archiving). Both were
dropped in favor of a subject-wise practice bank with instant feedback — the
`588ec57f6dc0` Alembic migration is the one that made that cut, dropping all test/exam
tables and the teacher/student role split in one pass; downgrading past it isn't
supported. A later round removed the ability to create new subjects entirely (the three
banks are now fixed) and added the activity heatmap.
