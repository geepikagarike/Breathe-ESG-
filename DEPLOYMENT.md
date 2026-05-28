# DEPLOYMENT.md

## Fastest path

Use Render Blueprint deployment with `render.yaml`.

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint**.
3. Select the GitHub repository.
4. Render creates `breathe-esg-api`.
5. Choose the free plan if Render asks. Free services can sleep when idle, but the public URL still works for assignment submission.
6. Open the `breathe-esg-api` URL. It serves the React app at `/` and the API at `/api/`.
7. Click `Seed demo` if the dashboard is empty.

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
- Deployed app URL: `https://breathe-esg-api-xl9b.onrender.com/`
- Click `Seed demo` in the UI if the deployed database is empty.
