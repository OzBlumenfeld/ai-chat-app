#!/bin/bash

# Script to query the RAG model with authentication
# Usage:
#   ./query_model.sh "Your question here" --token "YOUR_JWT_TOKEN"
#   ./query_model.sh "Your question here" --email "user@example.com" --password "password"

set -e

QUESTION="${1:-Who is Oz?}"
HOST="${HOST:-localhost}"
PORT="${PORT:-8080}"
ENDPOINT="http://${HOST}:${PORT}/query"
AUTH_ENDPOINT="http://${HOST}:${PORT}/auth/login"
TOKEN=""

# Parse arguments
while [[ $# -gt 1 ]]; do
  case $2 in
    --token)
      TOKEN="$3"
      shift 2
      ;;
    --email)
      EMAIL="$3"
      shift 2
      ;;
    --password)
      PASSWORD="$3"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# Get token from email/password if not provided
if [ -z "$TOKEN" ]; then
  if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
    echo "Error: Must provide either --token or both --email and --password"
    echo ""
    echo "Usage:"
    echo "  ./query_model.sh \"question\" --token \"TOKEN\""
    echo "  ./query_model.sh \"question\" --email \"user@example.com\" --password \"pass\""
    echo ""
    echo "To register a new user:"
    echo "  curl -X POST 'http://${HOST}:${PORT}/auth/register' \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"email\": \"user@example.com\", \"password\": \"password\"}'"
    exit 1
  fi

  echo "Logging in as $EMAIL..."
  AUTH_RESPONSE=$(curl -s -X POST "$AUTH_ENDPOINT" \
    -H 'Content-Type: application/json' \
    -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

  TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)

  if [ -z "$TOKEN" ]; then
    echo "Login failed. Response:"
    echo "$AUTH_RESPONSE"
    exit 1
  fi
  echo "Login successful. Token: ${TOKEN:0:20}..."
fi

echo ""
echo "Querying: $QUESTION"
echo "Endpoint: $ENDPOINT"
echo ""

curl -X POST "$ENDPOINT" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"question\": \"$QUESTION\"}"

echo ""