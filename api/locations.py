from fastapi import APIRouter, Query, HTTPException
from core.config import supabase

router = APIRouter(prefix="/locations", tags=["Locations"])

@router.get("/search")
async def search_districts(q: str = Query(..., min_length=2)):
    """
    البحث عن حي أو منطقة في دمشق وريفها (Offline من قاعدة البيانات)
    """
    try:
        # البحث عن الأسماء العربية التي تحتوي على النص المدخل
        response = supabase.table("cities") \
            .select("id, name_ar, province_name") \
            .ilike("name_ar", f"%{q}%") \
            .limit(10) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail="خطأ في جلب البيانات المحلية")

@router.get("/detect-nearby")
async def detect_nearby_districts(lat: float, lon: float, limit: int = 5):
    """
    جلب قائمة بأقرب المناطق للمستخدم بناءً على إحداثياته
    """
    try:
        # استدعاء الدالة المحدثة مع تمرير الحد المطلوب
        response = supabase.rpc("get_nearby_districts_v2", {
         "user_lat": lat,
         "user_long": lon,
            "radius_meters": 7000  # توسيع النطاق لـ 7 كم
        }).execute()
        
        if not response.data:
            return {"message": "الموقع خارج نطاق التغطية"}
            
        return response.data # سيعيد الآن قائمة (List) وليس كائناً واحداً
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/all-provinces")
async def get_provinces():
    """عرض المحافظات المتاحة حالياً"""
    return [{"id": 1, "name": "دمشق"}, {"id": 2, "name": "ريف دمشق"}]
