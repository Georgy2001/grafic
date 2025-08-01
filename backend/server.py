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
stores_collection = db.stores

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

class Store(BaseModel):
    id: str
    name: str
    address: str
    created_at: datetime
    is_active: bool = True

class StoreCreate(BaseModel):
    name: str
    address: str

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class User(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    store_ids: List[str] = []  # Stores this user can access (empty for managers = all stores)
    created_at: datetime

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: UserRole = UserRole.EMPLOYEE
    store_ids: List[str] = []  # For employees, specify which stores they work at

class UserLogin(BaseModel):
    email: str
    password: str

class ShiftAssignment(BaseModel):
    employee_id: str
    employee_name: str
    earnings: Optional[float] = None  # Заработок за смену в рублях
    earnings_set_at: Optional[datetime] = None  # Когда была установлена ставка
    earnings_set_by: Optional[str] = None  # Кто установил ставку (employee_id или "auto")
    can_edit_earnings: Optional[bool] = True  # Может ли сотрудник редактировать ставку

class Shift(BaseModel):
    type: ShiftType
    assignments: List[ShiftAssignment]
    hours: Optional[int] = None
    notes: Optional[str] = None

class DaySchedule(BaseModel):
    date: str  # YYYY-MM-DD format
    day_shift: Optional[Shift] = None
    night_shift: Optional[Shift] = None
    custom_shifts: List[Shift] = []

class Schedule(BaseModel):
    id: str
    store_id: str  # Link schedule to specific store
    month: int
    year: int
    days: List[DaySchedule]
    created_by: str
    updated_at: datetime

class ScheduleCreate(BaseModel):
    store_id: str  # Required field for creating schedule
    month: int
    year: int
    days: List[DaySchedule]

class EarningsUpdate(BaseModel):
    earnings: float
    
class EarningsResponse(BaseModel):
    success: bool
    message: str
    can_edit: bool

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
    user.pop("_id", None)  # Remove MongoDB ObjectId
    return user

def require_manager(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user

def can_edit_earnings(shift_date: str, current_user: dict) -> bool:
    """Проверяет, может ли пользователь редактировать ставку за смену"""
    # Менеджеры всегда могут редактировать
    if current_user["role"] == UserRole.MANAGER:
        return True
    
    # Сотрудники могут редактировать только в течение 12 часов после смены
    try:
        shift_datetime = datetime.strptime(shift_date, "%Y-%m-%d")
        # Предполагаем, что смена заканчивается в 23:59 того же дня
        shift_end = shift_datetime.replace(hour=23, minute=59, second=59)
        twelve_hours_later = shift_end + timedelta(hours=12)
        
        return datetime.now() <= twelve_hours_later
    except:
        return False

def set_default_earnings_if_needed():
    """Устанавливает ставки по умолчанию (2000₽) для смен старше 12 часов без ставки"""
    try:
        # Найти все расписания
        schedules = schedules_collection.find({})
        
        for schedule in schedules:
            updated = False
            
            for day in schedule.get("days", []):
                shift_date = day.get("date")
                if not shift_date:
                    continue
                
                # Проверить все типы смен в дне
                for shift_type in ["day_shift", "night_shift"]:
                    shift = day.get(shift_type)
                    if not shift:
                        continue
                    
                    for assignment in shift.get("assignments", []):
                        # Если ставка не установлена и прошло более 12 часов
                        if (assignment.get("earnings") is None and 
                            not can_edit_earnings(shift_date, {"role": "employee"})):
                            
                            assignment["earnings"] = 2000.0
                            assignment["earnings_set_at"] = datetime.now()
                            assignment["earnings_set_by"] = "auto"
                            assignment["can_edit_earnings"] = False
                            updated = True
                
                # Проверить custom_shifts
                for shift in day.get("custom_shifts", []):
                    for assignment in shift.get("assignments", []):
                        if (assignment.get("earnings") is None and 
                            not can_edit_earnings(shift_date, {"role": "employee"})):
                            
                            assignment["earnings"] = 2000.0
                            assignment["earnings_set_at"] = datetime.now()
                            assignment["earnings_set_by"] = "auto"
                            assignment["can_edit_earnings"] = False
                            updated = True
            
            # Обновить расписание если были изменения
            if updated:
                schedules_collection.update_one(
                    {"id": schedule["id"]},
                    {"$set": {"days": schedule["days"], "updated_at": datetime.now()}}
                )
    
    except Exception as e:
        print(f"Error setting default earnings: {e}")

# Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

# Store Management Routes
@app.post("/api/stores")
async def create_store(store_data: StoreCreate, current_user: dict = Depends(require_manager)):
    """Create a new store"""
    store_id = str(uuid.uuid4())
    
    new_store = {
        "id": store_id,
        "name": store_data.name,
        "address": store_data.address,
        "created_at": datetime.now(),
        "is_active": True
    }
    
    stores_collection.insert_one(new_store)
    new_store.pop("_id", None)
    return {"message": "Store created successfully", "store": new_store}

@app.get("/api/stores")
async def get_stores(current_user: dict = Depends(get_current_user)):
    """Get all stores or user's assigned stores"""
    if current_user["role"] == UserRole.MANAGER:
        # Managers can see all stores
        stores = list(stores_collection.find({"is_active": True}, {"_id": 0}))
    else:
        # Employees see only their assigned stores
        user_store_ids = current_user.get("store_ids", [])
        if user_store_ids:
            stores = list(stores_collection.find({
                "id": {"$in": user_store_ids}, 
                "is_active": True
            }, {"_id": 0}))
        else:
            stores = []
    
    return stores

@app.get("/api/stores/{store_id}")
async def get_store(store_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific store details"""
    # Check access permissions
    if current_user["role"] != UserRole.MANAGER:
        user_store_ids = current_user.get("store_ids", [])
        if store_id not in user_store_ids:
            raise HTTPException(status_code=403, detail="Access denied to this store")
    
    store = stores_collection.find_one({"id": store_id}, {"_id": 0})
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    return store

@app.put("/api/stores/{store_id}")
async def update_store(store_id: str, store_data: StoreUpdate, current_user: dict = Depends(require_manager)):
    """Update store information"""
    update_data = {k: v for k, v in store_data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.now()
    
    result = stores_collection.update_one({"id": store_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Store not found")
    
    return {"message": "Store updated successfully"}

@app.delete("/api/stores/{store_id}")
async def delete_store(store_id: str, current_user: dict = Depends(require_manager)):
    """Soft delete store (set is_active to False)"""
    result = stores_collection.update_one(
        {"id": store_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.now()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Store not found")
    
    return {"message": "Store deleted successfully"}

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
        "store_ids": user_data.store_ids,
        "created_at": datetime.now()
    }
    
    users_collection.insert_one(new_user)
    
    # Return user without password and _id
    new_user.pop("password", None)
    new_user.pop("_id", None)
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
    users = list(users_collection.find({}, {"password": 0, "_id": 0}))
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
    # Validate that store exists
    store = stores_collection.find_one({"id": schedule_data.store_id, "is_active": True})
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Check if schedule already exists for this month/year/store
    existing = schedules_collection.find_one({
        "store_id": schedule_data.store_id,
        "month": schedule_data.month,
        "year": schedule_data.year
    })
    
    schedule_id = str(uuid.uuid4())
    
    schedule = {
        "id": schedule_id,
        "store_id": schedule_data.store_id,
        "month": schedule_data.month,
        "year": schedule_data.year,
        "days": [day.dict() for day in schedule_data.days],
        "created_by": current_user["id"],
        "updated_at": datetime.now()
    }
    
    if existing:
        schedules_collection.replace_one({"_id": existing["_id"]}, schedule)
        # Return a clean copy without MongoDB _id
        clean_schedule = schedule.copy()
        clean_schedule.pop("_id", None)
        return {"message": "Schedule updated successfully", "schedule": clean_schedule}
    else:
        schedules_collection.insert_one(schedule)
        # Return a clean copy without MongoDB _id
        clean_schedule = schedule.copy()
        clean_schedule.pop("_id", None)
        return {"message": "Schedule created successfully", "schedule": clean_schedule}

@app.get("/api/schedules/{store_id}/{year}/{month}")
async def get_schedule(store_id: str, year: int, month: int, current_user: dict = Depends(get_current_user)):
    # Check access permissions
    if current_user["role"] != UserRole.MANAGER:
        user_store_ids = current_user.get("store_ids", [])
        if store_id not in user_store_ids:
            raise HTTPException(status_code=403, detail="Access denied to this store")
    
    schedule = schedules_collection.find_one({
        "store_id": store_id,
        "year": year, 
        "month": month
    })
    if not schedule:
        return {"schedule": None}
    
    schedule.pop("_id", None)
    return {"schedule": schedule}

@app.get("/api/schedules")
async def get_all_schedules(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == UserRole.MANAGER:
        # Managers can see all schedules
        schedules = list(schedules_collection.find({}, {"_id": 0}))
    else:
        # Employees see only schedules from their assigned stores
        user_store_ids = current_user.get("store_ids", [])
        if user_store_ids:
            schedules = list(schedules_collection.find({
                "store_id": {"$in": user_store_ids}
            }, {"_id": 0}))
        else:
            schedules = []
    
    return {"schedules": schedules}

@app.get("/api/my-shifts/{store_id}/{year}/{month}")
async def get_my_shifts(store_id: str, year: int, month: int, current_user: dict = Depends(get_current_user)):
    # Установить ставки по умолчанию для просроченных смен
    set_default_earnings_if_needed()
    
    # Check access permissions
    if current_user["role"] != UserRole.MANAGER:
        user_store_ids = current_user.get("store_ids", [])
        if store_id not in user_store_ids:
            raise HTTPException(status_code=403, detail="Access denied to this store")
    
    schedule = schedules_collection.find_one({
        "store_id": store_id,
        "year": year, 
        "month": month
    })
    if not schedule:
        return {"shifts": [], "stats": {"total_shifts": 0, "day_shifts": 0, "night_shifts": 0, "total_hours": 0, "total_earnings": 0}}
    
    my_shifts = []
    stats = {"total_shifts": 0, "day_shifts": 0, "night_shifts": 0, "total_hours": 0, "total_earnings": 0}
    
    for day_schedule in schedule.get("days", []):
        date = day_schedule["date"]
        
        # Check day shift
        if day_schedule.get("day_shift"):
            day_shift = day_schedule["day_shift"]
            for assignment in day_shift.get("assignments", []):
                if assignment["employee_id"] == current_user["id"]:
                    earnings = assignment.get("earnings", None)
                    can_edit = assignment.get("can_edit_earnings", True)
                    if can_edit and earnings is None:
                        can_edit = can_edit_earnings(date, current_user)
                    
                    my_shifts.append({
                        "date": date,
                        "type": "day",
                        "shift_data": day_shift,
                        "earnings": earnings,
                        "can_edit_earnings": can_edit,
                        "assignment_index": day_shift["assignments"].index(assignment)
                    })
                    stats["total_shifts"] += 1
                    stats["day_shifts"] += 1
                    hours = day_shift.get("hours", 12)
                    stats["total_hours"] += hours
                    if earnings:
                        stats["total_earnings"] += earnings
                    break
        
        # Check night shift
        if day_schedule.get("night_shift"):
            night_shift = day_schedule["night_shift"]
            for assignment in night_shift.get("assignments", []):
                if assignment["employee_id"] == current_user["id"]:
                    earnings = assignment.get("earnings", None)
                    can_edit = assignment.get("can_edit_earnings", True)
                    if can_edit and earnings is None:
                        can_edit = can_edit_earnings(date, current_user)
                    
                    my_shifts.append({
                        "date": date,
                        "type": "night",
                        "shift_data": night_shift,
                        "earnings": earnings,
                        "can_edit_earnings": can_edit,
                        "assignment_index": night_shift["assignments"].index(assignment)
                    })
                    stats["total_shifts"] += 1
                    stats["night_shifts"] += 1
                    hours = night_shift.get("hours", 12)
                    stats["total_hours"] += hours
                    if earnings:
                        stats["total_earnings"] += earnings
                    break
        
        # Check custom shifts
        for custom_shift in day_schedule.get("custom_shifts", []):
            for assignment in custom_shift.get("assignments", []):
                if assignment["employee_id"] == current_user["id"]:
                    earnings = assignment.get("earnings", None)
                    can_edit = assignment.get("can_edit_earnings", True)
                    if can_edit and earnings is None:
                        can_edit = can_edit_earnings(date, current_user)
                    
                    my_shifts.append({
                        "date": date,
                        "type": "custom",
                        "shift_data": custom_shift,
                        "earnings": earnings,
                        "can_edit_earnings": can_edit,
                        "assignment_index": custom_shift["assignments"].index(assignment)
                    })
                    stats["total_shifts"] += 1
                    hours = custom_shift.get("hours", 8)
                    stats["total_hours"] += hours
                    if earnings:
                        stats["total_earnings"] += earnings
                    break
    
    return {"shifts": my_shifts, "stats": stats}

@app.put("/api/shift-earnings/{store_id}/{year}/{month}/{date}/{shift_type}")
async def update_shift_earnings(
    store_id: str, 
    year: int, 
    month: int, 
    date: str, 
    shift_type: str,
    earnings_data: EarningsUpdate,
    assignment_index: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Обновить ставку за смену"""
    # Проверить доступ
    if current_user["role"] != UserRole.MANAGER:
        user_store_ids = current_user.get("store_ids", [])
        if store_id not in user_store_ids:
            raise HTTPException(status_code=403, detail="Access denied to this store")
        
        # Проверить временные ограничения для сотрудников
        if not can_edit_earnings(date, current_user):
            return EarningsResponse(
                success=False, 
                message="Время редактирования ставки истекло. Обратитесь к менеджеру.",
                can_edit=False
            )
    
    # Найти расписание
    schedule = schedules_collection.find_one({
        "store_id": store_id,
        "year": year,
        "month": month
    })
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Найти день и смену
    day_found = False
    shift_found = False
    
    for day_schedule in schedule.get("days", []):
        if day_schedule["date"] == date:
            day_found = True
            
            # Определить тип смены и обновить
            if shift_type == "day" and day_schedule.get("day_shift"):
                shift = day_schedule["day_shift"]
                if len(shift["assignments"]) > assignment_index:
                    assignment = shift["assignments"][assignment_index]
                    if assignment["employee_id"] == current_user["id"] or current_user["role"] == UserRole.MANAGER:
                        assignment["earnings"] = earnings_data.earnings
                        assignment["earnings_set_at"] = datetime.now()
                        assignment["earnings_set_by"] = current_user["id"]
                        assignment["can_edit_earnings"] = can_edit_earnings(date, current_user)
                        shift_found = True
                        
            elif shift_type == "night" and day_schedule.get("night_shift"):
                shift = day_schedule["night_shift"]
                if len(shift["assignments"]) > assignment_index:
                    assignment = shift["assignments"][assignment_index]
                    if assignment["employee_id"] == current_user["id"] or current_user["role"] == UserRole.MANAGER:
                        assignment["earnings"] = earnings_data.earnings
                        assignment["earnings_set_at"] = datetime.now()
                        assignment["earnings_set_by"] = current_user["id"]
                        assignment["can_edit_earnings"] = can_edit_earnings(date, current_user)
                        shift_found = True
                        
            elif shift_type == "custom":
                custom_shifts = day_schedule.get("custom_shifts", [])
                for custom_shift in custom_shifts:
                    if len(custom_shift["assignments"]) > assignment_index:
                        assignment = custom_shift["assignments"][assignment_index]
                        if assignment["employee_id"] == current_user["id"] or current_user["role"] == UserRole.MANAGER:
                            assignment["earnings"] = earnings_data.earnings
                            assignment["earnings_set_at"] = datetime.now()
                            assignment["earnings_set_by"] = current_user["id"]
                            assignment["can_edit_earnings"] = can_edit_earnings(date, current_user)
                            shift_found = True
                            break
            break
    
    if not day_found:
        raise HTTPException(status_code=404, detail="Date not found in schedule")
    
    if not shift_found:
        raise HTTPException(status_code=404, detail="Shift assignment not found")
    
    # Обновить расписание в базе данных
    schedules_collection.update_one(
        {"id": schedule["id"]},
        {"$set": {"days": schedule["days"], "updated_at": datetime.now()}}
    )
    
    can_edit = can_edit_earnings(date, current_user)
    return EarningsResponse(
        success=True, 
        message="Ставка успешно обновлена",
        can_edit=can_edit
    )

@app.get("/api/earnings-history/{store_id}")
async def get_earnings_history(store_id: str, current_user: dict = Depends(get_current_user)):
    """Получить историю заработка по месяцам"""
    # Проверить доступ
    if current_user["role"] != UserRole.MANAGER:
        user_store_ids = current_user.get("store_ids", [])
        if store_id not in user_store_ids:
            raise HTTPException(status_code=403, detail="Access denied to this store")
    
    # Получить все расписания для данного магазина
    schedules = schedules_collection.find({"store_id": store_id})
    
    history = []
    
    for schedule in schedules:
        month_earnings = 0
        month_shifts = 0
        
        for day_schedule in schedule.get("days", []):
            # Проверить все смены
            for shift_type in ["day_shift", "night_shift"]:
                shift = day_schedule.get(shift_type)
                if shift:
                    for assignment in shift.get("assignments", []):
                        if assignment["employee_id"] == current_user["id"]:
                            earnings = assignment.get("earnings", 0)
                            if earnings:
                                month_earnings += earnings
                                month_shifts += 1
            
            # Проверить custom_shifts
            for custom_shift in day_schedule.get("custom_shifts", []):
                for assignment in custom_shift.get("assignments", []):
                    if assignment["employee_id"] == current_user["id"]:
                        earnings = assignment.get("earnings", 0)
                        if earnings:
                            month_earnings += earnings
                            month_shifts += 1
        
        if month_shifts > 0:
            history.append({
                "year": schedule["year"],
                "month": schedule["month"],
                "total_earnings": month_earnings,
                "total_shifts": month_shifts,
                "average_per_shift": round(month_earnings / month_shifts, 2) if month_shifts > 0 else 0
            })
    
    # Сортировать по дате (новые сначала)
    history.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
    
    return {"history": history}

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
            "store_ids": [],  # Empty means access to all stores
            "created_at": datetime.now()
        }
        users_collection.insert_one(default_manager)
        print("Default manager created: manager@company.com / manager123")
    
    # Create default store if none exists
    existing_store = stores_collection.find_one({"is_active": True})
    if not existing_store:
        store_id = str(uuid.uuid4())
        default_store = {
            "id": store_id,
            "name": "Основная точка продаж",
            "address": "ул. Примерная, 1",
            "created_at": datetime.now(),
            "is_active": True
        }
        stores_collection.insert_one(default_store)
        print(f"Default store created: {default_store['name']}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)