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
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_SENDER_EMAIL = os.environ.get('SENDGRID_SENDER_EMAIL')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL')
PUSHOVER_APP_TOKEN = os.environ.get('PUSHOVER_APP_TOKEN')
PUSHOVER_USER_KEY = os.environ.get('PUSHOVER_USER_KEY')
BUCKET_NAME = os.environ['BUCKET_NAME']

# Determine available notification methods
AVAILABLE_METHODS = []
if all([SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL, RECIPIENT_EMAIL]):
    AVAILABLE_METHODS.append('email')
if all([PUSHOVER_APP_TOKEN, PUSHOVER_USER_KEY]):
    AVAILABLE_METHODS.append('push')

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
    main_content = soup.find('main') or soup.find('body')
    return str(main_content)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_email_notification(url, old_content, new_content):
    message = Mail(
        from_email=SENDGRID_SENDER_EMAIL,
        to_emails=RECIPIENT_EMAIL, 
        subject=f'Website Content Changed: {url}',
        html_content=f'<html><body><h1>Content changed</h1><h2>URL: {url}</h2><h3>Old Content:</h3><pre>{old_content[:1000]}...</pre><h3>New Content:</h3><pre>{new_content[:1000]}...</pre></body></html>'
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"Email notification sent successfully for {url}")
        return True
    except Exception as e:
        logger.error(f"Error sending email for {url}: {e}")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def send_push_notification(url, old_content, new_content, push_params):
    message = f"Website Content Changed: {url}\n\nOld Content:\n{old_content[:1000]}...\n\nNew Content:\n{new_content[:1000]}..."
    data = {
        "token": PUSHOVER_APP_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message,
        "title": f"Content Change Detected: {url}",
        **push_params  # Include all push parameters
    }
    try:
        response = requests.post("https://api.pushover.net/1/messages.json", data=data)
        response.raise_for_status()
        logger.info(f"Push notification sent successfully for {url} with params: {push_params}")
        return True
    except Exception as e:
        logger.error(f"Error sending Pushover notification for {url}: {e}")
        return False

def send_notifications(url, old_content, new_content, methods, push_params):
    sent_notifications = []
    for method in methods:
        if method == 'email' and send_email_notification(url, old_content, new_content):
            sent_notifications.append('email')
        elif method == 'push' and send_push_notification(url, old_content, new_content, push_params):
            sent_notifications.append('push')
    return sent_notifications

# --- Cloud Storage Functions ---
def load_from_storage(url_hash):
    blobs = list(bucket.list_blobs(prefix=f"{url_hash}_"))
    if blobs:
        latest_blob = max(blobs, key=lambda b: b.updated)
        content = latest_blob.download_as_text()
        logger.info(f"Loaded previous content from Cloud Storage")
        return content
    else:
        logger.info("No previous content found in Cloud Storage.")
        return ""

def save_to_storage(url_hash, content):
    content_hash = hashlib.md5(content.encode()).hexdigest()
    blob_name = f"{url_hash}_{content_hash}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content)
    logger.info(f"Saved new content to Cloud Storage")

# --- Main Cloud Function ---
@http
def check_website(request):
    try:
        # Parse the request to get the target URL, notification method, and push parameters
        if request.method == 'GET':
            target_url = request.args.get('url')
            notification_methods = request.args.getlist('method')
            push_params = json.loads(request.args.get('push_params', '{}'))
        elif request.method == 'POST':
            request_json = request.get_json(silent=True)
            target_url = request_json and request_json.get('url')
            notification_methods = request_json and request_json.get('method', [])
            push_params = request_json and request_json.get('push_params', {})
            if isinstance(notification_methods, str):
                notification_methods = [notification_methods]
        
        if not target_url:
            return json.dumps({"status": "error", "message": "No target URL provided"}), 400
        
        # If no methods specified or invalid methods, default to all available methods
        if not notification_methods or not set(notification_methods).issubset(AVAILABLE_METHODS):
            notification_methods = AVAILABLE_METHODS
        
        url_hash = hashlib.md5(target_url.encode()).hexdigest()
        
        old_content = load_from_storage(url_hash)
        new_content_raw = fetch_website(target_url)
        new_content = parse_content(new_content_raw)
        
        if old_content != new_content:
            save_to_storage(url_hash, new_content)
            if old_content:  # Not the first check
                sent_notifications = send_notifications(target_url, old_content, new_content, notification_methods, push_params) if AVAILABLE_METHODS else []
                return json.dumps({
                    "status": "change_detected",
                    "notification_sent": bool(sent_notifications),
                    "methods_used": sent_notifications
                }), 200
            else:  # First time checking this URL
                return json.dumps({"status": "initial_check", "notification_sent": False}), 200
        else:
            logger.info("No changes detected.")
            return json.dumps({"status": "no_change", "notification_sent": False}), 200
    except ValueError as ve:
        logger.error(f"Value error: {ve}")
        return json.dumps({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error checking website: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500
