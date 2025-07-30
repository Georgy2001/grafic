from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import jwt
import bcrypt
import os
import uuid
from enum import Enum

# Environment configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# MongoDB setup
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
users_collection = db.users
schedules_collection = db.schedules

app = FastAPI(title="Shift Schedule Manager")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Enums and Models
class UserRole(str, Enum):
    MANAGER = "manager"
    EMPLOYEE = "employee"

class ShiftType(str, Enum):
    DAY = "day"
    NIGHT = "night"
    CUSTOM = "custom"

class User(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    created_at: datetime

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: UserRole = UserRole.EMPLOYEE

class UserLogin(BaseModel):
    email: str
    password: str

class ShiftAssignment(BaseModel):
    employee_id: str
    employee_name: str

class Shift(BaseModel):
    date: str  # YYYY-MM-DD format
    type: ShiftType
    assignments: List[ShiftAssignment]
    hours: Optional[int] = None
    notes: Optional[str] = None

class Schedule(BaseModel):
    id: str
    month: int
    year: int
    shifts: List[Shift]
    created_by: str
    updated_at: datetime

class ScheduleCreate(BaseModel):
    month: int
    year: int
    shifts: List[Shift]

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(token_data: dict = Depends(verify_token)):
    user = users_collection.find_one({"id": token_data.get("sub")})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user.pop("password", None)
    return user

def require_manager(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user

# Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/api/auth/register")
async def register_user(user_data: UserCreate, current_user: dict = Depends(require_manager)):
    # Check if user already exists
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user_id = str(uuid.uuid4())
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hashed_password,
        "role": user_data.role,
        "created_at": datetime.now()
    }
    
    users_collection.insert_one(new_user)
    
    # Return user without password
    new_user.pop("password")
    return {"message": "User created successfully", "user": new_user}

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    user = users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": user["id"], "role": user["role"]})
    user.pop("password", None)
    user.pop("_id", None)  # Remove MongoDB ObjectId
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return current_user

@app.get("/api/users")
async def get_users(current_user: dict = Depends(require_manager)):
    users = list(users_collection.find({}, {"password": 0}))
    return users

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_manager)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = users_collection.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

@app.post("/api/schedules")
async def create_schedule(schedule_data: ScheduleCreate, current_user: dict = Depends(require_manager)):
    # Check if schedule already exists for this month/year
    existing = schedules_collection.find_one({
        "month": schedule_data.month,
        "year": schedule_data.year
    })
    
    schedule_id = str(uuid.uuid4())
    
    schedule = {
        "id": schedule_id,
        "month": schedule_data.month,
        "year": schedule_data.year,
        "shifts": [shift.dict() for shift in schedule_data.shifts],
        "created_by": current_user["id"],
        "updated_at": datetime.now()
    }
    
    if existing:
        schedules_collection.replace_one({"_id": existing["_id"]}, schedule)
        return {"message": "Schedule updated successfully", "schedule": schedule}
    else:
        schedules_collection.insert_one(schedule)
        return {"message": "Schedule created successfully", "schedule": schedule}

@app.get("/api/schedules/{year}/{month}")
async def get_schedule(year: int, month: int, current_user: dict = Depends(get_current_user)):
    schedule = schedules_collection.find_one({"year": year, "month": month})
    if not schedule:
        return {"schedule": None}
    
    schedule.pop("_id", None)
    return {"schedule": schedule}

@app.get("/api/schedules")
async def get_all_schedules(current_user: dict = Depends(get_current_user)):
    schedules = list(schedules_collection.find({}, {"_id": 0}))
    return {"schedules": schedules}

@app.get("/api/my-shifts/{year}/{month}")
async def get_my_shifts(year: int, month: int, current_user: dict = Depends(get_current_user)):
    schedule = schedules_collection.find_one({"year": year, "month": month})
    if not schedule:
        return {"shifts": [], "stats": {"total_shifts": 0, "day_shifts": 0, "night_shifts": 0, "total_hours": 0}}
    
    my_shifts = []
    stats = {"total_shifts": 0, "day_shifts": 0, "night_shifts": 0, "total_hours": 0}
    
    for shift in schedule.get("shifts", []):
        for assignment in shift.get("assignments", []):
            if assignment["employee_id"] == current_user["id"]:
                my_shifts.append(shift)
                stats["total_shifts"] += 1
                if shift["type"] == "day":
                    stats["day_shifts"] += 1
                elif shift["type"] == "night":
                    stats["night_shifts"] += 1
                
                hours = shift.get("hours")
                if hours:
                    stats["total_hours"] += hours
                elif shift["type"] == "day":
                    stats["total_hours"] += 12
                elif shift["type"] == "night":
                    stats["total_hours"] += 12
                break
    
    return {"shifts": my_shifts, "stats": stats}

# Initialize default manager account
@app.on_event("startup")
async def create_default_manager():
    existing_manager = users_collection.find_one({"role": "manager"})
    if not existing_manager:
        manager_id = str(uuid.uuid4())
        default_manager = {
            "id": manager_id,
            "email": "manager@company.com",
            "name": "Default Manager",
            "password": hash_password("manager123"),
            "role": "manager",
            "created_at": datetime.now()
        }
        users_collection.insert_one(default_manager)
        print("Default manager created: manager@company.com / manager123")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)