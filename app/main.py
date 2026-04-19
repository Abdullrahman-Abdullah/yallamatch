import os
import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .database import supabase, cloudinary

# --- الإعدادات الأمنية ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "YALLA_MATCH_SUPER_SECRET_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # أسبوع

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI(title="Yalla Match Ecosystem API")

# --- دوال الأمان والـ JWT ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

# --- 1. نظام الحسابات (Authentication) ---

@app.post("/auth/register")
async def register(
    phone: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    user_type: str = Form(...) # player or owner
):
    hashed_password = pwd_context.hash(password)
    user_entry = {
        "phone_number": phone,
        "password_hash": hashed_password,
        "full_name": name,
        "user_type": user_type
    }
    try:
        res = supabase.table("profiles").insert(user_entry).execute()
        return {"message": "User created successfully", "user": res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Phone number already exists or invalid data")

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    res = supabase.table("profiles").select("*").eq("phone_number", form_data.username).execute()
    if not res.data or not pwd_context.verify(form_data.password, res.data[0]['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    
    access_token = create_access_token(data={"sub": str(res.data[0]['id']), "role": res.data[0]['user_type']})
    return {"access_token": access_token, "token_type": "bearer"}

# --- 2. الملف الشخصي (Profile & My Stuff) ---

@app.get("/profile/me")
async def read_users_me(current_user: str = Depends(get_current_user)):
    user = supabase.table("profiles").select("*").eq("id", current_user).single().execute()
    # جلب التحديات التي أنشأها المستخدم أو شارك فيها
    challenges = supabase.table("challenges").select("*, bookings(booking_date, start_time, stadiums(name))")\
        .or_(f"team_a_id.eq.{current_user},team_b_id.eq.{current_user}").execute()
    
    return {
        "info": user.data,
        "my_active_challenges": challenges.data
    }

# --- 3. إدارة الملاعب (للأصحاب) ---

@app.post("/stadiums/add")
async def add_stadium(
    name: str = Form(...),
    price: int = Form(...),
    address: str = Form(...),
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    # التأكد أن المستخدم هو صاحب ملعب
    user_check = supabase.table("profiles").select("user_type").eq("id", current_user).single().execute()
    if user_check.data['user_type'] != 'owner':
        raise HTTPException(status_code=403, detail="Only owners can add stadiums")

    # رفع الصورة لكلوديناري
    img = cloudinary.uploader.upload(file.file, folder="yalla-match/stadiums")
    
    stadium_entry = {
        "name": name,
        "price_per_hour": price,
        "address": address,
        "owner_id": current_user,
        "image_url": img.get("secure_url")
    }
    res = supabase.table("stadiums").insert(stadium_entry).execute()
    return res.data

# --- 4. الحجوزات والتحديات (للاعبين) ---

@app.get("/explore/stadiums")
async def list_all_stadiums():
    # جلب الملاعب مع متوسط التقييمات (تجريبياً)
    res = supabase.table("stadiums").select("*, ratings(rating)").eq("is_active", True).execute()
    return res.data

@app.post("/bookings/new")
async def book_stadium(
    stadium_id: int,
    date: str,
    time: str,
    is_challenge: bool = False,
    current_user: str = Depends(get_current_user)
):
    # منع الحجز المزدوج
    conflict = supabase.table("bookings").select("*")\
        .eq("stadium_id", stadium_id).eq("booking_date", date).eq("start_time", time).execute()
    if conflict.data:
        raise HTTPException(status_code=400, detail="Time slot already taken")

    booking_data = {
        "stadium_id": stadium_id,
        "user_id": current_user,
        "booking_date": date,
        "start_time": time,
        "is_challenge": is_challenge
    }
    res = supabase.table("bookings").insert(booking_data).execute()
    
    # إذا كان تحدي، ننشئ سجلاً في جدول التحديات
    if is_challenge:
        challenge_data = {
            "booking_id": res.data[0]['id'],
            "team_a_id": current_user,
            "message": "هل أنت مستعد للتحدي؟"
        }
        supabase.table("challenges").insert(challenge_data).execute()

    return {"message": "Booked successfully", "data": res.data}

@app.get("/explore/challenges")
async def list_open_challenges():
    res = supabase.table("challenges").select("*, bookings(*, stadiums(*))").eq("status", "open").execute()
    return res.data

# --- 5. التقييمات ---

@app.post("/stadiums/{stadium_id}/rate")
async def rate_stadium(
    stadium_id: int,
    rating: int,
    comment: str,
    current_user: str = Depends(get_current_user)
):
    res = supabase.table("ratings").insert({
        "stadium_id": stadium_id,
        "user_id": current_user,
        "rating": rating,
        "comment": comment
    }).execute()
    return {"message": "Rating submitted"}