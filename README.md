# Website Change Monitor

This project is a Google Cloud Function that monitors specified websites for changes and sends notifications when changes are detected.

## Project Structure

```
.
├── README.md
├── deploy.sh
└── gcf/
    ├── main.py
    └── requirements.txt
```

- `README.md`: This file, containing project documentation.
- `deploy.sh`: Shell script for deploying the function to Google Cloud and setting up the Cloud Scheduler.
- `gcf/`: Directory containing the Cloud Function code.
  - `main.py`: The main Python script for the Cloud Function.
  - `requirements.txt`: List of Python dependencies.

## Purpose

The Website Change Monitor is designed to periodically check specified web pages for changes. When changes are detected, it sends a notification via email.

## Features

- Monitors web pages for changes
- Stores webpage content in Google Cloud Storage for comparison
- Sends email notifications using SendGrid when changes are detected
- Can be scheduled to run at specified intervals using Google Cloud Scheduler

## Prerequisites

- Google Cloud Platform account
- Google Cloud SDK installed and configured
- SendGrid account for email notifications

## Configuration

Before deploying, ensure you have set up the following:

1. Google Cloud Project
2. Google Cloud Storage bucket
3. SendGrid API key (to be stored in Secret Manager)

The following environment variables are used by the function:

- `SENDGRID_API_KEY`: Your SendGrid API key (stored in Secret Manager)
- `SENDGRID_SENDER_EMAIL`: The email address to send notifications from
- `RECIPIENT_EMAIL`: The email address to send notifications to
- `BUCKET_NAME`: The name of your Google Cloud Storage bucket

These variables can be updated in the `deploy.sh` script.

### Setting up Secret Manager

To securely store your SendGrid API key:

1. Enable the Secret Manager API in your Google Cloud project.
2. Create a secret:

```bash
echo -n "your_sendgrid_api_key" | gcloud secrets create sendgrid-api-key --data-file=-
```

3. Grant the Cloud Function access to the secret:

```bash
gcloud secrets add-iam-policy-binding sendgrid-api-key \
    --member=serviceAccount:YOUR_PROJECT_ID@appspot.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor
```

Replace `YOUR_PROJECT_ID` with your actual Google Cloud project ID.

## Deployment

To deploy the function and set up the Cloud Scheduler job, run the `deploy.sh` script:

```bash
./deploy.sh
```

This script contains the necessary `gcloud` commands to deploy the function, set environment variables, and create the Cloud Scheduler job.

## Usage

Once deployed and scheduled, the function will automatically check the specified website at the set interval.

### Monitoring a Different Website

To monitor a different website, you need to update or create a new Cloud Scheduler job. Here's an example command:

```bash
gcloud scheduler jobs create http new-website-monitor \
  --location us-central1 \
  --schedule "*/5 * * * *" \
  --uri "https://REGION-PROJECT_ID.cloudfunctions.net/website-change-monitor" \
  --http-method POST \
  --headers "Content-Type=application/json" \
  --message-body '{"url": "https://www.example.com/page-to-monitor"}' \
  --time-zone "America/Los_Angeles"
```

Replace the following:
- `new-website-monitor`: A unique name for your new monitoring job
- `us-central1`: The location where you want to create the job
- `REGION-PROJECT_ID`: Your function's region and project ID
- `"*/5 * * * *"`: The schedule (every 5 minutes in this example)
- `"https://www.example.com/page-to-monitor"`: The URL you want to monitor
- `"America/Los_Angeles"`: Your preferred timezone

You can create multiple scheduler jobs to monitor different websites.

## Monitoring and Logs

You can monitor the function's executions and view logs in the Google Cloud Console under the "Cloud Functions" and "Cloud Logging" sections.

## Troubleshooting

If you encounter issues:

1. Check the Cloud Function logs in the Google Cloud Console.
2. Ensure all required environment variables are set correctly in the `deploy.sh` script.
3. Verify that the Google Cloud Storage bucket exists and is accessible.
4. Check that the SendGrid API key secret is properly set up in Secret Manager and accessible to the function.

## How It Works

The Website Change Monitor uses a combination of cloud services and hashing algorithms to efficiently detect and report changes in web content. Here's a breakdown of the process:

1. URL Hashing:
   - When a URL is submitted for monitoring, it's first hashed using MD5.
   - The hash function is: `url_hash = hashlib.md5(target_url.encode()).hexdigest()`
   - This URL hash serves as a unique identifier for the website in our storage system.

2. Content Fetching and Parsing:
   - The function fetches the content of the specified URL.
   - It then uses BeautifulSoup to parse the HTML and extract the main content (typically the `<main>` or `<body>` element).

3. Content Storage:
   - The parsed content is hashed using MD5: `content_hash = hashlib.md5(content.encode()).hexdigest()`
   - A unique blob name is created in the format: `{url_hash}_{content_hash}`
   - This blob is stored in Google Cloud Storage, allowing for efficient comparison and storage of multiple versions.

4. Change Detection:
   - When checking for changes, the function retrieves the latest stored content for the URL.
   - It compares this stored content with the newly fetched and parsed content.
   - If there's a difference, it's considered a change.

5. Notification:
   - If a change is detected, the function sends an email notification via SendGrid.
   - The notification includes both the old and new content for comparison.

6. Scheduling:
   - Google Cloud Scheduler is used to periodically trigger the function.
   - Each scheduled job corresponds to a specific URL to be monitored.

This approach allows for:
- Efficient storage and retrieval of web content
- Quick comparison between versions
- Scalability to monitor multiple websites
- Secure handling of sensitive information (like API keys)

The use of content hashing ensures that only unique versions of a page are stored, saving storage space and allowing for easy identification of changes.

## Contributing

Contributions to improve the project are welcome. Please follow the standard fork-and-pull request workflow.

## License

This project is licensed under the GNU General Public License v2.0 (GPL-2.0).
This means:

You are free to use, modify, and distribute this software.
If you distribute this software or any derivative works, you must make the source code available under the same license.
There is no warranty for this program, and the author(s) cannot be held liable for any damages caused by its use.

For the full license text, see https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html
