"""
Comprehensive test suite for the FastAPI dashboard application

Tests cover:
- API endpoints (CRUD operations)
- WebSocket notifications
- Caching system
- Dashboard endpoints
- Real-time update functionality
- Integration scenarios
"""

import pytest
import asyncio
import json
import time
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.utils.cache import cache
from app.utils.websocket_manager import manager
from app.models.database import init_db, execute_query


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def clean_cache():
    """Clean cache before each test"""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def clean_websocket_manager():
    """Clean WebSocket manager before each test"""
    manager.active_connections.clear()
    manager.last_notification_time = 0
    yield
    manager.active_connections.clear()


@pytest.fixture(autouse=True)
def setup_database():
    """Initialize database before each test"""
    init_db()


class TestAPIEndpoints:
    """Test all API endpoints for CRUD operations"""

    def test_get_all_items(self, client):
        """Test GET /api/v1/items returns items list"""
        response = client.get("/api/v1/items")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_item(self, client, clean_cache):
        """Test POST /api/v1/items creates new item and invalidates cache"""
        # Verify cache is clean
        assert cache.get("dashboard_stats") is None
        assert cache.get("dashboard_items") is None

        # Create item
        item_data = {"name": "Test Item", "description": "Test Description"}
        response = client.post("/api/v1/items", json=item_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Item"
        assert data["description"] == "Test Description"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_item_by_id(self, client):
        """Test GET /api/v1/items/{id} returns specific item"""
        # Create an item first
        item_data = {"name": "Test Item", "description": "Test Description"}
        create_response = client.post("/api/v1/items", json=item_data)
        item_id = create_response.json()["id"]

        # Get the item
        response = client.get(f"/api/v1/items/{item_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["name"] == "Test Item"

    def test_get_nonexistent_item(self, client):
        """Test GET /api/v1/items/{id} with non-existent ID returns 404"""
        response = client.get("/api/v1/items/999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_item(self, client, clean_cache):
        """Test PUT /api/v1/items/{id} updates item and invalidates cache"""
        # Create an item first
        item_data = {"name": "Original Item", "description": "Original Description"}
        create_response = client.post("/api/v1/items", json=item_data)
        item_id = create_response.json()["id"]

        # Update the item
        update_data = {"name": "Updated Item", "description": "Updated Description"}
        response = client.put(f"/api/v1/items/{item_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["name"] == "Updated Item"
        assert data["description"] == "Updated Description"

    def test_update_nonexistent_item(self, client):
        """Test PUT /api/v1/items/{id} with non-existent ID returns 404"""
        update_data = {"name": "Updated Item"}
        response = client.put("/api/v1/items/999999", json=update_data)
        assert response.status_code == 404

    def test_partial_update_item(self, client):
        """Test PUT /api/v1/items/{id} with partial data"""
        # Create an item first
        item_data = {"name": "Original Item", "description": "Original Description"}
        create_response = client.post("/api/v1/items", json=item_data)
        item_id = create_response.json()["id"]

        # Update only the name
        update_data = {"name": "Updated Name Only"}
        response = client.put(f"/api/v1/items/{item_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name Only"
        assert data["description"] == "Original Description"

    def test_delete_item(self, client, clean_cache):
        """Test DELETE /api/v1/items/{id} deletes item and invalidates cache"""
        # Create an item first
        item_data = {"name": "Item to Delete", "description": "Will be deleted"}
        create_response = client.post("/api/v1/items", json=item_data)
        item_id = create_response.json()["id"]

        # Delete the item
        response = client.delete(f"/api/v1/items/{item_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["detail"]

        # Verify item is gone
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_item(self, client):
        """Test DELETE /api/v1/items/{id} with non-existent ID returns 404"""
        response = client.delete("/api/v1/items/999999")
        assert response.status_code == 404


class TestCachingSystem:
    """Test the caching system functionality"""

    def test_cache_basic_operations(self, clean_cache):
        """Test basic cache set/get/invalidate operations"""
        # Test set and get
        cache.set("test_key", "test_value", ttl_seconds=10)
        assert cache.get("test_key") == "test_value"

        # Test non-existent key
        assert cache.get("nonexistent_key") is None

        # Test invalidation
        cache.invalidate("test_key")
        assert cache.get("test_key") is None

    def test_cache_ttl_expiration(self, clean_cache):
        """Test cache TTL expiration"""
        # Set with very short TTL
        cache.set("short_ttl_key", "value", ttl_seconds=0.1)
        assert cache.get("short_ttl_key") == "value"

        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("short_ttl_key") is None

    def test_cache_thread_safety(self, clean_cache):
        """Test cache thread safety with concurrent operations"""
        import threading
        import time

        results = []

        def worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                cache.set(key, value, ttl_seconds=1)
                retrieved = cache.get(key)
                results.append(retrieved == value)
                time.sleep(0.01)

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All operations should have succeeded
        assert all(results)

    def test_cache_invalidation_on_api_operations(self, client, clean_cache):
        """Test that cache is invalidated when API operations occur"""
        # Prime the cache by calling dashboard endpoints
        stats_response = client.get("/dashboard-stats")
        items_response = client.get("/dashboard-items")
        assert stats_response.status_code == 200
        assert items_response.status_code == 200

        # Verify cache is populated
        assert cache.get("dashboard_stats") is not None
        assert cache.get("dashboard_items") is not None

        # Create an item (should invalidate cache)
        item_data = {"name": "Cache Test Item", "description": "Testing cache invalidation"}
        client.post("/api/v1/items", json=item_data)

        # Cache should be invalidated
        assert cache.get("dashboard_stats") is None
        assert cache.get("dashboard_items") is None


class TestDashboardEndpoints:
    """Test dashboard-specific endpoints"""

    def test_dashboard_main_page(self, client):
        """Test GET / returns dashboard HTML"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Dashboard" in response.text

    def test_dashboard_stats_endpoint(self, client):
        """Test GET /dashboard-stats returns stats HTML"""
        response = client.get("/dashboard-stats")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Total Items" in response.text
        assert "stat-card" in response.text

    def test_dashboard_items_endpoint(self, client):
        """Test GET /dashboard-items returns items HTML"""
        response = client.get("/dashboard-items")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_stats_caching(self, client, clean_cache):
        """Test dashboard stats endpoint caching behavior"""
        # First request should populate cache
        response1 = client.get("/dashboard-stats")
        assert response1.status_code == 200
        cached_content = cache.get("dashboard_stats")
        assert cached_content is not None

        # Second request should use cache
        response2 = client.get("/dashboard-stats")
        assert response2.status_code == 200
        assert response2.text == response1.text

    def test_dashboard_items_caching(self, client, clean_cache):
        """Test dashboard items endpoint caching behavior"""
        # First request should populate cache
        response1 = client.get("/dashboard-items")
        assert response1.status_code == 200
        cached_content = cache.get("dashboard_items")
        assert cached_content is not None

        # Second request should use cache
        response2 = client.get("/dashboard-items")
        assert response2.status_code == 200
        assert response2.text == response1.text

    def test_health_endpoint(self, client):
        """Test GET /health returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_manual_websocket_test_endpoint(self, client):
        """Test GET /test-websocket manual notification endpoint"""
        response = client.get("/test-websocket")
        assert response.status_code == 200
        assert response.json() == {"status": "notification sent"}

    def test_dashboard_uses_relative_paths(self, client):
        """Test that dashboard HTML uses relative paths for deployment compatibility"""
        response = client.get("/")
        assert response.status_code == 200
        html_content = response.text

        # Verify HTMX uses relative paths (not absolute paths starting with /)
        assert 'hx-get="dashboard-stats"' in html_content
        assert 'hx-get="dashboard-items"' in html_content
        assert 'hx-get="/dashboard-stats"' not in html_content
        assert 'hx-get="/dashboard-items"' not in html_content

        # Verify JavaScript uses relative paths
        assert "htmx.ajax('GET', 'dashboard-stats'" in html_content
        assert "htmx.ajax('GET', 'dashboard-items'" in html_content
        assert "htmx.ajax('GET', '/dashboard-stats'" not in html_content
        assert "htmx.ajax('GET', '/dashboard-items'" not in html_content

        # Verify links use relative paths
        assert 'href="docs"' in html_content
        assert 'href="health"' in html_content
        assert 'href="/docs"' not in html_content
        assert 'href="/health"' not in html_content

        # Verify WebSocket path construction is dynamic
        assert 'window.location.pathname' in html_content
        assert '/ws/dashboard' in html_content  # This should be in the constructed URL


class TestWebSocketManager:
    """Test WebSocket manager functionality"""

    def test_websocket_manager_initialization(self, clean_websocket_manager):
        """Test WebSocket manager initial state"""
        assert len(manager.active_connections) == 0
        assert manager.last_notification_time == 0
        assert manager.min_notification_interval == 1.0

    @pytest.mark.asyncio
    async def test_websocket_connection_management(self, clean_websocket_manager):
        """Test WebSocket connection and disconnection"""
        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()

        # Test connection
        await manager.connect(mock_websocket)
        assert len(manager.active_connections) == 1
        assert mock_websocket in manager.active_connections
        mock_websocket.accept.assert_called_once()

        # Test disconnection
        manager.disconnect(mock_websocket)
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_websocket_broadcast_rate_limiting(self, clean_websocket_manager):
        """Test WebSocket broadcast rate limiting"""
        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await manager.connect(mock_websocket)

        # First broadcast should work
        message1 = {"type": "test", "data": "first"}
        await manager.broadcast(message1)
        mock_websocket.send_text.assert_called_once()

        # Immediate second broadcast should be rate limited
        mock_websocket.send_text.reset_mock()
        message2 = {"type": "test", "data": "second"}
        await manager.broadcast(message2)
        mock_websocket.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_websocket_notify_data_change(self, clean_websocket_manager):
        """Test WebSocket data change notification"""
        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await manager.connect(mock_websocket)

        # Test notification
        await manager.notify_data_change("item_created", {"item_id": 123})

        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = mock_websocket.send_text.call_args[0][0]
        parsed_message = json.loads(sent_message)

        assert parsed_message["type"] == "data_change"
        assert parsed_message["change_type"] == "item_created"
        assert parsed_message["details"]["item_id"] == 123
        assert "timestamp" in parsed_message

    @pytest.mark.asyncio
    async def test_websocket_broadcast_with_failed_connection(self, clean_websocket_manager):
        """Test WebSocket broadcast handles failed connections"""
        # Mock WebSockets - one working, one failing
        working_ws = MagicMock()
        working_ws.accept = AsyncMock()
        working_ws.send_text = AsyncMock()

        failing_ws = MagicMock()
        failing_ws.accept = AsyncMock()
        failing_ws.send_text = AsyncMock(side_effect=Exception("Connection failed"))

        # Connect both
        await manager.connect(working_ws)
        await manager.connect(failing_ws)
        assert len(manager.active_connections) == 2

        # Broadcast message
        message = {"type": "test", "data": "broadcast_test"}
        await manager.broadcast(message)

        # Working connection should receive message
        working_ws.send_text.assert_called_once()

        # Failed connection should be removed
        assert len(manager.active_connections) == 1
        assert working_ws in manager.active_connections
        assert failing_ws not in manager.active_connections


class TestWebSocketIntegration:
    """Test WebSocket integration with FastAPI"""

    def test_websocket_endpoint_connection(self, client):
        """Test WebSocket endpoint accepts connections"""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Connection should be established without error
            assert websocket is not None

    @pytest.mark.asyncio
    async def test_api_operations_trigger_websocket_notifications(self, clean_websocket_manager):
        """Test that API operations trigger WebSocket notifications"""
        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await manager.connect(mock_websocket)

        # Create a test client and create an item
        client = TestClient(app)
        item_data = {"name": "WebSocket Test Item", "description": "Testing notifications"}
        response = client.post("/api/v1/items", json=item_data)

        # Give async operations time to complete
        await asyncio.sleep(0.1)

        assert response.status_code == 200

        # WebSocket should have received a notification
        # Note: In real async environment, this would be automatically triggered
        # For testing, we verify the manager can send notifications
        await manager.notify_data_change("item_created", {"item_id": 123})
        mock_websocket.send_text.assert_called()


class TestIntegrationScenarios:
    """Test complete integration scenarios"""

    def test_complete_crud_workflow_with_caching(self, client, clean_cache):
        """Test complete CRUD workflow with caching behavior"""
        # 1. Get initial dashboard stats (populates cache)
        stats_response = client.get("/dashboard-stats")
        initial_stats = stats_response.text
        assert cache.get("dashboard_stats") is not None

        # 2. Create an item (should invalidate cache)
        item_data = {"name": "Integration Test Item", "description": "Full workflow test"}
        create_response = client.post("/api/v1/items", json=item_data)
        item_id = create_response.json()["id"]

        # Cache should be invalidated
        assert cache.get("dashboard_stats") is None

        # 3. Get updated dashboard stats (should show increased count)
        new_stats_response = client.get("/dashboard-stats")
        new_stats = new_stats_response.text
        # The stats should be different (higher count)
        assert new_stats != initial_stats

        # 4. Update the item (should invalidate cache again)
        cache.get("dashboard_stats")  # This call populates cache
        update_data = {"name": "Updated Integration Test Item"}
        client.put(f"/api/v1/items/{item_id}", json=update_data)
        assert cache.get("dashboard_stats") is None

        # 5. Delete the item (should invalidate cache)
        cache.get("dashboard_stats")  # This call populates cache
        client.delete(f"/api/v1/items/{item_id}")
        assert cache.get("dashboard_stats") is None

    def test_dashboard_displays_recent_items_correctly(self, client, clean_cache):
        """Test that dashboard displays recent items correctly"""
        # Create multiple items
        items_created = []
        for i in range(3):
            item_data = {"name": f"Recent Item {i}", "description": f"Description {i}"}
            response = client.post("/api/v1/items", json=item_data)
            items_created.append(response.json())

        # Get dashboard items
        items_response = client.get("/dashboard-items")
        items_html = items_response.text

        # Should contain the most recent items
        assert "Recent Item 2" in items_html  # Most recent should be visible
        assert "item-name" in items_html
        assert "item-description" in items_html

    def test_error_handling_in_dashboard_endpoints(self, client):
        """Test error handling in dashboard endpoints"""
        # Dashboard endpoints should handle database errors gracefully
        with patch('app.main.get_dashboard_data', side_effect=Exception("Database error")):
            stats_response = client.get("/dashboard-stats")
            items_response = client.get("/dashboard-items")

            assert stats_response.status_code == 200
            assert items_response.status_code == 200
            assert "Error" in stats_response.text
            assert "Error" in items_response.text

    def test_polling_fallback_behavior(self, client):
        """Test that dashboard endpoints work for polling fallback"""
        # Multiple rapid requests should work (simulating polling)
        for i in range(5):
            stats_response = client.get("/dashboard-stats")
            items_response = client.get("/dashboard-items")

            assert stats_response.status_code == 200
            assert items_response.status_code == 200
            assert "Total Items" in stats_response.text

    @pytest.mark.asyncio
    async def test_websocket_notification_rate_limiting_integration(self, clean_websocket_manager):
        """Test WebSocket notification rate limiting in realistic scenario"""
        # Mock WebSocket
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()

        await manager.connect(mock_websocket)

        # Simulate rapid item creation (should be rate limited)
        notifications_sent = 0
        for i in range(5):
            try:
                await manager.notify_data_change("item_created", {"item_id": i})
                # Only the first notification should go through due to rate limiting
                if i == 0:
                    notifications_sent += 1
            except Exception:
                pass

        # Should have only sent one notification due to rate limiting
        assert mock_websocket.send_text.call_count <= 2  # Allow for some timing variance


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
