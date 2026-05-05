import os
from dotenv import load_dotenv
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials

# تحميل المتغيرات من ملف .env الموجود في المجلد الرئيسي
load_dotenv()

# إعدادات Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# تهيئة عميل Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعدادات Firebase
# المسار الآن أصبح داخل مجلد core بناءً على التنظيم الجديد
FIREBASE_KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")

def initialize_firebase():
    """تهيئة Firebase Admin SDK مرة واحدة فقط"""
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)

# استدعاء التهيئة عند استيراد الملف
initialize_firebase()