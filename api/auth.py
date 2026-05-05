import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.config import supabase # استيراد العميل المركزي[cite: 2]

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
        # حفظ الرمز في سوبابايس[cite: 2]
        supabase.table("otp_codes").upsert({
            "phone_number": request.phone_number,
            "otp_code": otp,
            "is_verified": False,
        }, on_conflict="phone_number").execute()
        
        # ملاحظة: في هذه المرحلة تظهر رسالة النجاح، والرمز يُرسل برمجياً (أو يظهر في الكونسول للتجربة)[cite: 2]
        return {"status": "success", "message": "OTP saved successfully", "otp": otp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save OTP: {str(e)}")

@router.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest):
    # التحقق من صحة الرمز[cite: 2]
    response = supabase.table("otp_codes") \
        .select("*") \
        .eq("phone_number", request.phone_number) \
        .eq("otp_code", request.otp_code) \
        .eq("is_verified", False) \
        .execute()

    if not response.data:
        raise HTTPException(status_code=400, detail="الرمز خاطئ أو منتهي الصلاحية")

    # تحديث حالة الرمز ليصبح مستخدماً[cite: 2]
    supabase.table("otp_codes").update({"is_verified": True}).eq("id", response.data[0]['id']).execute()

    # البحث عن المستخدم في جدول البروفايل برقم الهاتف الدولي[cite: 2]
    international_phone = "+963" + request.phone_number[1:]
    user_query = supabase.table("profiles").select("*").eq("phone_number", international_phone).execute()

    user_data = user_query.data[0] if user_query.data else None

    return {
        "status": "success",
        "exists": user_data is not None,
        "user_data": user_data,
        "user_id": international_phone
    }
    
@router.post("/update-profile")
async def update_profile(profile: UserProfileUpdate):
    try:
        # تحديث بيانات المستخدم وربطه بالمدينة المختارة
        response = supabase.table("profiles").upsert({
            "id": profile.user_id,
            "full_name": profile.full_name,
            "city_id": profile.city_id, # ربط احترافي عبر ID
            "updated_at": "now()"
        }).execute()
        
        return {"status": "success", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    