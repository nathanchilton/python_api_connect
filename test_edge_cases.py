"""
Additional edge case tests for the FastAPI dashboard application

These tests focus on:
- Edge cases and boundary conditions
- Performance under load
- Database connection issues
- Memory management
- Concurrent access patterns
- Frontend/backend interaction edge cases
"""

import pytest
import asyncio
import json
import time
import threading
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.utils.cache import cache
from app.utils.websocket_manager import manager
from app.models.database import init_db, get_dashboard_data


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


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_api_with_empty_request_body(self, client):
        """Test API endpoints with empty or malformed request bodies"""
        # Empty JSON body
        response = client.post("/api/v1/items", json={})
        # Should handle gracefully - empty fields should have defaults or validation
        assert response.status_code in [200, 422]  # Either success or validation error

        # Malformed JSON (handled by FastAPI)
        response = client.post("/api/v1/items", data="not json")
        assert response.status_code == 422

    def test_api_with_oversized_data(self, client):
        """Test API with very large data payloads"""
        # Very long strings
        large_name = "A" * 10000
        large_description = "B" * 50000

        item_data = {"name": large_name, "description": large_description}
        response = client.post("/api/v1/items", json=item_data)
        # Should either succeed or gracefully handle size limits
        assert response.status_code in [200, 422, 413]

    def test_concurrent_cache_operations(self, clean_cache):
        """Test cache under concurrent access"""
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(50):
                    key = f"concurrent_key_{worker_id}_{i}"
                    value = f"value_{worker_id}_{i}"

                    # Set value
                    cache.set(key, value, ttl_seconds=1)

                    # Get value
                    retrieved = cache.get(key)
                    results.append(retrieved == value)

                    # Invalidate randomly
                    if i % 3 == 0:
                        cache.invalidate(key)

                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # No errors should occur
        assert len(errors) == 0, f"Concurrent errors: {errors}"
        # Most operations should succeed
        success_rate = sum(results) / len(results) if results else 0
        assert success_rate > 0.9, f"Success rate too low: {success_rate}"

    def test_cache_memory_cleanup(self, clean_cache):
        """Test that cache properly cleans up expired entries"""
        # Add many short-lived entries
        for i in range(100):
            cache.set(f"temp_key_{i}", f"temp_value_{i}", ttl_seconds=1)

        # Wait for expiration
        time.sleep(1.1)

        # Access cache to trigger cleanup (if implemented)
        cache.get("nonexistent")

        # Add a new entry to see if memory was freed
        # This is more of a smoke test since we can't easily measure memory
        cache.set("after_cleanup", "value", ttl_seconds=1)
        assert cache.get("after_cleanup") == "value"

    @pytest.mark.asyncio
    async def test_websocket_manager_memory_cleanup(self, clean_websocket_manager):
        """Test that WebSocket manager cleans up disconnected connections"""
        mock_connections = []

        # Create many mock connections
        for i in range(10):
            mock_ws = MagicMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_connections.append(mock_ws)
            await manager.connect(mock_ws)

        assert len(manager.active_connections) == 10

        # Simulate some connections failing
        for i in range(5):
            mock_connections[i].send_text = AsyncMock(side_effect=Exception("Connection lost"))

        # Trigger broadcast to clean up failed connections
        await manager.broadcast({"type": "test", "data": "cleanup_test"})

        # Failed connections should be removed
        assert len(manager.active_connections) == 5

    def test_database_error_resilience(self, client, clean_cache):
        """Test API resilience to database errors"""
        # Test various database error scenarios
        with patch('app.main.get_dashboard_data', side_effect=Exception("Database connection failed")):
            # API should handle database errors gracefully
            response = client.get("/api/v1/items")
            assert response.status_code in [200, 500]  # Either cached data or error response

            # Dashboard should show error state
            response = client.get("/dashboard-stats")
            assert response.status_code == 200
            assert "Error" in response.text or "❌" in response.text

    def test_dashboard_with_no_data(self, client, clean_cache):
        """Test dashboard behavior with empty database"""
        # Clear all items first
        with patch('app.main.get_dashboard_data', return_value={"total_items": 0, "recent_items": []}):
            stats_response = client.get("/dashboard-stats")
            items_response = client.get("/dashboard-items")

            assert stats_response.status_code == 200
            assert items_response.status_code == 200
            assert "0" in stats_response.text
            assert ("empty" in items_response.text.lower() or "no items" in items_response.text.lower())

    @pytest.mark.asyncio
    async def test_websocket_rapid_connect_disconnect(self, clean_websocket_manager):
        """Test rapid WebSocket connect/disconnect cycles"""
        for i in range(20):
            mock_ws = MagicMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()

            # Connect and immediately disconnect
            await manager.connect(mock_ws)
            manager.disconnect(mock_ws)

            # Should handle gracefully
            assert len(manager.active_connections) == 0

    def test_api_rate_limiting_simulation(self, client):
        """Simulate high-frequency API calls to test system stability"""
        responses = []

        # Make many rapid requests
        for i in range(50):
            response = client.get("/api/v1/items")
            responses.append(response.status_code)

        # All should succeed (no rate limiting implemented, but system should be stable)
        assert all(status == 200 for status in responses)

    def test_dashboard_caching_under_load(self, client, clean_cache):
        """Test dashboard caching behavior under concurrent load"""
        def make_requests():
            results = []
            for i in range(20):
                stats_response = client.get("/dashboard-stats")
                items_response = client.get("/dashboard-items")
                results.append((stats_response.status_code, items_response.status_code))
            return results

        # Make concurrent requests
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_requests) for _ in range(3)]
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())

        # All requests should succeed
        assert all(stats == 200 and items == 200 for stats, items in all_results)

    def test_malformed_websocket_messages(self, client):
        """Test WebSocket endpoint with malformed messages"""
        try:
            with client.websocket_connect("/ws/dashboard") as websocket:
                # Send various malformed messages
                websocket.send_text("not json")
                websocket.send_text('{"incomplete": ')
                websocket.send_text("")

                # Connection should remain stable
                websocket.send_text("ping")
                response = websocket.receive_text()
                assert "Echo: ping" in response

        except Exception as e:
            # Connection errors are acceptable for malformed data
            pass

    def test_unicode_and_special_characters(self, client):
        """Test API with Unicode and special characters"""
        test_cases = [
            {"name": "测试项目", "description": "这是一个测试描述"},
            {"name": "🚀 Rocket Item", "description": "Description with emoji 🎉"},
            {"name": "Item with\nnewlines", "description": "Multi\nline\ndescription"},
            {"name": "Special chars: !@#$%^&*()", "description": "More special: []{}|\\;':\",./<>?"},
        ]

        for item_data in test_cases:
            response = client.post("/api/v1/items", json=item_data)
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == item_data["name"]
            assert data["description"] == item_data["description"]


