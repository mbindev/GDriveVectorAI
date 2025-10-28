from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
from typing import List, Dict

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """Initialize Google Drive API service using service account credentials."""
    # Assuming credentials are stored in Secret Manager or as environment variable
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/credentials.json")

    if os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES)
    else:
        # If credentials are in Secret Manager
        from app.main import get_secret
        import json
        credentials_json = get_secret("drive-service-account-key")
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(credentials_json), scopes=SCOPES)

    return build('drive', 'v3', credentials=credentials)

def list_files_in_folder(folder_id: str) -> List[Dict]:
    """List all files in a Google Drive folder."""
    service = get_drive_service()

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, webViewLink)"
    ).execute()

    return results.get('files', [])

def download_file(file_id: str, file_name: str, destination_path: str = None) -> bytes:
    """Download a file from Google Drive."""
    service = get_drive_service()

    request = service.files().get_media(fileId=file_id)
    file_content = io.BytesIO()
    downloader = MediaIoBaseDownload(file_content, request)

    done = False
    while done is False:
        status, done = downloader.next_chunk()

    file_content.seek(0)
    content = file_content.read()

    if destination_path:
        with open(destination_path, 'wb') as f:
            f.write(content)

    return content
