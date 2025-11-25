# app.py

import os
import sqlite3
import requests
from flask import Flask, render_template, abort, request, jsonify, Response, stream_with_context
from google.oauth2 import service_account
from google.auth.transport.requests import Request as AuthRequest

# If deploying to platforms like Render where you cannot store a file directly,
# we support providing the service account JSON via the environment variable
# `SERVICE_ACCOUNT_JSON`. If set, write it to `credentials.json` at startup.
sa_json = os.environ.get('SERVICE_ACCOUNT_JSON')
if sa_json:
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    try:
        with open(creds_path, 'w') as f:
            f.write(sa_json)
        try:
            os.chmod(creds_path, 0o600)
        except Exception:
            pass
    except Exception:
        # If we cannot write the file, log and continue; proxy endpoint will fail later if needed
        print('Warning: could not write credentials.json from SERVICE_ACCOUNT_JSON')

app = Flask(__name__)
from config import DATABASE_PATH

# Use the detected database path from config (DATABASE_URL-aware fallback)
DATABASE = DATABASE_PATH

# === Konfigurasi Root Folder (harus sesuai dengan drive_sync.py) ===
ROOT_FOLDERS = {
    "EBOOKS": "12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z",
    "Pengetahuan": "1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll",
    "Service_Manual_1": "1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW",
    "Service_Manual_2": "1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT"
}

# === Nama tampilan untuk UI ===
DISPLAY_NAMES = {
    "EBOOKS": "📚 EBOOKS",
    "Pengetahuan": "🧠 Pengetahuan",
    "Service_Manual_1": "🔧 Service Manual (1)",
    "Service_Manual_2": "⚙️ Service Manual (2)"
}

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


@app.context_processor
def inject_root_list():
    """Make root_list available in all templates for the sidebar."""
    conn = get_db_connection()
    root_list = []
    try:
        for key, folder_id in ROOT_FOLDERS.items():
            count = conn.execute(
                "SELECT COUNT(*) FROM files WHERE (parent_id = ?) OR (root_folder_name = ?)",
                (folder_id, key)
            ).fetchone()[0]
            name = DISPLAY_NAMES.get(key, key)
            root_list.append((name, folder_id, count))
    finally:
        conn.close()
    return dict(root_list=root_list)

def sizeof_fmt(num, suffix="B"):
    if not num or num == "—":
        return "—"
    try:
        num = int(num)
    except:
        return "—"
    for unit in ["", "K", "M", "G"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} T{suffix}"

app.jinja_env.filters['filesizeformat'] = sizeof_fmt


# === HALAMAN UTAMA: Tampilkan 4 root folder eksplisit ===
@app.route('/')
def index():
    conn = get_db_connection()
    root_list = []
    for key, folder_id in ROOT_FOLDERS.items():
        # Hitung jumlah file & folder langsung di bawah root folder ini
        count = conn.execute(
            "SELECT COUNT(*) FROM files WHERE (parent_id = ?) OR (root_folder_name = ?)",
            (folder_id, key)
        ).fetchone()[0]
        name = DISPLAY_NAMES.get(key, key)
        root_list.append((name, folder_id, count))
    conn.close()
    return render_template('index.html', root_list=root_list)


# === TAMPILKAN ISI FOLDER ===
@app.route('/folder/<folder_id>')
def view_folder(folder_id):
    conn = get_db_connection()
    
    # Cari nama folder ini (untuk judul halaman)
    folder_name = "Folder"
    for key, fid in ROOT_FOLDERS.items():
        if fid == folder_id:
            folder_name = DISPLAY_NAMES.get(key, key)
            break
    else:
        # Coba cari dari database jika ini subfolder
        folder_row = conn.execute(
            "SELECT name FROM files WHERE id = ? AND is_directory = 1", (folder_id,)
        ).fetchone()
        if folder_row:
            folder_name = folder_row['name']
        else:
            # Cek apakah ada file di folder ini (meski folder root tidak tersimpan)
            count = conn.execute(
                "SELECT COUNT(*) FROM files WHERE parent_id = ?", (folder_id,)
            ).fetchone()[0]
            if count == 0:
                abort(404)

    # Ambil semua item di folder ini
    items = conn.execute(
        "SELECT * FROM files WHERE parent_id = ? ORDER BY is_directory DESC, name",
        (folder_id,)
    ).fetchall()
    conn.close()

    return render_template('folder.html', folder_id=folder_id, folder_name=folder_name, items=items)


