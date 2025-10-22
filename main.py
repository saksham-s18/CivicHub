# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
import uuid
import requests
from math import radians, sin, cos, sqrt, atan2

import models, schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Full-Stack Civic Sense Complaint System")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

admin_action_stacks = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Geocoding and Distance Calculation Helpers (Unchanged) ---
def get_coords_for_city(city: str) -> Optional[tuple]:
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            location = data["results"][0]
            return location["latitude"], location["longitude"]
    except requests.exceptions.RequestException as e:
        print(f"Geocoding API error: {e}")
    return None

def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

# --- User Authentication (Unchanged) ---
@app.post("/register", response_model=schemas.User, status_code=201)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
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

# --- Complaint Management Endpoints (Unchanged) ---
@app.post("/complaint", response_model=schemas.Complaint, status_code=201)
def submit_complaint(complaint: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    if not db.query(models.User).filter(models.User.id == complaint.owner_id).first():
        raise HTTPException(status_code=404, detail="Owner user not found")
    
    new_complaint = models.Complaint(**complaint.model_dump())
    
    coords = get_coords_for_city(complaint.location)
    if coords:
        new_complaint.latitude, new_complaint.longitude = coords
        
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

@app.get("/complaints", response_model=List[schemas.Complaint])
def get_all_complaints(db: Session = Depends(get_db)):
    return db.query(models.Complaint).order_by(desc(models.Complaint.upvotes)).all()

# --- Upvote and Most-Voted Endpoints (Unchanged) ---
@app.post("/complaint/{complaint_id}/upvote", response_model=schemas.Complaint)
def upvote_complaint(complaint_id: uuid.UUID, vote_request: schemas.UpvoteRequest, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint: raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.status != "Pending": raise HTTPException(status_code=400, detail="Cannot vote on a resolved complaint")
    if db.query(models.Upvote).filter(models.Upvote.complaint_id == complaint_id, models.Upvote.user_id == vote_request.user_id).first():
        raise HTTPException(status_code=400, detail="You have already voted for this complaint")
    db.add(models.Upvote(user_id=vote_request.user_id, complaint_id=complaint_id))
    complaint.upvotes += 1
    db.commit()
    db.refresh(complaint)
    return complaint

@app.get("/complaints/most_voted", response_model=Optional[schemas.Complaint])
def get_most_voted_complaint(db: Session = Depends(get_db)):
    return db.query(models.Complaint).filter(models.Complaint.status == "Pending").order_by(desc(models.Complaint.upvotes)).first()

# --- Admin Status Update and Undo (Unchanged) ---
@app.put("/admin/complaint/{complaint_id}/status", response_model=schemas.AdminActionResponse)
def update_complaint_status_by_admin(complaint_id: uuid.UUID, admin_id: uuid.UUID, status: str, db: Session = Depends(get_db)):
    admin_user = db.query(models.User).filter(models.User.id == admin_id).first()
    if not admin_user or not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    old_status = complaint.status
    if old_status != status:
        if admin_id not in admin_action_stacks:
            admin_action_stacks[admin_id] = []
        admin_action_stacks[admin_id].append({"complaint_id": complaint_id, "previous_status": old_status})

    complaint.status = status
    db.commit()
    db.refresh(complaint)
    return {"updated_complaint": complaint, "actions_to_undo": len(admin_action_stacks.get(admin_id, []))}

@app.post("/admin/undo", response_model=schemas.AdminActionResponse)
def undo_last_admin_action(request: schemas.UndoRequest, db: Session = Depends(get_db)):
    admin_stack = admin_action_stacks.get(request.admin_id)
    if not admin_stack:
        raise HTTPException(status_code=404, detail="No actions to undo")

    last_action = admin_stack.pop()
    complaint = db.query(models.Complaint).filter(models.Complaint.id == last_action["complaint_id"]).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Original complaint not found")

    complaint.status = last_action["previous_status"]
    db.commit()
    db.refresh(complaint)
    return {"updated_complaint": complaint, "actions_to_undo": len(admin_stack)}

# --- **MODIFIED**: New Global Clustering Endpoint ---
@app.post("/admin/cluster-all", status_code=204)
def create_all_clusters(request: schemas.ClusterRequest, db: Session = Depends(get_db)):
    """
    Finds all interconnected groups of complaints within the given radius
    and assigns them to clusters.
    """
    all_pending = db.query(models.Complaint).filter(
        models.Complaint.status == "Pending",
        models.Complaint.latitude.isnot(None)
    ).all()

    # Reset existing clusters before recalculating
    for complaint in all_pending:
        complaint.cluster_id = None
    db.commit()

    visited = set()
    for complaint in all_pending:
        if complaint.id in visited:
            continue

        # Start a new cluster discovery (BFS)
        parent_complaint = complaint
        current_cluster_members = {parent_complaint}
        queue = [parent_complaint]
        visited.add(parent_complaint.id)

        while queue:
            current = queue.pop(0)
            for other in all_pending:
                if other.id in visited:
                    continue
                
                distance = haversine_distance(
                    current.latitude, current.longitude,
                    other.latitude, other.longitude
                )

                if distance <= request.radius_km:
                    visited.add(other.id)
                    current_cluster_members.add(other)
                    queue.append(other)
        
        # After finding all connected complaints, if the group has more than one member,
        # assign them to a cluster.
        if len(current_cluster_members) > 1:
            for member in current_cluster_members:
                member.cluster_id = parent_complaint.id
    
    db.commit()

# --- Get Clustered Complaints (Unchanged) ---
@app.get("/complaints/clustered", response_model=List[schemas.ClusteredComplaintResponse])
def get_clustered_complaints(db: Session = Depends(get_db)):
    cluster_parents = db.query(models.Complaint).filter(
        models.Complaint.id == models.Complaint.cluster_id
    ).options(joinedload(models.Complaint.cluster_children)).all()

    response = []
    for parent in cluster_parents:
        response.append({
            "parent": parent,
            "children": [child for child in parent.cluster_children if child.id != parent.id]
        })
    return response