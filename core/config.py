import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials

# تحميل المتغيرات من ملف .env في التطوير المحلي
load_dotenv()

# --- إعدادات Supabase ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# تهيئة عميل Supabase المركزي
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- إعدادات Firebase ---
def initialize_firebase():
    """تهيئة Firebase Admin SDK باستخدام متغيرات البيئة أو ملف محلي"""
    if not firebase_admin._apps:
        # محاولة القراءة من متغيرات البيئة (مناسب لـ Vercel)
        firebase_json = os.getenv("FIREBASE_CONFIG")
        
        if firebase_json:
            try:
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized via Environment Variables")
            except Exception as e:
                print(f"Error parsing FIREBASE_CONFIG env: {e}")
        else:
            # الحل الاحتياطي: البحث عن الملف محلياً (للتجربة الحالية)[cite: 3]
            FIREBASE_KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if os.path.exists(FIREBASE_KEY_PATH):
                cred = credentials.Certificate(FIREBASE_KEY_PATH)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized via local JSON file")
            else:
                print("Warning: Firebase credentials not found!")

# استدعاء التهيئة فور استيراد الملف[cite: 6]
initialize_firebase()