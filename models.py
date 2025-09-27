# models.py
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from database import Base

# --- CHANGE: Added a new association table for upvotes ---
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

    complaints = relationship("Complaint", back_populates="owner")

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(String, index=True)
    category = Column(String, index=True)
    location = Column(String)
    upvotes = Column(Integer, default=0)
    status = Column(String, default="Pending") # Statuses: Pending, Resolved
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    owner = relationship("User", back_populates="complaints")