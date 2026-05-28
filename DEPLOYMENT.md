# DEPLOYMENT.md

## Fastest path

Use Render Blueprint deployment with `render.yaml`.

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint**.
3. Select the GitHub repository.
4. Render creates:
   - `breathe-esg-api`
   - `breathe-esg-web`
5. The frontend receives `VITE_API_BASE_URL` automatically from the backend service URL.
6. If Render asks you to confirm paid resources, choose a paid web service plan for always-on hosting. Free web services can sleep.
7. Open the frontend URL and click `Seed demo` if the dashboard is empty.

The backend build command installs dependencies, applies migrations, seeds demo data, and collects static files.

## Local verification commands

Backend:

```powershell
.\scripts\run-backend.ps1
```

Frontend, in a second terminal:

```powershell
.\scripts\run-frontend.ps1
```

Manual checks:

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test

cd ..\frontend
npm run build
```

## Notes for reviewers

- No login is required.
- Reviewer actions are recorded as `analyst@breatheesg.com`.
- Click `Seed demo` in the UI if the deployed database is empty.
