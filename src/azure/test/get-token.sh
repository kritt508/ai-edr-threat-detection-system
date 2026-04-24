#!/bin/bash

TENANT_ID="d74618be-1bca-49ba-b4dd-eb7604415c8a"
CLIENT_ID="a251e1ed-ff99-4b6f-b23f-ba466008b1c6"
CLIENT_SECRET="fCD8Q~sRRXHTaZMJUoaTqZKkjx19n4fz6LSdKdh9"

RESPONSE=$(curl -X POST -s "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_id=$CLIENT_ID" \
     -d "client_secret=$CLIENT_SECRET" \
     -d "grant_type=client_credentials" \
     -d "scope=https://management.azure.com/.default")

TOKEN=$(echo $RESPONSE | jq -r .access_token)

echo $TOKEN
