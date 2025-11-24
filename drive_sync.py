# drive_sync.py

import sqlite3
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === Konfigurasi ===
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DATABASE_PATH = 'database.db'

ROOT_FOLDERS = {
    "EBOOKS": "12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z",
    "Pengetahuan": "1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll",
    "Service_Manual_1": "1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW",
    "Service_Manual_2": "1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT"
}

# === Setup Google Drive API ===
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

# === Setup Database ===
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        mime_type TEXT,
        size INTEGER DEFAULT 0,
        modified_time TEXT,
        parent_id TEXT,
        root_folder_name TEXT,
        is_directory BOOLEAN DEFAULT 0
    )''')
    conn.commit()
    conn.close()

# === Sinkronisasi Rekursif (Gunakan koneksi yang sama) ===
def sync_folder_recursive(service, conn, folder_id, root_name, parent_id=None, level=0):
    cursor = conn.cursor()
    page_token = None

    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageSize=1000,
            pageToken=page_token
        ).execute()

        items = results.get('files', [])
        if not items:
            break

        for item in items:
            is_dir = item.get('mimeType') == 'application/vnd.google-apps.folder'
            size = int(item.get('size', 0)) if not is_dir else 0

            cursor.execute('''INSERT OR REPLACE INTO files
                (id, name, mime_type, size, modified_time, parent_id, root_folder_name, is_directory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    item['id'],
                    item['name'],
                    item.get('mimeType', 'unknown'),
                    size,
                    item.get('modifiedTime', ''),
                    folder_id,
                    root_name,
                    is_dir
                )
            )
            print("  " * level + f"{'📁' if is_dir else '📄'} {item['name']}")

            # Rekursif jika folder — tetap gunakan koneksi yang sama!
            if is_dir:
                sync_folder_recursive(service, conn, item['id'], root_name, item['id'], level + 1)

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    conn.commit()  # Commit setelah setiap folder selesai

# === Sinkronisasi Semua Root Folder ===
def sync_all_folders():
    print("🔧 Memulai sinkronisasi Google Drive...")
    init_db()
    service = get_drive_service()

    # Gunakan SATU koneksi database untuk seluruh proses
    conn = sqlite3.connect(DATABASE_PATH, timeout=20.0)

    try:
        for root_name, folder_id in ROOT_FOLDERS.items():
            print(f"\n🚀 Sinkronisasi root folder: {root_name} (ID: {folder_id})")
            sync_folder_recursive(service, conn, folder_id, root_name, folder_id)
        print("\n✅ Sinkronisasi selesai! Data tersimpan di database.db")
    finally:
        conn.close()

# === Jalankan Saat File Di-Run Langsung ===
if __name__ == '__main__':
    sync_all_folders()