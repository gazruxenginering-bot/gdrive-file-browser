import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
# If a platform provides a DATABASE_URL env var, try to detect sqlite URLs and
# translate them to a local file path. Full Postgres/SQLAlchemy support is
# recommended but out-of-scope for this small patch.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # support sqlite:///absolute/path/to/db or sqlite:///relative/path
    if DATABASE_URL.startswith('sqlite:///'):
        # strip the sqlite:/// prefix to get the file path
        path = DATABASE_URL[len('sqlite:///'):]
        # if relative path provided, make absolute relative to project
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        DATABASE_PATH = path
    elif DATABASE_URL.startswith('sqlite://'):
        # fallback handling for other sqlite URL variants
        path = DATABASE_URL.split('sqlite://', 1)[-1]
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
        DATABASE_PATH = path
    else:
        # Not an sqlite URL (e.g. postgres). Keep using the bundled SQLite DB
        # and surface a warning for the operator to migrate the app.
        print('Notice: DATABASE_URL provided but is not an SQLite URL.\n' \
              'The app will continue using local SQLite (database.db).\n' \
              'To use Postgres, migrate the app to SQLAlchemy and set DATABASE_URL accordingly.')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# === GANTI DENGAN FOLDER ID DARI URL ANDA ===
ROOT_FOLDERS = {
    "EBOOKS": "12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z",
    "Pengetahuan": "1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll",
    "Service_Manual_1": "1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW",
    "Service_Manual_2": "1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT"
}

