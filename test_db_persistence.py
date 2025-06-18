#!/usr/bin/env python3
"""
Test script for database backup/restore functionality
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.utils.db_persistence import db_manager

def test_backup_restore():
    print("=== Database Backup/Restore Test ===")

    # Check if CONNECT_API_KEY is set
    if not os.getenv('CONNECT_API_KEY'):
        print("Warning: CONNECT_API_KEY not set")
        print("Set it with: export CONNECT_API_KEY=your_api_key")
        return

    # Check username
    username = os.getenv('CONNECT_USERNAME', 'default_user')
    print(f"Using username: {username}")
    if username == 'default_user':
        print("Warning: Using default username. Set CONNECT_USERNAME for proper pin naming.")

    print(f"Pin name: {db_manager.pin_name}")
    print(f"Database path: {db_manager.db_path}")
    print(f"Database exists: {db_manager.db_path.exists()}")
    print(f"Backup interval: {db_manager.backup_interval_hours} hours")

    if db_manager.db_path.exists():
        size = db_manager.db_path.stat().st_size
        print(f"Database size: {size} bytes")

    # Test status
    print("\n--- Testing backup status ---")
    status = db_manager.get_status()
    for key, value in status.items():
        print(f"{key}: {value}")

    # Test backup info
    print("\n--- Testing backup info ---")
    backup_info = db_manager.get_backup_info()
    if backup_info:
        print(f"Backup info: {backup_info}")
    else:
        print("No backup info available")

    # Test data change marking
    print("\n--- Testing data change tracking ---")
    print("Marking data change...")
    db_manager.mark_data_change()
    print(f"Last data change: {db_manager.last_data_change_time}")
    print(f"Should backup now: {db_manager.should_backup_now()}")

    # Test backup
    print("\n--- Testing backup ---")
    backup_success = db_manager.backup_database()
    print(f"Backup successful: {backup_success}")

    # Test force backup
    print("\n--- Testing forced backup ---")
    force_backup_success = db_manager.backup_database(force=True)
    print(f"Forced backup successful: {force_backup_success}")

    # Test restore (caution: this will overwrite local database)
    print("\n--- Testing restore ---")
    restore_input = input("Do you want to test restore? This will overwrite your local database (y/N): ")
    if restore_input.lower() == 'y':
        restore_success = db_manager.restore_database()
        print(f"Restore successful: {restore_success}")
    else:
        print("Skipping restore test")

    print("\n--- Final status ---")
    final_status = db_manager.get_status()
    for key, value in final_status.items():
        print(f"{key}: {value}")

    print("\n=== Test completed ===")
    print("Note: The backup timer runs in background every 5 minutes to check for needed backups")

if __name__ == "__main__":
    test_backup_restore()
