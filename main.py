import os
import requests
from bs4 import BeautifulSoup  
from difflib import HtmlDiff
from functions_framework import http
from google.cloud import storage
import hashlib

# --- Configuration (from Environment Variables) ---
TARGET_URL = os.environ['TARGET_URL']
SENDGRID_API_KEY = os.environ['SENDGRID_API_KEY']
SENDGRID_SENDER_EMAIL = "change-notifier@shapor.com"
RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']
BUCKET_NAME = "website-differ"  

# Initialize Cloud Storage client
storage_client = storage.Client()

# --- Helper Functions ---

def fetch_website(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def generate_diff(old_content, new_content):
    diff = HtmlDiff().make_table(
        fromlines=old_content.splitlines(),
        tolines=new_content.splitlines(),
        fromdesc='Old Page',
        todesc='New Page'
    )
    return diff

def send_notification(diff):
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(
        from_email=SENDGRID_SENDER_EMAIL,
        to_emails=RECIPIENT_EMAIL, 
        subject='Website Content Changed!',
        html_content=f'<html><body><pre>{diff}</pre></body></html>'
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY) 
        sg.send(message)
    except Exception as e:
        print(f"Error sending email: {e}")

# --- Cloud Storage Functions ---
def load_from_storage(url):
    bucket = storage_client.bucket(BUCKET_NAME)
    # Hash the URL to create a consistent prefix
    url_hash = calculate_hash(url)  
    for blob in bucket.list_blobs(prefix=f"{url_hash}_"):
        try:
            content = blob.download_as_text()
            if calculate_hash(content) == blob.name.split("_")[1]:
                print(f"Loaded previous content from Cloud Storage (hash: {blob.name.split('_')[1]})")
                return content
        except:
            pass
    print("No matching previous content found in Cloud Storage.")
    return ""

def save_to_storage(url, content):
    bucket = storage_client.bucket(BUCKET_NAME)
    content_hash = calculate_hash(content)
    url_hash = calculate_hash(url)  # Hash the URL
    blob_name = f"{url_hash}_{content_hash}" 
    blob = bucket.blob(blob_name)

    blob.upload_from_string(content)
    print(f"Saved new content to Cloud Storage (hash: {content_hash})")

def calculate_hash(content):
    return hashlib.md5(content.encode()).hexdigest()

# --- Main Cloud Function ---

@http
def check_website(request):
    try:
        old_content = load_from_storage(TARGET_URL)
        new_content = fetch_website(TARGET_URL)

        if old_content != new_content:
            diff = generate_diff(old_content, new_content)
            send_notification(diff)
            save_to_storage(TARGET_URL, new_content)
        else:
            print("No changes detected.")

    except Exception as e:
        print(f"Error checking website: {e}")
        return "Error", 500

    return "OK", 200
