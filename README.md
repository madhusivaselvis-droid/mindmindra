# MINDNER

MINDNER is an AI-assisted cognitive companion for elderly people and their caregivers. It is a daily assistance and monitoring platform, not a diagnostic or medical prediction system.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The demo uses the caregiver persona, but the backend also supports registration, JWT login, and Argon2 password hashing. Completed game summaries are queued in IndexedDB with a UUID `event_id`; `/sync` is idempotent and rejects duplicate events.

### PostgreSQL and Redis

`docker compose up -d` starts local PostgreSQL and Redis. Configure `DATABASE_URL` and run `alembic upgrade head` (or apply `database/schema.sql`). Copy `.env.example` to `.env` and replace secrets before deploying.

### Complete Docker stack

The Compose stack builds the FastAPI backend and an Nginx-served frontend alongside PostgreSQL and Redis:

```powershell
docker compose up --build
```

The frontend is available at `http://localhost:8080` and the API at `http://localhost:8000/docs`. PostgreSQL health checks gate backend startup, and the backend applies Alembic migrations before serving traffic.

## Architecture

- `backend/app/main.py`: FastAPI REST API with SQLAlchemy persistence, JWT auth, role enforcement, pagination, aggregates, reminders, alerts, and sync idempotency.
- `backend/app/models.py`: normalized SQLAlchemy models and indexes.
- `backend/app/auth.py`: Argon2 hashing and JWT token validation.
- `backend/app/adaptive.py`: explainable rule-based difficulty recommendation.
- `backend/app/ai/difficulty.py`: CPS scoring and Random Forest difficulty recommendations for Pattern Recognition.
- `backend/alembic/`: migration configuration and initial migration.
- `database/schema.sql`: normalized PostgreSQL schema for users, patient assignments, games, reminders, aggregates, content, sync events, and audit logs.
- `frontend/src/offline.ts`: IndexedDB sync queue.
- `frontend/src/App.tsx`: responsive patient and caregiver demo views.
- `frontend/src/auth.ts` and `frontend/src/api.ts`: session-scoped JWT client and caregiver API helpers.
- `frontend/src/gameLogic.ts`: tested aggregate game scoring.
- `frontend/src/i18n/en.json` and `frontend/src/i18n/ta.json`: centralized English/Tamil resource catalogs.

This remains a cognitive-support demonstrator, not a diagnostic medical device. Before real data, configure HTTPS, a strong `JWT_SECRET_KEY`, production PostgreSQL, rate limiting, object storage, background aggregate jobs, monitoring, and a formal privacy/compliance review. The demo accounts use `demo-password` only in development and must never be deployed.

## Useful API routes

`POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /patients`, `GET /patients/{id}`, `POST /game-sessions`, `POST /game-results`, `POST /sync`, `GET /reminders`, `POST /reminders`, `PATCH /reminders/{id}/complete`, `GET /analytics/patients/{id}/daily`, `GET /analytics/patients/{id}/weekly`, `GET /recommendations/{id}`, and `GET /alerts/{id}`.

Run tests with `pytest`. The local fallback database is SQLite; PostgreSQL is selected through `DATABASE_URL`.

## Pattern Recognition Adaptive Difficulty

Completed pattern results persist accuracy, score, response time, attempts, mistakes, the previous level, CPS component scores, the recommendation, and the model source. CPS is calculated as `0.4 × accuracy + 0.2 × reaction + 0.2 × completion + 0.2 × consistency`; component values are normalized to 0–100. More than 8 historical pattern sessions with varied outcomes activate the Random Forest classifier. Before there is enough patient history, the API uses the transparent CPS thresholds as a fallback. CPS below 40 recommends a guided easier activity and creates a caregiver alert. The UI shows the CPS components, prior/next level, and model source after synchronization.

Docker image builds were not executable in the current development environment because Docker CLI was unavailable; validate them with `docker compose config` and `docker compose up --build` on a Docker-enabled machine.

Authentication uses an HTTPS-only, HttpOnly, SameSite cookie in production and double-submit CSRF protection; passwords and access tokens are not stored in frontend storage. The analytics trend uses a lightweight accessible SVG renderer, so the previous Recharts bundle warning is removed. English/Tamil resource catalogs now cover the application vocabulary; component-level extraction of every legacy dashboard sentence remains a follow-up for translation QA.
