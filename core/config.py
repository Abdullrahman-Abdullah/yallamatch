import os
import json
from supabase import create_client, Client
import firebase_admin
from firebase_admin import credentials

# --- إعدادات Supabase المباشرة للتجربة ---
SUPABASE_URL = "https://hhqzsqwtkwmfilobubhs.supabase.co" # ضع الرابط هنا مباشرة
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhocXpzcXd0a3dtZmlsb2J1YmhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2MTgwNTIsImV4cCI6MjA5MjE5NDA1Mn0.-fI-9ARvWBEttBjNSnyAxq050ySq-yEY0sXkI11E1lE" # ضع المفتاح هنا مباشرة[cite: 3]

# تهيئة عميل Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- إعدادات Firebase ---
def initialize_firebase():
    """تهيئة Firebase باستخدام متغير البيئة أو ملف محلي"""
    if not firebase_admin._apps:
        # فحص وجود متغير البيئة أولاً
        firebase_json = os.getenv("FIREBASE_CONFIG")
        
        if firebase_json:
            try:
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            except Exception:
                pass
        else:
            # الحل الاحتياطي: الملف المحلي (تأكد من وجوده في مجلد core)[cite: 2]
            FIREBASE_KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
            if os.path.exists(FIREBASE_KEY_PATH):
                cred = credentials.Certificate(FIREBASE_KEY_PATH)
                firebase_admin.initialize_app(cred)

initialize_firebase()