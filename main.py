import argparse
import logging
import sys
import re
from datetime import datetime
from pathlib import Path

from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Constants
URL_AUTH = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PATH = Path('token.json')
CREDS_PATH = Path('credentials.json')
MAX_RETRIES = 3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Utility Functions
def sanitize_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Backup to Google Drive")
    parser.add_argument('--name', type=str, help="Custom name for the Drive folder")
    parser.add_argument('--directory', type=Path, required=True, help="Path to the directory to upload")
    return parser.parse_args()

def get_files(directory: Path):
    """Returns a list of all files (recursively) in a directory."""
    return [p for p in directory.rglob('*') if p.is_file()]

# Authentication
def get_credentials(token_path=TOKEN_PATH, creds_path=CREDS_PATH):
    """Handles Google Drive credentials loading and refreshing."""
    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(token_path, URL_AUTH)
        except ValueError:
            logging.warning("Invalid or corrupted 'token.json' file.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                logging.error("Failed to refresh token. Please re-authenticate.")
                creds = None

        if not creds:
            if not creds_path.exists():
                raise FileNotFoundError(f"Credentials file '{creds_path}' not found.")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, URL_AUTH)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                logging.error(f"Credentials file not found: {creds_path}")
                raise
            except DefaultCredentialsError as e:
                logging.error(f"Failed to load credentials: {e}")
                raise

        with token_path.open("w") as f:
            f.write(creds.to_json())

    return creds

def authenticate_google():
    """Returns an authenticated Google Drive service instance."""
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)

# Drive Operations
def create_drive_folder(service, folder_name, parent_id=None):
    """Creates a folder in Google Drive with timestamp."""
    current_date = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    folder_name = sanitize_filename(f"{folder_name}_{current_date}")

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    folder = service.files().create(body=file_metadata, fields='id').execute()
    logging.info(f"Drive folder created with timestamp: {folder_name}")
    return folder['id']

def upload_file(service, file_path: Path, folder_id: str) -> bool:
    """Uploads a single file to Google Drive with retry logic."""
    file_metadata = {
        'name': file_path.name,
        'parents': [folder_id]
    }

    for attempt in range(MAX_RETRIES):
        media = MediaFileUpload(str(file_path), resumable=True)
        try:
            logging.info(f"Starting upload: {file_path.name}")
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            logging.info("Upload successful.")
            return True
        except HttpError as error:
            logging.error(f"Failed to upload '{file_path.name}': {error}")
            if attempt < MAX_RETRIES - 1:
                logging.info(f"Retrying... ({attempt + 1}/{MAX_RETRIES})")
            else:
                return False

def upload_files(directory: Path, folder_name: str = None):
    """Processes all files in a directory and uploads them to Google Drive."""
    if not directory.exists() or not directory.is_dir():
        logging.error(f"Error: The path '{directory}' is not a valid directory or doesn't exist.")
        return

    files = list(get_files(directory))
    if not files:
        logging.warning(f"Warning: The directory '{directory}' is empty. Nothing to upload.")
        return

    service = authenticate_google()

    folder_base_name = folder_name or directory.name
    folder_id = create_drive_folder(service, folder_base_name)

    success_count = 0
    for file_path in files:
        if upload_file(service, file_path, folder_id):
            success_count += 1

    total = len(files)
    failure_count = total - success_count
    logging.info(f"{success_count}/{total} file(s) uploaded successfully.")
    if failure_count:
        logging.warning(f"{failure_count} file(s) failed to upload.")

# Main
def main():
    try:
        start = datetime.now()

        args = parse_arguments()
        upload_files(args.directory, folder_name=args.name)

        end = datetime.now()
        elapsed = end - start
        logging.info(f"Script completed in {elapsed}")
    except FileNotFoundError as e:
        logging.error(f"File or directory not found: {e}")
        sys.exit(1)
    except PermissionError as e:
        logging.error(f"Permission denied: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
