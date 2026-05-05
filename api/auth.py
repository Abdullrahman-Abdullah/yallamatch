import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.config import supabase 

router = APIRouter(prefix="/auth", tags=["Authentication"])

class PhoneAuthRequest(BaseModel):
    phone_number: str

class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp_code: str

class UserProfileUpdate(BaseModel):
    user_id: str
    full_name: str
    city_id: int

@router.post("/send-otp")
async def send_otp(request: PhoneAuthRequest):
    otp = str(random.randint(100000, 999999))
    try:
        supabase.table("otp_codes").upsert({
            "phone_number": request.phone_number,
            "otp_code": otp,
            "is_verified": False,
        }, on_conflict="phone_number").execute() 
        return {"status": "success", "otp": otp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest):
    response = supabase.table("otp_codes") \
        .select("*") \
        .eq("phone_number", request.phone_number) \
        .eq("otp_code", request.otp_code) \
        .eq("is_verified", False) \
        .execute()

    if not response.data:
        raise HTTPException(status_code=400, detail="الرمز خاطئ")

    supabase.table("otp_codes").update({"is_verified": True}).eq("id", response.data[0]['id']).execute() 

    international_phone = "+963" + request.phone_number[1:]
    user_query = supabase.table("profiles").select("*").eq("phone_number", international_phone).execute() 

    if user_query.data:
        user_data = user_query.data[0]
        return {
            "status": "success",
            "exists": True,
            "user_data": user_data,
            "user_id": user_data['id'] # إرجاع الـ UUID الحقيقي[cite: 4]
        }
    else:
        return {
            "status": "success",
            "exists": False,
            "user_id": international_phone
        }

@router.post("/update-profile")
async def update_profile(profile: UserProfileUpdate):
    try:
        response = supabase.table("profiles").upsert({
            "id": profile.user_id, # سيقبل الـ UUID القادم من التطبيق[cite: 4]
            "full_name": profile.full_name,
            "city_id": profile.city_id,
            "updated_at": "now()"
        }).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))