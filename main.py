from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import heapq

app = FastAPI(
    title="Full-Stack Civic Sense Complaint System",
    description="A system to manage, vote on, and process civic complaints using various DSA concepts."
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models (using Pydantic) ---

class User(BaseModel):
    id: str = ""
    username: str
    password: str # In a real app, this should be a hash

class Complaint(BaseModel):
    id: str = ""
    description: str
    category: str
    location: str
    upvotes: int = 0
    owner_id: str
    status: str = "Pending"
    
class LoginRequest(BaseModel):
    username: str
    password: str

# --- In-Memory Data Storage (Simulating a Database) ---

# DSA Topic 1: Hashing
# Dictionaries (hash maps) are used for O(1) average time complexity for lookups,
# insertions, and deletions of users and complaints by their IDs.
users_db: Dict[str, User] = {}
complaints_db: Dict[str, Complaint] = {}

# DSA Topic 2: Priority Queue (Max-Heap)
# A priority queue is used to keep track of the most urgent complaints.
# We prioritize based on the number of upvotes. Since Python's heapq is a min-heap,
# we store the negative of the upvote count to simulate max-heap behavior.
complaints_pq = []

# DSA Topic 3: Graph (Adjacency List)
# The graph of related categories remains to show structured relationships.
category_graph = {
    "Waste Management": ["Public Health", "Sanitation"],
    "Roads & Traffic": ["Public Safety", "Infrastructure"],
    "Public Health": ["Waste Management", "Water Supply"],
    "Sanitation": ["Waste Management", "Public Health"],
    "Water Supply": ["Public Health", "Infrastructure"],
    "Public Safety": ["Roads & Traffic"],
    "Infrastructure": ["Roads & Traffic", "Water Supply"],
    "Noise Pollution": []
}


# --- API Endpoints ---

# --- User Authentication Endpoints ---

@app.post("/register", response_model=User, status_code=201)
def register_user(user: User):
    """Registers a new user."""
    if any(u.username == user.username for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Username already exists")
    user.id = str(uuid.uuid4())
    users_db[user.id] = user
    return user

@app.post("/login", response_model=User)
def login_user(login_request: LoginRequest):
    """Logs in a user."""
    for user in users_db.values():
        if user.username == login_request.username and user.password == login_request.password:
            return user
    raise HTTPException(status_code=401, detail="Invalid username or password")


# --- Complaint Management Endpoints ---

@app.post("/complaint", response_model=Complaint, status_code=201)
def submit_complaint(complaint: Complaint):
    """Submits a new complaint linked to a user."""
    if complaint.owner_id not in users_db:
        raise HTTPException(status_code=404, detail="Owner user not found")
    complaint.id = str(uuid.uuid4())
    complaints_db[complaint.id] = complaint
    # Add to priority queue
    heapq.heappush(complaints_pq, (-complaint.upvotes, complaint.id))
    return complaint

@app.get("/complaints", response_model=List[Complaint])
def get_all_complaints():
    """
    Retrieves all complaints, sorted by upvotes in descending order.
    DSA Topic 4: Sorting Algorithm
    Python's built-in sort (Timsort) is used here for an efficient O(n log n)
    sorting operation to present the most popular complaints first.
    """
    sorted_complaints = sorted(complaints_db.values(), key=lambda c: c.upvotes, reverse=True)
    return sorted_complaints

@app.post("/complaint/{complaint_id}/upvote", response_model=Complaint)
def upvote_complaint(complaint_id: str):
    """Increments the upvote count for a complaint."""
    if complaint_id not in complaints_db:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    complaint = complaints_db[complaint_id]
    complaint.upvotes += 1
    
    # Re-prioritize in the priority queue. A simple way is to remove and re-add.
    # A more efficient way would be to update in-place, but that's more complex.
    global complaints_pq
    # Create a new list excluding the old entry
    complaints_pq = [item for item in complaints_pq if item[1] != complaint_id]
    heapq.heapify(complaints_pq) # Turn the list back into a heap
    heapq.heappush(complaints_pq, (-complaint.upvotes, complaint.id)) # Add the updated item
    
    return complaint

@app.get("/complaints/most_voted", response_model=Optional[Complaint])
def get_most_voted_complaint():
    """Retrieves the complaint with the most upvotes from the priority queue."""
    while complaints_pq:
        upvotes, complaint_id = complaints_pq[0] # Peek at the top
        if complaint_id in complaints_db and complaints_db[complaint_id].status == "Pending":
            return complaints_db[complaint_id]
        else:
            heapq.heappop(complaints_pq) # Remove if resolved or deleted
    return None

@app.put("/complaint/{complaint_id}/status", response_model=Complaint)
def update_complaint_status(complaint_id: str, status: str):
    """Updates the status of a complaint."""
    if complaint_id not in complaints_db:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaints_db[complaint_id].status = status
    return complaints_db[complaint_id]

# --- Other Endpoints ---
@app.get("/complaints/category_graph", response_model=Dict[str, List[str]])
def get_category_graph():
    """Returns the graph of complaint categories."""
    return category_graph

# To run: uvicorn main:app --reload