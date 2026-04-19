from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from .database import supabase, cloudinary
from typing import Optional
import datetime

app = FastAPI(title="Yalla Match API")

@app.get("/")
def health_check():
    return {"status": "Yalla Match API is Live", "time": datetime.datetime.now()}

# --- قسم مالك الملعب (Type A) ---

@app.post("/stadiums/register")
async def register_stadium(
    name: str = Form(...),
    price: int = Form(...),
    address: str = Form(...),
    owner_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # 1. رفع الصورة
        img_result = cloudinary.uploader.upload(file.file, folder="stadiums")
        img_url = img_result.get("secure_url")

        # 2. الحفظ في القاعدة
        stadium_data = {
            "name": name,
            "price_per_hour": price,
            "address": address,
            "owner_id": owner_id,
            "image_url": img_url,
            "is_active": True
        }
        res = supabase.table("stadiums").insert(stadium_data).execute()
        return {"message": "Success", "stadium": res.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- قسم اللاعب والحجوزات (Type B) ---

@app.get("/stadiums/explore")
async def list_stadiums():
    res = supabase.table("stadiums").select("*").eq("is_active", True).execute()
    return {"available_stadiums": res.data}

@app.post("/bookings/create")
async def create_booking(
    stadium_id: int,
    user_id: str,
    date: str, # Format: YYYY-MM-DD
    start_time: str, # Format: HH:MM
    is_challenge: bool = False
):
    # التحقق من عدم وجود حجز مسبق في نفس الوقت
    check = supabase.table("bookings")\
        .select("*")\
        .eq("stadium_id", stadium_id)\
        .eq("booking_date", date)\
        .eq("start_time", start_time)\
        .execute()
    
    if check.data:
        raise HTTPException(status_code=400, detail="هذا الوقت محجوز مسبقاً")

    booking_data = {
        "stadium_id": stadium_id,
        "user_id": user_id,
        "booking_date": date,
        "start_time": start_time,
        "is_challenge": is_challenge,
        "status": "confirmed"
    }
    res = supabase.table("bookings").insert(booking_data).execute()
    return {"message": "تم الحجز بنجاح", "booking": res.data}

# --- قسم التحديات والبحث عن فريق ---

@app.post("/challenges/open")
async def open_challenge(booking_id: int, user_id: str, message: str):
    challenge_data = {
        "booking_id": booking_id,
        "team_a_id": user_id,
        "message": message,
        "status": "open"
    }
    res = supabase.table("challenges").insert(challenge_data).execute()
    return {"message": "تم نشر التحدي، بانتظار الخصم", "challenge": res.data}

@app.get("/challenges/list")
async def get_open_challenges():
    # جلب التحديات المفتوحة مع بيانات الملاعب (Join بسيط)
    res = supabase.table("challenges")\
        .select("*, bookings(booking_date, start_time, stadiums(name))")\
        .eq("status", "open")\
        .execute()
    return {"challenges": res.data}

# وظيفة الـ Keep-Alive لمنع تجميد سوبابيس
@app.get("/keep-alive")
def keep_alive():
    supabase.table("stadiums").select("id").limit(1).execute()
    return {"status": "Supabase is awake"}