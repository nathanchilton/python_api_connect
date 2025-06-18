from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class Item(BaseModel):
    """Item model for API requests/responses"""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ItemCreate(BaseModel):
    """Model for creating new items"""

    name: str
    description: Optional[str] = None


class ItemUpdate(BaseModel):
    """Model for updating items"""

    name: Optional[str] = None
    description: Optional[str] = None
