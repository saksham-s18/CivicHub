// script.js
const API_URL = 'http://127.0.0.1:8000';
let currentUser = null;

// --- Helper function to manage Undo button visibility ---
function updateUndoButtonVisibility(actions_to_undo) {
    const undoBtn = document.getElementById('undo-btn');
    if (currentUser && currentUser.is_admin && actions_to_undo > 0) {
        undoBtn.classList.remove('hidden');
        undoBtn.textContent = `Undo (${actions_to_undo})`;
    } else {
        undoBtn.classList.add('hidden');
    }
}

// --- SPA Navigation ---
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    
    document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
    const activeLink = document.querySelector(`a[onclick="showPage('${pageId}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

function switchAuthTab(tabId) {
    if (tabId === 'login') {
        document.getElementById('login-form').classList.remove('hidden');
        document.getElementById('register-form').classList.add('hidden');
        document.getElementById('login-tab').classList.add('text-indigo-600', 'border-indigo-600');
        document.getElementById('register-tab').classList.remove('text-indigo-600', 'border-indigo-600');
    } else {
        document.getElementById('register-form').classList.remove('hidden');
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-tab').classList.add('text-indigo-600', 'border-indigo-600');
        document.getElementById('login-tab').classList.remove('text-indigo-600', 'border-indigo-600');
    }
}

// --- UI Rendering ---
function updateUIforAuthState() {
    if (currentUser) {
        document.getElementById('auth-links').classList.add('hidden');
        document.getElementById('user-info').classList.remove('hidden');
        document.getElementById('username-display').textContent = `Welcome, ${currentUser.username}`;
        renderComplaintForm();
    } else {
        document.getElementById('auth-links').classList.remove('hidden');
        document.getElementById('user-info').classList.add('hidden');
        updateUndoButtonVisibility(0); // Hide undo button on logout
        renderLoginPrompt();
    }
}

function renderLoginPrompt() {
      document.getElementById('form-container').innerHTML = `
        <h2 class="text-2xl font-semibold mb-4">Join the Conversation</h2>
        <p>Please <a onclick="showPage('auth')" class="text-indigo-600 font-bold hover:underline cursor-pointer">login or register</a> to submit a new complaint.</p>
      `;
}

function renderComplaintForm() {
    document.getElementById('form-container').innerHTML = `
        <h2 class="text-2xl font-semibold mb-4">File a New Complaint</h2>
        <form id="complaint-form" class="space-y-4">
            <textarea id="description" rows="3" required placeholder="Describe the issue..." class="w-full rounded-md p-2 border"></textarea>
            <input type="text" id="location" required placeholder="Location (e.g., Main Street Park)" class="w-full rounded-md p-2 border">
            <select id="category" required class="w-full rounded-md p-2 border">
                <option>Waste Management</option><option>Roads & Traffic</option><option>Public Health</option>
                <option>Sanitation</option><option>Water Supply</option><option>Public Safety</option>
                <option>Infrastructure</option><option>Pollution</option>
            </select>
            <button type="submit" class="w-full bg-indigo-600 text-white font-semibold py-2 rounded-md hover:bg-indigo-700">Submit Complaint</button>
            <div id="form-message" class="mt-2 text-center"></div>
        </form>
    `;
    document.getElementById('complaint-form').addEventListener('submit', handleComplaintSubmit);
}

// --- API Calls & Event Handlers ---
async function fetchAllData() {
    fetchComplaints();
    fetchMostVoted();
}

// MODIFIED: Function now splits complaints into 'Pending' and 'Resolved'
async function fetchComplaints() {
    const response = await fetch(`${API_URL}/complaints`);
    const complaints = await response.json();

    const pendingList = document.getElementById('pending-complaints-list');
    const resolvedList = document.getElementById('resolved-complaints-list');
    pendingList.innerHTML = '';
    resolvedList.innerHTML = '';

    const pendingComplaints = complaints.filter(c => c.status === 'Pending');
    const resolvedComplaints = complaints.filter(c => c.status !== 'Pending');

    if (pendingComplaints.length === 0) {
        pendingList.innerHTML = '<p class="text-gray-500">No pending issues. Great job, community!</p>';
    } else {
        pendingComplaints.forEach(c => pendingList.appendChild(createComplaintCard(c)));
    }

    if (resolvedComplaints.length === 0) {
        resolvedList.innerHTML = '<p class="text-gray-500">No issues have been resolved yet.</p>';
    } else {
        resolvedComplaints.forEach(c => resolvedList.appendChild(createComplaintCard(c)));
    }
    
    lucide.createIcons(); // Re-render icons
}

// NEW: Helper function to create a complaint card to avoid code duplication
function createComplaintCard(complaint) {
    const card = document.createElement('div');
    const isResolved = complaint.status !== 'Pending';

    card.className = `p-4 border rounded-lg flex justify-between items-center ${isResolved ? 'bg-gray-100 opacity-70' : 'bg-white'}`;
    
    const adminControls = (currentUser && currentUser.is_admin && !isResolved) 
        ? `<div class="mt-2">
             <button onclick="handleResolve('${complaint.id}')" class="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600">Mark Resolved</button>
           </div>` 
        : '';

    const statusColor = isResolved ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800';

    card.innerHTML = `
        <div>
            <p class="font-semibold">${complaint.category}</p>
            <p class="text-sm text-gray-600">${complaint.description}</p>
            <p class="text-xs text-gray-500 mt-1">@ ${complaint.location}</p>
            <span class="inline-block mt-2 px-2 py-1 text-xs rounded-full ${statusColor}">${complaint.status}</span>
            ${adminControls}
        </div>
        <div class="text-center">
            <button onclick="handleUpvote('${complaint.id}')" ${!currentUser || isResolved ? 'disabled' : ''} class="flex items-center space-x-2 bg-gray-200 px-4 py-2 rounded-full hover:bg-indigo-200 disabled:cursor-not-allowed disabled:opacity-50">
                <i data-lucide="arrow-up" class="w-5 h-5"></i>
                <span class="font-bold text-lg">${complaint.upvotes}</span>
            </button>
        </div>
    `;
    return card;
}


async function fetchMostVoted() {
    const response = await fetch(`${API_URL}/complaints/most_voted`);
    const complaint = await response.json();
    const el = document.getElementById('most-voted-complaint');
    if (complaint) {
        el.innerHTML = `<strong>(${complaint.upvotes} votes) ${complaint.category}:</strong> ${complaint.description}`;
    } else {
        el.textContent = 'No pending complaints.';
    }
}

// MODIFIED: Upvote now sends the user ID in the request body
async function handleUpvote(id) {
    if (!currentUser) return;
    
    const response = await fetch(`${API_URL}/complaint/${id}/upvote`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: currentUser.id })
    });

    if (!response.ok) {
        const error = await response.json();
        alert(`Vote failed: ${error.detail}`);
    }

    fetchAllData();
}

// MODIFIED: handleResolve now processes the new API response
async function handleResolve(complaintId) {
    if (!currentUser || !currentUser.is_admin) return;
    const url = `${API_URL}/admin/complaint/${complaintId}/status?admin_id=${currentUser.id}&status=Resolved`;
    const response = await fetch(url, { method: 'PUT' });

    if(response.ok) {
        const data = await response.json();
        updateUndoButtonVisibility(data.actions_to_undo);
        fetchAllData();
    }
}

// NEW: Function to handle the undo button click
async function handleUndo() {
    if (!currentUser || !currentUser.is_admin) return;
    
    const response = await fetch(`${API_URL}/admin/undo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin_id: currentUser.id })
    });

    if (response.ok) {
        const data = await response.json();
        updateUndoButtonVisibility(data.actions_to_undo);
        fetchAllData();
    } else {
        const error = await response.json();
        alert(`Undo failed: ${error.detail}`);
        if (response.status === 404) {
            updateUndoButtonVisibility(0);
        }
    }
}


