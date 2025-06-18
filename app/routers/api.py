from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from app.models.database import execute_query, execute_insert, execute_update
from app.models.item import Item, ItemCreate, ItemUpdate
from app.utils.cache import cache
from app.utils.websocket_manager import manager
from app.utils.db_persistence import db_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/items", response_model=List[Item])
def get_all_items():
    """Get all items"""
    query = "SELECT * FROM items ORDER BY created_at DESC"
    results = execute_query(query)
    return results


@router.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    """Get a specific item by ID"""
    query = "SELECT * FROM items WHERE id = ?"
    results = execute_query(query, (item_id,))

    if not results:
        raise HTTPException(status_code=404, detail="Item not found")

    return results[0]


@router.post("/items", response_model=Item)
async def create_item(item: ItemCreate):
    """Create a new item"""
    query = "INSERT INTO items (name, description) VALUES (?, ?)"
    item_id = execute_insert(query, (item.name, item.description))

    if item_id is None:
        raise HTTPException(status_code=500, detail="Failed to create item")

    # Invalidate cache when new item is created
    cache.invalidate("dashboard_stats")
    cache.invalidate("dashboard_items")

    # Send WebSocket notification directly
    await manager.notify_data_change("item_created", {"item_id": item_id, "name": item.name})

    # Mark data change and backup if needed
    db_manager.mark_data_change()
    db_manager.backup_database()

    # Return the created item
    return get_item(item_id)


@router.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    """Update an existing item"""
    # Check if item exists
    existing_item = execute_query("SELECT * FROM items WHERE id = ?", (item_id,))
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Build dynamic update query
    update_fields = []
    params = []

    if item.name is not None:
        update_fields.append("name = ?")
        params.append(item.name)

    if item.description is not None:
        update_fields.append("description = ?")
        params.append(item.description)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Add the ID parameter for WHERE clause
    params.append(item_id)

    query = f"UPDATE items SET {', '.join(update_fields)} WHERE id = ?"
    affected_rows = execute_update(query, tuple(params))

    if affected_rows == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    # Invalidate cache when item is updated
    cache.invalidate("dashboard_stats")
    cache.invalidate("dashboard_items")

    # Send WebSocket notification directly
    await manager.notify_data_change("item_updated", {"item_id": item_id})

    # Mark data change and backup if needed
    db_manager.mark_data_change()
    db_manager.backup_database()

    # Return the updated item
    return get_item(item_id)


@router.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item"""
    query = "DELETE FROM items WHERE id = ?"
    affected_rows = execute_update(query, (item_id,))

    if affected_rows == 0:
        raise HTTPException(status_code=404, detail="Item not found")

    # Invalidate cache when item is deleted
    cache.invalidate("dashboard_stats")
    cache.invalidate("dashboard_items")

    # Send WebSocket notification directly
    await manager.notify_data_change("item_deleted", {"item_id": item_id})

    # Mark data change and backup if needed
    db_manager.mark_data_change()
    db_manager.backup_database()

    return {"detail": "Item deleted successfully"}
