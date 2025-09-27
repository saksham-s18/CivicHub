# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

import models
import schemas
from database import SessionLocal, engine

# This line creates the tables in your database based on your models
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Full-Stack Civic Sense Complaint System",
    description="A system to manage, vote on, and process civic complaints with a persistent database."
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DSA Topic: Stack Implementation ---
# In-memory dictionary to hold a stack of actions for each admin.
# Format: { admin_id: [ { "complaint_id": ..., "previous_status": ... }, ... ] }
admin_action_stacks = {}


# --- Dependency for getting a DB session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---

# --- User Authentication Endpoints ---
@app.post("/register", response_model=schemas.User, status_code=201)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = models.User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.User)
def login_user(login_request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == login_request.username).first()
    if not user or user.password != login_request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return user

# --- Complaint Management Endpoints ---
@app.post("/complaint", response_model=schemas.Complaint, status_code=201)
def submit_complaint(complaint: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    owner = db.query(models.User).filter(models.User.id == complaint.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner user not found")
    
    new_complaint = models.Complaint(**complaint.model_dump())
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

@app.get("/complaints", response_model=List[schemas.Complaint])
def get_all_complaints(db: Session = Depends(get_db)):
    complaints = db.query(models.Complaint).order_by(desc(models.Complaint.upvotes)).all()
    return complaints

@app.post("/complaint/{complaint_id}/upvote", response_model=schemas.Complaint)
def upvote_complaint(complaint_id: uuid.UUID, vote_request: schemas.UpvoteRequest, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.status != "Pending":
        raise HTTPException(status_code=400, detail="Cannot vote on a resolved complaint")

    existing_vote = db.query(models.Upvote).filter(
        models.Upvote.complaint_id == complaint_id,
        models.Upvote.user_id == vote_request.user_id
    ).first()

    if existing_vote:
        raise HTTPException(status_code=400, detail="You have already voted for this complaint")
    
    new_vote = models.Upvote(user_id=vote_request.user_id, complaint_id=complaint_id)
    db.add(new_vote)
    complaint.upvotes += 1
    db.commit()
    db.refresh(complaint)
    return complaint

@app.get("/complaints/most_voted", response_model=Optional[schemas.Complaint])
def get_most_voted_complaint(db: Session = Depends(get_db)):
    most_voted = db.query(models.Complaint).filter(models.Complaint.status == "Pending").order_by(desc(models.Complaint.upvotes)).first()
    return most_voted

# --- Admin Endpoints ---

# MODIFIED: Endpoint now supports the undo stack
@app.put("/admin/complaint/{complaint_id}/status", response_model=schemas.AdminActionResponse)
def update_complaint_status_by_admin(
    complaint_id: uuid.UUID,
    admin_id: uuid.UUID,
    status: str,
    db: Session = Depends(get_db)
):
    admin_user = db.query(models.User).filter(models.User.id == admin_id).first()
    if not admin_user or not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: Requires admin privileges")

    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # --- STACK PUSH LOGIC ---
    old_status = complaint.status
    if old_status != status:
        if admin_id not in admin_action_stacks:
            admin_action_stacks[admin_id] = []
        action_to_undo = {"complaint_id": complaint_id, "previous_status": old_status}
        admin_action_stacks[admin_id].append(action_to_undo)

    complaint.status = status
    db.commit()
    db.refresh(complaint)
    
    actions_to_undo = len(admin_action_stacks.get(admin_id, []))
    
    return {"updated_complaint": complaint, "actions_to_undo": actions_to_undo}

# NEW: Endpoint to handle the undo action
@app.post("/admin/undo", response_model=schemas.AdminActionResponse)
def undo_last_admin_action(request: schemas.UndoRequest, db: Session = Depends(get_db)):
    admin_id = request.admin_id
    admin_user = db.query(models.User).filter(models.User.id == admin_id).first()
    if not admin_user or not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden: Requires admin privileges")

    # --- STACK POP LOGIC ---
    admin_stack = admin_action_stacks.get(admin_id)
    if not admin_stack:
        raise HTTPException(status_code=404, detail="No actions to undo")

    last_action = admin_stack.pop()
    complaint_id = last_action["complaint_id"]
    previous_status = last_action["previous_status"]
    
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Original complaint not found, action removed from undo stack.")

    complaint.status = previous_status
    db.commit()
    db.refresh(complaint)
    
    actions_to_undo = len(admin_stack)
    
    return {"updated_complaint": complaint, "actions_to_undo": actions_to_undo}