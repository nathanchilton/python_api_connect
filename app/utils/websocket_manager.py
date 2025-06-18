"""
WebSocket manager for real-time dashboard notifications
"""
import asyncio
import json
import time
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket
import logging
from queue import Queue
import threading

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for dashboard notifications"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.last_notification_time = 0
        self.min_notification_interval = 1.0  # Minimum 1 second between notifications
        self.notification_queue = Queue()
        self.processing_task = None

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")

        # Start the notification processing task if not already running
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_notifications())

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected WebSockets with rate limiting"""
        current_time = time.time()

        print(f"[DEBUG] Broadcast called with {len(self.active_connections)} connections")
        print(f"[DEBUG] Rate limit check: {current_time} - {self.last_notification_time} >= {self.min_notification_interval}")

        # Rate limiting: don't send notifications more than once per second
        if current_time - self.last_notification_time < self.min_notification_interval:
            print(f"[DEBUG] Rate limited - skipping broadcast")
            return

        if not self.active_connections:
            print(f"[DEBUG] No active connections - skipping broadcast")
            return

        self.last_notification_time = current_time
        message_str = json.dumps(message)

        print(f"[DEBUG] Broadcasting message: {message_str}")

        # Send to all connections, remove failed ones
        disconnected = set()
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message_str)
                print(f"[DEBUG] Sent message to connection")
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {e}")
                disconnected.add(connection)

        # Remove disconnected WebSockets
        self.active_connections -= disconnected

        if disconnected:
            logger.info(f"Removed {len(disconnected)} disconnected WebSockets")

    async def notify_data_change(self, change_type: str, details: Optional[Dict[str, Any]] = None):
        """Notify all clients about data changes"""
        message = {
            "type": "data_change",
            "change_type": change_type,  # "items_updated", "stats_updated", etc.
            "timestamp": time.time(),
            "details": details or {}
        }

        await self.broadcast(message)
        logger.info(f"Broadcasted {change_type} notification to {len(self.active_connections)} connections")

    def queue_notification(self, change_type: str, details: Optional[Dict[str, Any]] = None):
        """Queue a notification to be processed by the async task"""
        try:
            self.notification_queue.put((change_type, details or {}))
        except Exception as e:
            logger.error(f"Failed to queue notification: {e}")

    async def _process_notifications(self):
        """Process queued notifications in the background"""
        while True:
            try:
                # Check if there are any notifications to process
                notifications = []
                while not self.notification_queue.empty():
                    try:
                        notifications.append(self.notification_queue.get_nowait())
                    except:
                        break

                # Process notifications
                for change_type, details in notifications:
                    await self.notify_data_change(change_type, details)

                # Wait a bit before checking again
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing notifications: {e}")
                await asyncio.sleep(1)


# Global connection manager instance
manager = ConnectionManager()
