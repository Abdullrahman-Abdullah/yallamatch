from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.auth import router as auth_router
from api.locations import router as loc_router
from core.config import initialize_firebase # استدعاء دالة التهيئة المركزية

app = FastAPI(title="Yalla Match API")

# 1. إعدادات الـ CORS للسماح بالاتصال من تطبيق الهاتف
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. تسجيل الـ Routers 
# لاحظ أننا استخدمنا Routers منفصلة للحفاظ على نظافة الملف
# روابط تسجيل الدخول ستكون متاحة تحت /auth/send-otp و /auth/verify-otp تلقائياً
app.include_router(auth_router)
app.include_router(loc_router)

# 3. نقطة فحص عمل السيرفر (اختياري)
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Welcome to Yalla Match API Server",
        "version": "1.0.0"
    }

# ملاحظة: تهيئة Firebase و Supabase تتم الآن تلقائياً عند استيراد core.config