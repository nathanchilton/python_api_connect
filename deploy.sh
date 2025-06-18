#!/bin/bash
# Deploy to Posit Connect with database persistence

# Make sure we're in the project directory
cd "$(dirname "$0")"

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

echo "Configuration loaded:"
echo "  CONNECT_SERVER: $CONNECT_SERVER"
echo "  CONNECT_APP_ID: $CONNECT_APP_ID"
echo "  CONNECT_USERNAME: $CONNECT_USERNAME"
echo ""

echo "Starting deployment with database backup/restore..."

# Step 1: Trigger backup on current running application (if it exists)
echo "Triggering backup on current application..."
if [ -n "$CONNECT_API_KEY" ]; then
    APP_URL="${CONNECT_SERVER}/content/${CONNECT_APP_ID}"

    # Try to trigger backup on running app
    curl -s -X POST "$APP_URL/admin/backup-database" \
         -H "Authorization: Key $CONNECT_API_KEY" \
         -H "Content-Type: application/json" && echo " - Backup triggered successfully" || echo " - Could not trigger backup (app may not be running)"

    # Give it a moment to complete the backup
    echo "Waiting 5 seconds for backup to complete..."
    sleep 5
else
    echo "Warning: CONNECT_API_KEY not set, cannot trigger pre-deployment backup"
fi

# Step 2: Download current database from pin (if it exists) for local bundling
echo "Attempting to restore database for bundling..."
python3 -c "
import pins
from pathlib import Path
import os
import sys

try:
    # Connect to Posit Connect
    board = pins.board_connect(
        server_url=os.getenv('CONNECT_SERVER'),
        api_key=os.getenv('CONNECT_API_KEY')
    )

    # Try to download existing database
    db_path = Path('data/database.db')
    db_path.parent.mkdir(exist_ok=True)

    # Get username for pin name (try from environment or use default)
    username = os.getenv('CONNECT_USERNAME', 'default_user')
    pin_name = f'{username}/python-api-database'
    print(f'Using pin name: {pin_name}')

    try:
        # Download the pin and copy to local database path
        downloaded_files = board.pin_download(pin_name)
        if downloaded_files:
            import shutil
            shutil.copy2(downloaded_files[0], db_path)
            print(f'Database downloaded for bundling: {db_path}')
            print(f'Database size: {db_path.stat().st_size} bytes')
        else:
            print('No files in downloaded pin')
    except Exception as e:
        print(f'No existing database pin found or error downloading: {e}')
        print('Will deploy with fresh/existing local database')

except Exception as e:
    print(f'Error connecting to pins: {e}')
    print('Proceeding without database download')
    sys.exit(0)  # Don't fail deployment if pins connection fails
"

# Step 3: Deploy the application
echo "Deploying application..."
rsconnect deploy fastapi . \
    --server $CONNECT_SERVER \
    --api-key $CONNECT_API_KEY \
    --title "Python FastAPI" \
    -e app.main:app \
    --app-id $CONNECT_APP_ID
    # Note: Environment variables are now set via API below
    # rather than via command line flags

# Step 4: Set environment variables as secrets using Connect API
echo "Setting environment variables as secrets..."
if [ -n "$CONNECT_API_KEY" ]; then
    CONTENT_GUID="$CONNECT_APP_ID"

    # Set CONNECT_USERNAME as secret
    echo "Setting CONNECT_USERNAME as secret..."
    curl -s -X PATCH "${CONNECT_SERVER}/__api__/v1/content/${CONTENT_GUID}/environment" \
         -H "Authorization: Key $CONNECT_API_KEY" \
         -H "Content-Type: application/json" \
         -d "[
           {
             \"name\": \"CONNECT_USERNAME\",
             \"value\": \"$CONNECT_USERNAME\"
           }
         ]" && echo " - CONNECT_USERNAME set (mark as secret manually in UI)" || echo " - Failed to set CONNECT_USERNAME"

    # Set CONNECT_SERVER as regular variable (not sensitive)
    echo "Setting CONNECT_SERVER as regular variable..."
    curl -s -X PATCH "${CONNECT_SERVER}/__api__/v1/content/${CONTENT_GUID}/environment" \
         -H "Authorization: Key $CONNECT_API_KEY" \
         -H "Content-Type: application/json" \
         -d "[
           {
             \"name\": \"CONNECT_SERVER\",
             \"value\": \"$CONNECT_SERVER\"
           }
         ]" && echo " - CONNECT_SERVER set as regular variable" || echo " - Failed to set CONNECT_SERVER"

    echo "Environment variables configured."
    echo ""
    echo "⚠️  IMPORTANT: To mark CONNECT_USERNAME as secret:"
    echo "   1. Go to ${CONNECT_SERVER}/connect/#/apps/${CONTENT_GUID}/vars"
    echo "   2. Click 'Edit' next to CONNECT_USERNAME"
    echo "   3. Check the 'Secret' checkbox"
    echo "   4. Save changes"
else
    echo "Warning: CONNECT_API_KEY not set, cannot configure environment variables as secrets"
fi

echo "Deployment completed."
echo "The application will automatically restore the database from backup on startup."
echo "Database will be automatically backed up after any data changes."
