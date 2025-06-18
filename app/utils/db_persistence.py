import pins
import os
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import logging
import asyncio
import threading
import time
from dotenv import load_dotenv

# Load environment variables from .env file if not already loaded
load_dotenv()

logger = logging.getLogger(__name__)

class PersistentSQLiteDB:
    """SQLite database manager with Posit Connect pins backup/restore functionality"""

    def __init__(self, db_path="data/database.db", pin_name=None, backup_interval_hours=1):
        self.db_path = Path(db_path)
        # Auto-generate pin name with username if not provided
        if pin_name is None:
            username = os.getenv('CONNECT_USERNAME') or 'default_user'
            self.pin_name = f"{username}/python-api-database"
        else:
            self.pin_name = pin_name
        self.backup_interval_hours = backup_interval_hours
        self.last_backup_time = None
        self.last_data_change_time = None
        self.board = None
        self._backup_timer = None
        self._shutdown_requested = False
        self._init_pins_board()
        self._start_backup_timer()
        logger.info(f"Database persistence initialized with pin name: {self.pin_name}")

    def _init_pins_board(self):
        """Initialize pins board connection"""
        try:
            server_url = os.getenv('CONNECT_SERVER', 'https://connect.posit.it')
            api_key = os.getenv('CONNECT_API_KEY')

            if not api_key:
                logger.warning("CONNECT_API_KEY not found, pins backup/restore disabled")
                return

            self.board = pins.board_connect(
                server_url=server_url,
                api_key=api_key
            )
            logger.info("Successfully connected to Posit Connect pins board")
        except Exception as e:
            logger.warning(f"Could not connect to pins board: {e}")
            logger.warning("Database backup/restore will not be available")

    def _start_backup_timer(self):
        """Start the periodic backup timer"""
        def backup_timer():
            while not self._shutdown_requested:
                time.sleep(300)  # Check every 5 minutes
                if self._shutdown_requested:
                    break
                self._check_and_backup_if_needed()

        self._backup_timer = threading.Thread(target=backup_timer, daemon=True)
        self._backup_timer.start()
        logger.info("Backup timer started - checking every 5 minutes")

    def _check_and_backup_if_needed(self):
        """Check if backup is needed based on data changes and time elapsed"""
        if self.should_backup_now():
            logger.info("Scheduled backup triggered due to data changes")
            self.backup_database()

    def mark_data_change(self):
        """Mark that data has changed - call this after any database modification"""
        self.last_data_change_time = datetime.now()
        logger.debug(f"Data change marked at {self.last_data_change_time}")

    def should_backup_now(self):
        """Check if backup should be performed now based on time and changes"""
        if not self.last_data_change_time:
            return False  # No changes to backup

        now = datetime.now()

        # If no backup has been made yet, backup immediately
        if not self.last_backup_time:
            return True

        # If it's been more than the interval since last backup and there are changes
        time_since_backup = now - self.last_backup_time
        if (time_since_backup >= timedelta(hours=self.backup_interval_hours) and
            self.last_data_change_time > self.last_backup_time):
            return True

        return False

    def shutdown(self):
        """Shutdown the backup system and perform final backup if needed"""
        logger.info("Shutting down database persistence manager...")
        self._shutdown_requested = True

        # Perform final backup if there are unsaved changes
        if (self.last_data_change_time and
            (not self.last_backup_time or self.last_data_change_time > self.last_backup_time)):
            logger.info("Performing final backup before shutdown...")
            self.backup_database(force=True)

        # Wait for timer thread to finish
        if self._backup_timer and self._backup_timer.is_alive():
            self._backup_timer.join(timeout=5)

    def backup_database(self, force=False):
        """Backup current database to pin"""
        if not force and not self.should_backup_now():
            logger.debug("Backup skipped - not enough time elapsed or no changes")
            return False

        if not self.board:
            logger.warning("Pins board not available, skipping backup")
            return False

        if not self.db_path.exists():
            logger.warning(f"Database file {self.db_path} does not exist, skipping backup")
            return False

        try:
            # Create metadata
            metadata = {
                "backup_time": datetime.now().isoformat(),
                "file_size": self.db_path.stat().st_size,
                "description": "SQLite database backup for Python FastAPI app",
                "last_data_change": self.last_data_change_time.isoformat() if self.last_data_change_time else None
            }

            # Upload the database file as a pin
            self.board.pin_upload(
                str(self.db_path),
                name=self.pin_name,
                metadata=metadata,
                description="Database backup"
            )
            self.last_backup_time = datetime.now()
            logger.info(f"Database backed up to pin '{self.pin_name}' at {self.last_backup_time}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False

    def restore_database(self):
        """Restore database from pin"""
        if not self.board:
            logger.warning("Pins board not available, skipping restore")
            return False

        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Download from pin - this returns a list of downloaded file paths
            downloaded_files = self.board.pin_download(self.pin_name)

            if not downloaded_files:
                logger.warning("No files downloaded from pin")
                return False

            # Copy the downloaded database file to our target location
            downloaded_db_path = downloaded_files[0]  # Should be the database.db file
            shutil.copy2(downloaded_db_path, self.db_path)

            logger.info(f"Database restored from pin '{self.pin_name}' to {self.db_path}")
            logger.info(f"Downloaded from cache: {downloaded_db_path}")
            return True
        except Exception as e:
            logger.info(f"Could not restore database from pin: {e}")
            logger.info("This is normal for first deployment or when no backup exists")
            return False

    def get_backup_info(self):
        """Get information about the latest backup"""
        if not self.board:
            return None

        try:
            pin_info = self.board.pin_meta(self.pin_name)
            return pin_info
        except Exception as e:
            logger.info(f"No backup information available: {e}")
            return None

    def get_status(self):
        """Get current status of backup system"""
        return {
            "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None,
            "last_data_change_time": self.last_data_change_time.isoformat() if self.last_data_change_time else None,
            "backup_interval_hours": self.backup_interval_hours,
            "pins_available": self.board is not None,
            "database_exists": self.db_path.exists(),
            "database_size": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "next_scheduled_backup": None if not self.last_backup_time else
                (self.last_backup_time + timedelta(hours=self.backup_interval_hours)).isoformat(),
            "backup_needed": self.should_backup_now()
        }

# Global instance
db_manager = PersistentSQLiteDB()