async function handleComplaintSubmit(e) {
    e.preventDefault();
    const messageDiv = document.getElementById('form-message');
    const complaint = {
        description: document.getElementById('description').value,
        location: document.getElementById('location').value,
        category: document.getElementById('category').value,
        owner_id: currentUser.id
    };
    
    const response = await fetch(`${API_URL}/complaint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(complaint)
    });

    if (response.ok) {
        messageDiv.textContent = 'Submitted!';
        messageDiv.className = 'text-green-600';
        e.target.reset();
        fetchAllData();
    } else {
         messageDiv.textContent = 'Submission failed.';
         messageDiv.className = 'text-red-600';
    }
}

// --- Authentication Logic ---
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const messageDiv = document.getElementById('auth-message');
    
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const user = await response.json();
        if (!response.ok) throw new Error(user.detail);

        currentUser = user;
        localStorage.setItem('currentUser', JSON.stringify(user));
        updateUIforAuthState();
        fetchAllData();
        showPage('home');
    } catch(error) {
        messageDiv.textContent = error.message;
        messageDiv.className = 'text-red-500';
    }
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const messageDiv = document.getElementById('auth-message');

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const user = await response.json();
        if (!response.ok) throw new Error(user.detail);
        
        messageDiv.textContent = 'Registration successful! Please log in.';
        messageDiv.className = 'text-green-500';
        switchAuthTab('login');
        e.target.reset();
    } catch(error) {
        messageDiv.textContent = error.message;
        messageDiv.className = 'text-red-500';
    }
});

function handleLogout() {
    currentUser = null;
    localStorage.removeItem('currentUser');
    updateUIforAuthState();
    fetchAllData(); 
}

// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
    }
    updateUIforAuthState();
    fetchAllData();
    lucide.createIcons();
});