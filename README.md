# Breathe ESG Tech Intern Assignment

Prototype ESG ingestion and analyst review app for SAP fuel/procurement, utility electricity, and corporate travel data.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/geepikagarike/Breathe-ESG-)

## Stack

- Backend: Django + Django REST Framework + SQLite/PostgreSQL-ready models
- Frontend: React + Vite
- Deployment: Render blueprint included in `render.yaml`

## Local Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to Django.

On Windows, you can also run:

```powershell
.\scripts\run-backend.ps1
.\scripts\run-frontend.ps1
```

## Demo Login

The prototype does not require auth for local review. It records reviewer identity from `X-Analyst-Email`; the React app sends `analyst@breatheesg.com`.

## Assignment Docs

- `MODEL.md`
- `DECISIONS.md`
- `TRADEOFFS.md`
- `SOURCES.md`

## API Highlights

- `POST /api/ingestions/upload/` multipart file upload
- `POST /api/ingestions/seed-demo/` reload sample data
- `GET /api/dashboard/?tenant=acme-industrials`
- `GET /api/activity-records/?tenant=acme-industrials&status=needs_review`
- `POST /api/activity-records/{id}/approve/`
- `POST /api/activity-records/{id}/reject/`

## Deployment

`render.yaml` defines a Django web service and a React static site. The backend build runs migrations and seeds demo data. After pushing to GitHub, create a Render Blueprint from this repository, then set `VITE_API_BASE_URL` in the static site to the backend URL. A live deployment still needs your Render/GitHub account access.

See `DEPLOYMENT.md` and `SUBMISSION.md` for the exact submission flow.