# === PREVIEW FILE (PDF) ===
@app.route('/file/<file_id>')
def file_preview(file_id):
    conn = get_db_connection()
    try:
        file = conn.execute(
            "SELECT * FROM files WHERE id = ? AND is_directory = 0", (file_id,)
        ).fetchone()
        if not file:
            abort(404)

        parent_id = file['parent_id']
        sidebar_items = []
        if parent_id:
            # show sibling folders (directories) in the same parent for navigation
            sidebar_items = conn.execute(
                "SELECT id, name FROM files WHERE parent_id = ? AND is_directory = 1 ORDER BY name",
                (parent_id,)
            ).fetchall()
    finally:
        conn.close()

    # Render a PDF.js single-page viewer (falls back to Drive preview if CORS prevents loading)
    return render_template('pdfjs_viewer.html', file=file, sidebar_items=sidebar_items)


@app.route('/download/<file_id>')
def download_proxy(file_id):
    """Proxy endpoint that downloads a file from Google Drive using a service account
    and streams it back to the client. This avoids client-side CORS issues when
    PDF.js requests the PDF binary directly.
    """
    # ensure credentials file exists
    creds_file = os.path.join(os.path.dirname(__file__), 'credentials.json')
    if not os.path.exists(creds_file):
        app.logger.error('credentials.json not found')
        abort(404)

    try:
        creds = service_account.Credentials.from_service_account_file(
            creds_file, scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        creds.refresh(AuthRequest())
        token = creds.token
    except Exception:
        app.logger.exception('Failed to obtain service account token')
        abort(500)

    drive_url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
    headers = {'Authorization': f'Bearer {token}'}
    try:
        r = requests.get(drive_url, headers=headers, stream=True, timeout=60)
    except Exception:
        app.logger.exception('Error requesting file from Drive')
        abort(502)

    if r.status_code != 200:
        app.logger.error('Drive returned status %s for file %s', r.status_code, file_id)
        return (f'Failed to download file (status {r.status_code})', 502)

    def generate():
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    content_type = r.headers.get('Content-Type', 'application/octet-stream')
    resp = Response(stream_with_context(generate()), content_type=content_type)
    disp = r.headers.get('Content-Disposition')
    if disp:
        resp.headers['Content-Disposition'] = disp
    return resp


# === PENCARIAN GLOBAL ===
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return index()

    conn = get_db_connection()
    results = conn.execute(
        "SELECT *, (CASE WHEN root_folder_name = 'EBOOKS' THEN '📚 EBOOKS' " +
        "WHEN root_folder_name = 'Pengetahuan' THEN '🧠 Pengetahuan' " +
        "WHEN root_folder_name = 'Service_Manual_1' THEN '🔧 Service Manual (1)' " +
        "WHEN root_folder_name = 'Service_Manual_2' THEN '⚙️ Service Manual (2)' " +
        "ELSE root_folder_name END) as display_root " +
        "FROM files WHERE name LIKE ? ORDER BY root_folder_name, name",
        (f"%{query}%",)
    ).fetchall()
    conn.close()
    return render_template('search.html', query=query, results=results)


# === API untuk integrasi (misal: Compyle) ===
@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"results": []})
    
    conn = get_db_connection()
    results = conn.execute(
        "SELECT name, id FROM files WHERE is_directory = 0 AND name LIKE ? LIMIT 10",
        (f"%{query}%",)
    ).fetchall()
    conn.close()
    
    return jsonify([
        {
            "name": r['name'],
            "url": f"https://drive.google.com/file/d/{r['id']}/view"
        }
        for r in results
    ])


# === JALANKAN APLIKASI ===
if __name__ == '__main__':
    # In production the app should be run with a WSGI server (gunicorn).
    # Only use Flask's dev server when running locally. The debug mode
    # can be enabled by setting FLASK_DEBUG=true in the environment.
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)


# Lightweight healthcheck for deployment platforms
@app.route('/healthz')
def healthz():
    return "ok", 200