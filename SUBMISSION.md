# SUBMISSION.md

## What to submit

Send these in your assignment email:

1. GitHub repository link containing this project.
2. Live deployed app URL from Render/Railway/Fly.
3. Credentials: no login is required for this prototype. The app records reviewer actions as `analyst@breatheesg.com`.

Also share the repository with:

- saurav@breatheesg.com
- rahul@breatheesg.com
- shivang@breatheesg.com

## Files that must be in the repo

- `backend/`
- `frontend/`
- `sample-data/`
- `MODEL.md`
- `DECISIONS.md`
- `TRADEOFFS.md`
- `SOURCES.md`
- `README.md`
- `DEPLOYMENT.md`
- `render.yaml`

Do not manually upload `node_modules`, `.venv`, `.tools`, `.codex-pydeps`, `frontend/dist`, or `backend/db.sqlite3`. They are generated locally and ignored by `.gitignore`.

## Render deployment steps

1. Push this folder to GitHub.
2. In Render, create a new Blueprint and select this repository.
3. Render will create:
   - `breathe-esg-api`
   - `breathe-esg-web`
4. After the backend deploys, copy its URL.
5. Set the frontend static site's `VITE_API_BASE_URL` environment variable to the backend URL.
6. Redeploy the frontend.
7. Open the frontend URL and click `Seed demo` if the dashboard is empty.

Free Render hosting is acceptable for a student submission. The backend can sleep when idle, so the first request may take a little longer to load.

## Suggested email text

Hi,

Please find my submission for the Breathe ESG Tech Intern Assignment:

- GitHub repository: `<your GitHub repo URL>`
- Deployed app: `<your Render/Railway/Fly frontend URL>`
- Credentials: no login required; reviewer actions are recorded as `analyst@breatheesg.com`

I have shared the repository with saurav@breatheesg.com, rahul@breatheesg.com, and shivang@breatheesg.com.

Thanks,
`<your name>`
