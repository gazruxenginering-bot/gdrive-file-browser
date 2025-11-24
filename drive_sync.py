import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE, ROOT_FOLDERS

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

def sync_folder_tree(service, folder_id, root_key, current_path="/", visited=None):
    if visited is None:
        visited = set()
    if folder_id in visited:
        return []
    visited.add(folder_id)

    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, size, webViewLink, parents, modifiedTime)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        pageSize=1000  # ← ambil hingga 1000 file per folder
    ).execute()
    items = results.get('files', [])
    result = []

    for item in items:
        item_path = os.path.join(current_path, item['name']).replace('\\', '/')
        is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
        modified_time = item.get('modifiedTime')
        if modified_time:
            from datetime import datetime
            modified_time = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))

        data = {
            'drive_id': item['id'],
            'name': item['name'],
            'mime_type': item['mimeType'],
            'is_folder': is_folder,
            'parent_id': folder_id,
            'root_key': root_key,
            'path': item_path,
            'size': int(item.get('size', 0)) if not is_folder else 0,
            'web_view_link': item.get('webViewLink', ''),
            'modified_time': modified_time
        }
        result.append(data)

        if is_folder:
            result.extend(sync_folder_tree(service, item['id'], root_key, item_path, visited))

    return result

def sync_all_roots(service):
    all_items = []
    for key, folder_id in ROOT_FOLDERS.items():
        print(f"Syncing root: {key} ({folder_id})")
        # Buat entri virtual root agar muncul di halaman utama
        virtual_root = {
            'drive_id': folder_id,
            'name': key.replace('_', ' ').title(),
            'mime_type': 'application/vnd.google-apps.folder',
            'is_folder': True,
            'parent_id': None,
            'root_key': key,
            'path': f"/{key}",
            'size': 0,
            'web_view_link': '',
            'modified_time': None
        }
        all_items.append(virtual_root)
        # Sinkronkan isi folder
        all_items.extend(sync_folder_tree(service, folder_id, key, f"/{key}"))
    return all_items
