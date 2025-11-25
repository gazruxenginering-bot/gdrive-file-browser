# gdrive-file-browser

This is a small Flask app that indexes Google Drive folders and provides a web UI to browse and preview PDF files. The project includes a server-side proxy to stream files from Google Drive (avoids CORS issues) and a single-page PDF viewer using PDF.js.

## Quick deploy to Render (recommended safe setup)

1. Push this repository to GitHub (already done).

2. On Render, create a new **Web Service** and connect to this repository.

3. Environment variables (Render: Dashboard → Environment):

- `SERVICE_ACCOUNT_JSON` (required for proxy)
  - Paste the full JSON contents of your Google service account `credentials.json` here.
  - The app will write this value to `credentials.json` at startup.

- `PORT` (not required) — Render provides this automatically.

- `FLASK_DEBUG` (optional) — set to `true` to enable Flask debug server (not recommended in production). Default is `false`.

4. Build & Start commands on Render:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app -w 4 -b 0.0.0.0:$PORT`

5. Notes about database and files:

- This app uses `database.db` (SQLite) by default. Render's filesystem is ephemeral; if you need persistent storage across deploys, use a managed database (e.g., Render Postgres) and update the app to use it.
- The proxy uses the service account to access Drive files. Make sure the service account has permissions to view the files (share files/folders with service account or make files accessible as needed).

6. Healthcheck

- The app exposes `/healthz` which returns `200 OK`. Configure Render's health check to use this endpoint.

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
