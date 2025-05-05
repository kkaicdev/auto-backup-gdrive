# auto-backup-gdrive

This Python script automates the backup of a local directory to a Google Drive folder, creating a new timestamped folder for each upload session.

## 🔧 Features

- Recursively uploads all files in a given directory to Google Drive.
- Creates a uniquely named folder with the current date and time.
- Supports retries on upload failures.
- Handles OAuth2 authentication using `credentials.json`.
- Skips empty directories and provides detailed logs.

## 📦 Requirements

- Python 3.7+
- Google Cloud credentials file (`credentials.json`)

### 🔌 Python Dependencies:

Install required packages using:
pip install -r requirements.txt

### 🔌 Instructions:

To use this project, you'll need your own Google Drive API key, which can be easily obtained at: [here](https://console.cloud.google.com/). 

it will be a credentials.json, and you need to place it in the same folder as the main file.
                                                                                                                                           
## 🚀 Usage:

python main.py --directory /your/path/folder [--name custom_folder_name]
                                                                                                                                           
                                                                                                                                          
