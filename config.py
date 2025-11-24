import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

# === GANTI DENGAN FOLDER ID DARI URL ANDA ===
ROOT_FOLDERS = {
    "EBOOKS": "12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z",
    "Pengetahuan": "1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll",
    "Perpustakaan_Service": "1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW",
    "Service_Manual": "1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT"
}
