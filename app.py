from flask import Flask, render_template, request, jsonify
from models import db, File
from drive_sync import get_drive_service, sync_all_roots
from config import DATABASE_PATH, ROOT_FOLDERS
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def sizeof_fmt(num, suffix="B"):
    if not num:
        return "—"
    for unit in ["", "K", "M", "G"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f} T{suffix}"

app.jinja_env.filters['filesizeformat'] = sizeof_fmt

@app.template_filter('datetime_format')
def datetime_format(value, format='%d/%m/%Y %H:%M'):
    if value:
        return value.strftime(format)
    return "—"

# === SYNC ===
@app.route('/sync')
def sync_route():
    try:
        service = get_drive_service()
        all_items = sync_all_roots(service)
        db.session.query(File).delete()
        for item in all_items:
            f = File(
                drive_id=item['drive_id'],
                name=item['name'],
                mime_type=item['mime_type'],
                is_folder=item['is_folder'],
                parent_id=item['parent_id'],
                root_key=item['root_key'],
                path=item['path'],
                size=item['size'],
                web_view_link=item['web_view_link'],
                modified_time=item['modified_time']
            )
            db.session.add(f)
        db.session.commit()
        return f"✅ Synced {len(all_items)} items from {len(ROOT_FOLDERS)} root folders."
    except Exception as e:
        return f"❌ Error during sync: {str(e)}", 500

# === HALAMAN UTAMA ===
@app.route('/')
def home():
    roots = []
    for key, folder_id in ROOT_FOLDERS.items():
        name = key.replace('_', ' ').title()
        roots.append({'name': name, 'drive_id': folder_id})
    return render_template('index.html', roots=roots, is_home=True, search_results=None)

# === PENCARIAN GLOBAL ===
@app.route('/search')
def global_search():
    query = request.args.get('q', '').strip()
    if not query:
        return render_template('index.html', roots=[], is_home=True, search_results=[])

    try:
        matches = File.query.filter(File.name.contains(query)).all()
        return render_template(
            'index.html',
            roots=[],
            is_home=True,
            search_results=matches,
            query=query
        )
    except Exception as e:
        return f"❌ Search error: {str(e)}", 500

# === TAMPILKAN FOLDER ===
@app.route('/folder/<drive_id>')
def folder_view(drive_id):
    try:
        current = File.query.filter_by(drive_id=drive_id).first_or_404()
        query = request.args.get('q', '').strip()

        if query:
            files = File.query.filter(File.parent_id == drive_id, File.name.contains(query)).all()
        else:
            files = File.query.filter(File.parent_id == drive_id).all()

        path_parts = [p for p in current.path.split('/') if p]
        breadcrumb = []
        for i, part in enumerate(path_parts):
            current_path = "/" + "/".join(path_parts[:i+1])
            folder = File.query.filter_by(path=current_path, is_folder=True).first()
            breadcrumb.append({'name': part, 'id': folder.drive_id if folder else None})

        return render_template(
            'index.html',
            current_folder=current,
            files=files,
            breadcrumb=breadcrumb,
            query=query,
            is_home=False
        )
    except Exception as e:
        return f"❌ Folder error: {str(e)}", 500

# === API UNTUK COMPLYLE ===
@app.route('/api/search', methods=['POST'])
def compyle_search():
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        if not query:
            return jsonify({"results": []})

        matches = File.query.filter(File.is_folder == False, File.name.contains(query)).limit(10).all()
        results = [{
            "name": f.name,
            "url": f.web_view_link,
            "path": f.path,
            "size": sizeof_fmt(f.size)
        } for f in matches if f.web_view_link]

        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === JALANKAN ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    with app.app_context():
        if not os.path.exists(DATABASE_PATH):
            db.create_all()
    app.run(host='0.0.0.0', port=port)
