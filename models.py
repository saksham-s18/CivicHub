# models.py
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from database import Base

class Upvote(Base):
    __tablename__ = 'upvotes'
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey('complaints.id'), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    is_admin = Column(Boolean, default=False)
    complaints = relationship("Complaint", back_populates="owner", foreign_keys="[Complaint.owner_id]")


class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(String, index=True)
    category = Column(String, index=True)
    location = Column(String)
    upvotes = Column(Integer, default=0)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # --- NEW: Fields for Geolocation and Clustering ---
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Self-referencing FK for clustering. This complaint belongs to the cluster identified by cluster_id.
    cluster_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=True)
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    owner = relationship("User", back_populates="complaints", foreign_keys=[owner_id])
    
    # Defines the one-to-many relationship for a cluster parent to its children
    cluster_children = relationship("Complaint", back_populates="cluster_parent", cascade="all, delete-orphan")
    cluster_parent = relationship("Complaint", back_populates="cluster_children", remote_side=[id])