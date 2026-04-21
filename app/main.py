import os
import random
import datetime
from typing import List, Optional
from fastapi import FastAPI, Form, HTTPException, Depends, UploadFile, File, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from .database import supabase, cloudinary
from fastapi.middleware.cors import CORSMiddleware

# --- Settings ---
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "YALLA_MATCH_SECRET_2026_KEY")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify")
origins = ["*"]

app = FastAPI(title="Yalla Match Ecosystem")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # السماح بجميع أنواع الطلبات (GET, POST, etc.)
    allow_headers=["*"],  # السماح بجميع الـ Headers (مثل Authorization)
)

# --- Helpers ---
def create_access_token(user_id: str):
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None: raise HTTPException(status_code=401)
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

# --- 1. المرحلة الأولى: التحقق (Auth Phase) ---

@app.post("/auth/send-otp")
async def send_otp(phone: str = Form(...)):
    otp = str(random.randint(100000, 999999))
    expiry = (datetime.datetime.utcnow() + datetime.timedelta(minutes=5)).isoformat()
    
    # حفظ أو تحديث المستخدم برقم الهاتف والـ OTP
    supabase.table("profiles").upsert({
        "phone_number": phone,
        "otp_code": otp,
        "otp_expiry": expiry
    }, on_conflict="phone_number").execute()
    
    return {"message": "OTP Sent", "debug_otp": otp} # في الإنتاج يتم الإرسال عبر SMS

@app.post("/auth/verify")
async def verify_otp(phone: str = Form(...), otp: str = Form(...)):
    res = supabase.table("profiles").select("*").eq("phone_number", phone).single().execute()
    if not res.data or res.data['otp_code'] != otp:
        raise HTTPException(status_code=400, detail="الرمز غير صحيح")
    
    # توليد التوكن وربط المستخدم به فوراً
    token = create_access_token(str(res.data['id']))
    return {
        "access_token": token, 
        "token_type": "bearer",
        "is_onboarded": res.data['is_onboarded'],
        "current_type": res.data['user_type']
    }

# --- 2. المرحلة الثانية: التوجيه (Onboarding Phase) ---

@app.post("/onboard/setup")
async def setup_account(
    name: str = Form(...),
    user_type: str = Form(...), # 'player', 'team', 'owner'
    user_id: str = Depends(get_current_user)
):
    if user_type not in ['player', 'team', 'owner']:
        raise HTTPException(status_code=400, detail="نوع حساب غير صالح")
    
    res = supabase.table("profiles").update({
        "full_name": name,
        "user_type": user_type,
        "is_onboarded": True
    }).eq("id", user_id).execute()
    
    return {"message": f"Welcome aboard as {user_type}!", "user": res.data}

# --- 3. المرحلة الثالثة: الخدمات المتخصصة (Specialized Endpoints) ---

# --- Endpoints للملاعب (للـ Owner فقط) ---
@app.post("/owner/stadiums/add")
async def add_stadium(
    name: str = Form(...), price: int = Form(...), address: str = Form(...),
    file: UploadFile = File(...), user_id: str = Depends(get_current_user)
):
    # حماية: التأكد من أنه Owner
    user = supabase.table("profiles").select("user_type").eq("id", user_id).single().execute()
    if user.data['user_type'] != 'owner':
        raise HTTPException(status_code=403, detail="هذا القسم مخصص لأصحاب الملاعب فقط")

    img = cloudinary.uploader.upload(file.file, folder="stadiums")
    data = {"name": name, "price_per_hour": price, "address": address, "owner_id": user_id, "image_url": img.get("secure_url")}
    res = supabase.table("stadiums").insert(data).execute()
    return res.data

# --- Endpoints للاعبين والفرق (Players/Teams) ---
@app.get("/player/explore")
async def explore_matches():
    # جلب الملاعب والتحديات المفتوحة
    stadiums = supabase.table("stadiums").select("*").execute()
    challenges = supabase.table("challenges").select("*, bookings(*)").eq("status", "open").execute()
    return {"stadiums": stadiums.data, "open_challenges": challenges.data}

@app.post("/player/booking/new")
async def create_booking(stadium_id: int, date: str, time: str, is_challenge: bool = False, user_id: str = Depends(get_current_user)):
    # التحقق من نوع الحساب
    user = supabase.table("profiles").select("user_type").eq("id", user_id).single().execute()
    if user.data['user_type'] not in ['player', 'team']:
        raise HTTPException(status_code=403, detail="الملاعب لا تحجز ملاعب!")

    booking = {"stadium_id": stadium_id, "user_id": user_id, "booking_date": date, "start_time": time, "is_challenge": is_challenge}
    res = supabase.table("bookings").insert(booking).execute()
    return res.data

# --- 4. الملف الشخصي والتقييمات (General) ---

@app.get("/me/profile")
async def get_my_full_profile(user_id: str = Depends(get_current_user)):
    profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    bookings = supabase.table("bookings").select("*, stadiums(name)").eq("user_id", user_id).execute()
    return {"profile": profile.data, "my_bookings": bookings.data}

@app.post("/stadiums/{stadium_id}/rate")
async def rate_stadium(stadium_id: int, rating: int, comment: str, user_id: str = Depends(get_current_user)):
    res = supabase.table("ratings").insert({"stadium_id": stadium_id, "user_id": user_id, "rating": rating, "comment": comment}).execute()
    return {"status": "success"}