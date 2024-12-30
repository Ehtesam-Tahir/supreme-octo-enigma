import os
from flask import Flask
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

# Get the path to the service account file from the environment variable
service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Verify the file exists
if not service_account_path or not os.path.exists(service_account_path):
    raise FileNotFoundError("Service account file not found. Please check the path in your .env file.")

# Use the service account credentials
credentials = Credentials.from_service_account_file(service_account_path)
print("Successfully loaded service account credentials.")

# Initialize Google Sheets service
service = build('sheets', 'v4', credentials=credentials)

# Spreadsheet ID and initial row
SPREADSHEET_ID = ""
current_row = 2

from lapp import routes  # Import routes after app initialization to avoid circular imports
