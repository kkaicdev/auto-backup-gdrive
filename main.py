import os
import logging
import argparse

from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

URL_AUTH = ['https://www.googleapis.com/auth/drive.file']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', URL_AUTH)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', URL_AUTH)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def create_folder(service, folder_name, parent_id=None):
    current_date = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    folder_name_with_date = f"{folder_name}_{current_date}"

    file_metadata = {
        'name': folder_name_with_date,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder['id']

def upload_files(directory_path):
    try:
        service = authenticate_google()

        if not os.path.exists(directory_path):
            logging.error(f"Erro: O diretório '{directory_path}' não existe.")
            return

        logging.info(f"Iniciando upload dos arquivos de {directory_path}...")

        folder_name = os.path.basename(directory_path)
        folder_id = create_folder(service, folder_name)

        logging.info(f'Pasta criada no Drive com a data e horário da execução.')

        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
        
                if not os.path.exists(file_path):
                    logging.warning(f'Arquivo não encontrado: {file_path}')
                    continue

                logging.info(f"Enviando arquivo: {file_name}...")

                file_metadata = {'name': file_name, 'parents': [folder_id]}
                media = MediaFileUpload(file_path, resumable=True)
                
                try:
                    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                    logging.info(f'Arquivo enviado com sucesso!')
                except HttpError as error:
                    logging.error(f'Ocorreu um erro ao enviar o arquivo {file_name}: {error}')
        
    except HttpError as error:
        logging.error(f'Ocorreu um erro: {error}')

def parse_arguments():
    parser = argparse.ArgumentParser(description="Backup para o Google Drive")
    parser.add_argument('--directory', type=str, required=True, help="Caminho do diretório para upload")
    return parser.parse_args()

def main():
    args = parse_arguments()
    upload_files(args.directory)

if __name__ == "__main__":
    main()
