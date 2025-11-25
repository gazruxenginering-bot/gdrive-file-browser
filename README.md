# gdrive-file-browser

This is a small Flask app that indexes Google Drive folders and provides a web UI to browse and preview PDF files. The project includes a server-side proxy to stream files from Google Drive (avoids CORS issues) and a single-page PDF viewer using PDF.js.

## Quick deploy to Railway (recommended safe setup)

1. Push this repository to GitHub (already done).

2. Create a new project on Railway.app and connect this repository:
   - Go to https://railway.app/dashboard
   - New Project → Import from GitHub
   - Select `gdrive-file-browser` repository

3. Environment variables (Railway: Dashboard → Your Service → Variables):

   Add the following variables:

   - `SERVICE_ACCOUNT_JSON` (required for proxy)
     - Paste the full JSON contents of your Google service account `credentials.json` here.
     - The app will write this value to `credentials.json` at startup.
   
   - `FLASK_DEBUG=false` (optional but recommended for production)

4. Railway will automatically:
   - Detect `railway.json` and use it to configure the deployment
   - Build using Nixpacks: `pip install -r requirements.txt`
   - Start using: `gunicorn app:app -w 4 -b 0.0.0.0:$PORT`
   - Set up health check to `/healthz`

5. Notes about database and files:

   - This app uses `database.db` (SQLite) by default. Railway's filesystem is ephemeral; data will be lost on redeploy/restart.
   - For persistent storage, use Railway Postgres or another managed DB (set `DATABASE_URL` env var).
   - The proxy uses the service account to access Drive files. Make sure the service account has permissions to view the files (share files/folders with service account or make files accessible as needed).

6. Healthcheck

   - The app exposes `/healthz` which returns `200 OK`. Railway will automatically monitor this endpoint.

---

## Alternative: Deploy to Render

If you prefer Render, use `render.yaml` instead (Railway uses `railway.json`).

## Local development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run locally:

```bash
FLASK_DEBUG=true python app.py
```

Or with Gunicorn (closer to production):

```bash
gunicorn app:app -w 4 -b 0.0.0.0:5000
```

## Security

- Never commit `credentials.json` to the repository. Use `SERVICE_ACCOUNT_JSON` or a secret manager.
- Monitor logs for large file downloads; proxying PDFs streams them through your app which increases bandwidth usage.
