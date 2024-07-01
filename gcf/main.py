import os
import requests
from bs4 import BeautifulSoup
from functions_framework import http
from google.cloud import storage
import hashlib
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from tenacity import retry, stop_after_attempt, wait_exponential
import json

# --- Configuration ---
SENDGRID_API_KEY = os.environ['SENDGRID_API_KEY']
SENDGRID_SENDER_EMAIL = os.environ['SENDGRID_SENDER_EMAIL']
RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']
BUCKET_NAME = os.environ['BUCKET_NAME']

# Initialize clients
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper Functions ---
def fetch_website(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Example: extract main content, adjust as needed
    main_content = soup.find('main') or soup.find('body')
    return str(main_content)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_notification(url, old_content, new_content):
    message = Mail(
        from_email=SENDGRID_SENDER_EMAIL,
        to_emails=RECIPIENT_EMAIL, 
        subject=f'Website Content Changed: {url}',
        html_content=f'<html><body><h1>Content changed</h1><h2>URL: {url}</h2><h3>Old Content:</h3><pre>{old_content}</pre><h3>New Content:</h3><pre>{new_content}</pre></body></html>'
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Notification sent successfully for {url}")
    except Exception as e:
        logger.error(f"Error sending email for {url}: {e}")
        raise

# --- Cloud Storage Functions ---
def load_from_storage(url_hash):
    blob = bucket.blob(url_hash)
    if blob.exists():
        content = blob.download_as_text()
        logger.info(f"Loaded previous content from Cloud Storage")
        return content
    else:
        logger.info("No previous content found in Cloud Storage.")
        return ""

def save_to_storage(url_hash, content):
    blob = bucket.blob(url_hash)
    blob.upload_from_string(content)
    logger.info(f"Saved new content to Cloud Storage")

# --- Main Cloud Function ---
@http
def check_website(request):
    try:
        # Parse the request to get the target URL
        if request.method == 'GET':
            target_url = request.args.get('url')
        elif request.method == 'POST':
            request_json = request.get_json(silent=True)
            target_url = request_json and request_json.get('url')
        
        if not target_url:
            return "Error: No target URL provided", 400

        url_hash = hashlib.md5(target_url.encode()).hexdigest()
        
        old_content = load_from_storage(url_hash)
        new_content_raw = fetch_website(target_url)
        new_content = parse_content(new_content_raw)
        
        if old_content != new_content:
            send_notification(target_url, old_content, new_content)
            save_to_storage(url_hash, new_content)
            return json.dumps({"status": "change_detected"}), 200
        else:
            logger.info("No changes detected.")
            return json.dumps({"status": "no_change"}), 200
    except Exception as e:
        logger.error(f"Error checking website: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500
