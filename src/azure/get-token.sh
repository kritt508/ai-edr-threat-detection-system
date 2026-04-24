#!/bin/bash

source .env

RESPONSE=$(curl -X POST -s "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_id=$CLIENT_ID" \
     -d "client_secret=$CLIENT_SECRET" \
     -d "grant_type=client_credentials" \
     -d "scope=https://management.azure.com/.default")

TOKEN=$(echo $RESPONSE | jq -r .access_token)

echo $TOKEN
