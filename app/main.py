from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import os
from dotenv import load_dotenv
from app.routers import api
from app.models.database import init_db, get_dashboard_data, DATABASE_PATH
from app.utils.cache import cache
from app.utils.websocket_manager import manager
from app.utils.db_persistence import db_manager
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        print("Attempting to restore database from backup...")
        # Try to restore database from pin before initialization
        if not DATABASE_PATH.exists():
            restore_success = db_manager.restore_database()
            if restore_success:
                print("Database restored from backup!")
            else:
                print("No backup found or restore failed, will create fresh database")
        else:
            print("Local database exists, skipping restore")

        print("Initializing database...")
        init_db()
        print("Database initialization complete!")

        # Check if there's existing backup metadata to restore timing info
        backup_info = db_manager.get_backup_info()
        if backup_info:
            try:
                from datetime import datetime
                # Access metadata from pins object
                metadata = getattr(backup_info, 'metadata', {})
                if metadata and 'backup_time' in metadata:
                    backup_time_str = metadata['backup_time']
                    db_manager.last_backup_time = datetime.fromisoformat(backup_time_str.replace('Z', '+00:00'))
                    print(f"Restored backup time from metadata: {db_manager.last_backup_time}")
            except Exception as e:
                print(f"Could not parse backup time from metadata: {e}")

        # Create an initial backup if this is a fresh database
        if not DATABASE_PATH.exists() or DATABASE_PATH.stat().st_size == 0:
            print("Creating initial database backup...")
            db_manager.backup_database(force=True)

    except Exception as e:
        print(f"Database initialization failed: {e}")
        print("App will continue without database initialization")

    yield

    # Shutdown (if needed)
    print("Shutting down...")
    print("Performing shutdown backup...")
    db_manager.shutdown()
    cache.clear()  # Clear cache on shutdown


# Setup templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

app = FastAPI(
    title="Python API",
    description="A FastAPI application with SQLite database",
    lifespan=lifespan,
)

app.include_router(api.router, prefix="/api/v1")


@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboard real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            # We don't expect to receive messages from the client,
            # but we need to handle the connection
            data = await websocket.receive_text()
            # Echo back for debugging if needed
            if data.strip():
                await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/test-websocket")
async def test_websocket():
    """Test endpoint to manually trigger WebSocket notification"""
    await manager.notify_data_change("test_notification", {"message": "Manual test"})
    return {"status": "notification sent"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard page"""
    return templates.TemplateResponse(request, "dashboard.html")


@app.get("/dashboard-stats", response_class=HTMLResponse)
async def get_dashboard_stats():
    """Get dashboard statistics (cached)"""
    # Try to get from cache first
    cached_data = cache.get("dashboard_stats")
    if cached_data is not None:
        return HTMLResponse(content=cached_data)

    # Get fresh data from database
    try:
        dashboard_data = get_dashboard_data()
        stats_html = f'<div class="stat-card"><div class="stat-number">{dashboard_data["total_items"]}</div><div class="stat-label">Total Items</div></div>'

        # Cache for 10 seconds
        cache.set("dashboard_stats", stats_html, ttl_seconds=10)
        return HTMLResponse(content=stats_html)

    except Exception as e:
        error_html = f'<div class="stat-card"><div class="stat-number">❌</div><div class="stat-label">Error loading stats: {str(e)}</div></div>'
        return HTMLResponse(content=error_html)


@app.get("/dashboard-items", response_class=HTMLResponse)
async def get_dashboard_items():
    """Get recent items list (cached)"""
    # Try to get from cache first
    cached_data = cache.get("dashboard_items")
    if cached_data is not None:
        return HTMLResponse(content=cached_data)

    # Get fresh data from database
    try:
        dashboard_data = get_dashboard_data()
        recent_items = dashboard_data['recent_items']

        if not recent_items:
            items_html = '<div class="empty-state"><p>📭 No items found</p><p>Create your first item using the API!</p></div>'
        else:
            items_html = ""
            for item in recent_items:
                # Format the date nicely
                created_at = item.get('created_at', 'Unknown')
                if created_at and created_at != 'Unknown':
                    try:
                        from datetime import datetime
                        # Parse the SQLite datetime format
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_date = created_at
                else:
                    formatted_date = 'Unknown'

                description = item.get('description', 'No description')
                if description and len(description) > 60:
                    description = description[:60] + "..."

                items_html += f'<div class="item"><div class="item-info"><div class="item-name">{item.get("name", "Untitled")}</div><div class="item-description">{description}</div></div><div class="item-meta"><div class="item-id">ID: {item.get("id", "N/A")}</div><div>{formatted_date}</div></div></div>'

        # Cache for 10 seconds
        cache.set("dashboard_items", items_html, ttl_seconds=10)
        return HTMLResponse(content=items_html)

    except Exception as e:
        error_html = f'<div class="empty-state"><p>❌ Error loading items</p><p>{str(e)}</p></div>'
        return HTMLResponse(content=error_html)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/status")
async def status():
    """Get database status and table statistics"""
    try:
        # Get database file size in MiB
        db_size = os.path.getsize(DATABASE_PATH) / (1024 * 1024)  # Convert bytes to MiB

        # Connect to database and get table statistics
        conn = sqlite3.connect(str(DATABASE_PATH))
        cursor = conn.cursor()

        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        # Get record count for each table
        table_stats = {}
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table_stats[table_name] = count

        conn.close()

        return JSONResponse({
            "database_size_mib": round(db_size, 2),
            "tables": table_stats
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to get database statistics",
                "detail": str(e)
            }
        )


@app.post("/admin/backup-database")
async def backup_database():
    """Manual database backup endpoint"""
    try:
        success = db_manager.backup_database(force=True)  # Force backup regardless of timing
        if success:
            return {"success": True, "message": "Database backup completed successfully"}
        else:
            return {"success": False, "message": "Database backup failed - check logs for details"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Database backup error: {str(e)}"}
        )


@app.get("/admin/backup-status")
async def get_backup_status():
    """Get detailed backup system status"""
    try:
        status = db_manager.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error retrieving backup status: {str(e)}"}
        )


@app.post("/admin/restore-database")
async def restore_database():
    """Manual database restore endpoint - USE WITH CAUTION"""
    try:
        success = db_manager.restore_database()
        if success:
            # Re-initialize database connections after restore
            return {"success": True, "message": "Database restored successfully from backup"}
        else:
            return {"success": False, "message": "Database restore failed - check logs for details"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Database restore error: {str(e)}"}
        )


@app.get("/admin/backup-info")
async def get_backup_info():
    """Get information about the latest database backup"""
    try:
        backup_info = db_manager.get_backup_info()
        if backup_info:
            return {"success": True, "backup_info": backup_info}
        else:
            return {"success": False, "message": "No backup information available"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error retrieving backup info: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