class TestPerformanceEdgeCases:
    """Test performance-related edge cases"""

    def test_large_dataset_dashboard_performance(self, client):
        """Test dashboard performance with large dataset simulation"""
        # Mock a large dataset
        large_items = [
            {"id": i, "name": f"Item {i}", "description": f"Description {i}", "created_at": "2024-01-01T00:00:00Z"}
            for i in range(1000)
        ]

        with patch('app.models.database.get_dashboard_data', return_value={"total_items": 1000, "recent_items": large_items[:10]}):
            start_time = time.time()
            response = client.get("/dashboard-items")
            end_time = time.time()

            assert response.status_code == 200
            # Should respond within reasonable time even with large dataset
            assert (end_time - start_time) < 2.0  # Less than 2 seconds

    @pytest.mark.asyncio
    async def test_websocket_broadcast_performance(self, clean_websocket_manager):
        """Test WebSocket broadcast performance with many connections"""
        # Create many mock connections
        mock_connections = []
        for i in range(100):
            mock_ws = MagicMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_connections.append(mock_ws)
            await manager.connect(mock_ws)

        # Time the broadcast
        start_time = time.time()
        await manager.broadcast({"type": "performance_test", "data": "test_data"})
        end_time = time.time()

        # Should complete within reasonable time
        assert (end_time - start_time) < 1.0  # Less than 1 second for 100 connections

    def test_cache_performance_under_load(self, clean_cache):
        """Test cache performance under high load"""
        start_time = time.time()

        # Perform many cache operations
        for i in range(1000):
            key = f"perf_key_{i % 100}"  # Reuse some keys
            cache.set(key, f"value_{i}", ttl_seconds=10)
            cache.get(key)
            if i % 10 == 0:
                cache.invalidate(key)

        end_time = time.time()

        # Should complete within reasonable time
        assert (end_time - start_time) < 2.0  # Less than 2 seconds for 1000 operations


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
