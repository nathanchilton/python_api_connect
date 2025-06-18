# Database Persistence with Posit Connect Pins

✅ **STATUS: FULLY IMPLEMENTED AND TESTED**

This application now includes intelligent SQLite database backup and restore functionality using Posit Connect's pins feature.

All functionality has been tested and is working correctly:

- ✅ Backup functionality (using `pin_upload()`)
- ✅ Restore functionality (using `pin_download()` with proper file copying)
- ✅ Admin API endpoints
- ✅ Deploy script database bundling
- ✅ Environment variable configuration
- ✅ Background timing and monitoring

## How It Works

1. **On Startup**: The application attempts to restore the database from a pin backup
2. **During Runtime**: Database changes are tracked and smart backup decisions are made
3. **Scheduled Backups**: Background timer checks every 5 minutes for needed backups
4. **On Shutdown**: Final backup is performed if there are unsaved changes
5. **On Deployment**: The deploy script triggers a backup before deploying the new version

## Intelligent Backup Features

- **Time-Based Backups**: Backups only occur if at least 1 hour has passed since the last backup
- **Change Tracking**: Data changes are tracked, backups only happen when there are actual changes
- **Scheduled Monitoring**: Background timer checks every 5 minutes for needed backups
- **Shutdown Protection**: Automatic backup during application shutdown if changes exist
- **Manual Override**: Admin endpoints can force immediate backups regardless of timing

## Features

- **Smart Backup**: Database is backed up only when needed (changes + time interval)
- **Startup Restore**: Fresh deployments automatically restore from the latest backup
- **Background Timer**: Automated backup checking every 5 minutes
- **Shutdown Backup**: Final backup before application shutdown
- **Manual Controls**: Admin endpoints for manual backup/restore operations
- **Status Monitoring**: Detailed backup system status and timing information

## Admin Endpoints

- `POST /admin/backup-database` - Manually trigger a database backup (forced)
- `POST /admin/restore-database` - Manually restore from backup (USE WITH CAUTION)
- `GET /admin/backup-info` - Get information about the latest backup
- `GET /admin/backup-status` - Get detailed backup system status and timing

## Backup Logic

### Automatic Backups

- Data changes are marked when items are created, updated, or deleted
- Backups occur only if:
  - At least 1 hour has passed since the last backup AND
  - There have been data changes since the last backup
- Background timer checks every 5 minutes for needed backups

### Manual Backups

- Admin endpoint forces immediate backup regardless of timing
- Useful for pre-maintenance or critical data protection

### Shutdown Backups

- Automatic backup if unsaved changes exist when application shuts down
- Protects against data loss during Posit Connect sleep/restart cycles

## Environment Variables

### Local Development
The application automatically loads environment variables from a `.env` file in the project root.

- `CONNECT_API_KEY` - Required for pins functionality
- `CONNECT_SERVER` - Server URL (defaults to <https://connect.posit.it>)
- `CONNECT_USERNAME` - Username for pin naming (defaults to 'default_user')

### Setting up .env file for Local Development

Create a `.env` file in the project root with:

```env
CONNECT_API_KEY=your_api_key_here
CONNECT_USERNAME=your_username
CONNECT_SERVER=https://your-connect-server.com
```

### Posit Connect Deployment

For production deployment on Posit Connect:

1. **Automatic Variables**: `CONNECT_API_KEY` is automatically available
2. **Deploy-time Variables**: Set via `--env` flags in deploy script
3. **API-based Secrets**: Configured via Posit Connect API as secrets
4. **Runtime Variables**: Set through Posit Connect web interface

#### Setting Variables via Deploy Script

The deploy script sets environment variables automatically:

```bash
# Basic deployment with environment variables
rsconnect deploy fastapi . \
    --env CONNECT_USERNAME=your_username \
    --env CONNECT_SERVER=https://your-connect-server.com

# Automatically configure variables via API
curl -X PATCH "https://your-connect-server.com/__api__/v1/content/${CONTENT_GUID}/environment" \
     -H "Authorization: Key $CONNECT_API_KEY" \
     -d '[{"name": "CONNECT_USERNAME", "value": "your_username"}]'
```

**Note**: The Posit Connect API doesn't support setting the "secret" flag programmatically. Variables will be set as regular environment variables and need to be manually marked as secrets in the UI.

#### Manual Secrets Configuration

Run the dedicated configuration script:

```bash
./configure_secrets.sh
```

This will set the environment variables, then manually mark sensitive ones as secrets in the Connect UI.

#### Setting Variables as Secrets in Posit Connect UI (Required for Secrets)

1. Login to Posit Connect → Navigate to your app
2. Go to **Settings** → **Runtime** → **Environment Variables**
3. Find `CONNECT_USERNAME` and click the "Edit" button
4. Check the **"Secret"** checkbox
5. Save the changes

Variables that should be marked as secrets:
- `CONNECT_USERNAME` = `your_username` ✓ **Mark as secret**
- `CONNECT_SERVER` = `https://your-connect-server.com` (leave as regular variable)

## Configuration

- **Backup Interval**: 1 hour (configurable in PersistentSQLiteDB constructor)
- **Check Frequency**: 5 minutes (background timer)
- **Pin Name**: `{username}/python-api-database` (automatically includes username)
- **Pin Type**: File (SQLite database)

## Status Information

The backup system tracks:

- Last backup time
- Last data change time
- Backup interval configuration
- Next scheduled backup time
- Whether backup is currently needed
- Database size and existence

## Testing

Run the enhanced test script to verify backup/restore functionality:

```bash
export CONNECT_API_KEY=your_api_key
python test_db_persistence.py
```

## Deployment

The enhanced `deploy.sh` script now:

1. Triggers backup on the current running application
2. Downloads the latest database backup for bundling
3. Deploys the application with the restored database

## Limitations

- Pins feature requires a valid `CONNECT_API_KEY`
- If pins is unavailable, the app continues without backup/restore
- Large databases may take longer to backup/restore
- Manual restore operations will overwrite the current database
- Background timer runs as daemon thread (stops when main process stops)

## Monitoring

Check the application logs for backup/restore status messages:

- "Database backed up to pin 'python-api-database'"
- "Database restored from pin 'python-api-database'"
- "Scheduled backup triggered due to data changes"
- "Backup skipped - not enough time elapsed or no changes"
- "Performing final backup before shutdown"
- Warnings if pins board is unavailable
