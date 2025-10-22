# schemas.py
import uuid
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Complaint Schemas ---
class ComplaintBase(BaseModel):
    description: str
    category: str
    location: str

class ComplaintCreate(ComplaintBase):
    owner_id: uuid.UUID

class Complaint(ComplaintBase):
    id: uuid.UUID
    upvotes: int
    status: str
    owner_id: uuid.UUID
    created_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cluster_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True

# --- User Schemas ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: uuid.UUID
    is_admin: bool
    complaints: List[Complaint] = []

    class Config:
        from_attributes = True

# --- Other Request/Response Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class UpvoteRequest(BaseModel):
    user_id: uuid.UUID

class UndoRequest(BaseModel):
    admin_id: uuid.UUID

class AdminActionResponse(BaseModel):
    updated_complaint: Complaint
    actions_to_undo: int

# --- NEW: Schemas for Clustering Feature ---
class ClusterRequest(BaseModel):
    radius_km: float

class ClusteredComplaintResponse(BaseModel):
    parent: Complaint
    children: List[Complaint]