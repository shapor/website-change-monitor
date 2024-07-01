#!/bin/bash

gcloud scheduler jobs create http sfusd-enrollment-monitor \
  --location us-central1 \
  --schedule "*/2 * * * *" \
  --uri "https://us-central1-shapor-dev.cloudfunctions.net/website-change-monitor" \
  --http-method POST \
  --headers "Content-Type=application/json" \
  --message-body '{"url": "https://www.sfusd.edu/schools/enroll/apply/open-enrollment"}' \
  --time-zone "America/Los_Angeles"
