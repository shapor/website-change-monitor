#!/bin/bash

gcloud functions deploy website-change-monitor \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point check_website \
  --source ./gcf/ \
  --set-env-vars SENDGRID_SENDER_EMAIL=change-notifier@shapor.com,RECIPIENT_EMAIL=shapor@gmail.com,BUCKET_NAME=website-differ
