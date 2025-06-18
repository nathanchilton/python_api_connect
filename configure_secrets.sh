#!/bin/bash
# Configure environment variables as secrets in Posit Connect

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading configuration from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Validate required environment variables
required_vars=("CONNECT_API_KEY" "CONNECT_APP_ID" "CONNECT_USERNAME" "CONNECT_SERVER")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "Error: Required environment variables are not set:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please either:"
    echo "  1. Copy .env.example to .env and fill in your values"
    echo "  2. Set the variables in your environment"
    exit 1
fi

CONTENT_GUID="$CONNECT_APP_ID"
SERVER_URL="$CONNECT_SERVER"

echo "Configuring environment variables for Posit Connect app..."
echo "  Server: $SERVER_URL"
echo "  App ID: $CONTENT_GUID"
echo ""

# Function to set environment variable
set_env_var() {
    local name=$1
    local value=$2
    local is_secret=$3

    echo "Setting $name as $([ "$is_secret" = "true" ] && echo "secret" || echo "regular variable")..."

    response=$(curl -s -w "%{http_code}" -X PATCH "${SERVER_URL}/__api__/v1/content/${CONTENT_GUID}/environment" \
         -H "Authorization: Key $CONNECT_API_KEY" \
         -H "Content-Type: application/json" \
         -d "[
           {
             \"name\": \"$name\",
             \"value\": \"$value\"
           }
         ]")

    http_code="${response: -3}"
    if [ "$http_code" = "200" ]; then
        echo " ✓ $name configured successfully"
        if [ "$is_secret" = "true" ]; then
            echo "   Note: You'll need to manually mark this as secret in the Posit Connect UI"
        fi
    else
        echo " ✗ Failed to configure $name (HTTP $http_code)"
        echo "   Response: ${response%???}"
    fi
}

# Set environment variables
set_env_var "CONNECT_USERNAME" "$CONNECT_USERNAME" "true"
set_env_var "CONNECT_SERVER" "$CONNECT_SERVER" "false"

echo ""
echo "Environment variable configuration complete!"
echo "You can verify the settings in the Posit Connect web interface:"
echo "${SERVER_URL}/connect/#/apps/${CONTENT_GUID}/vars"
