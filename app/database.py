import os
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# الاتصال بـ Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# إعداد Cloudinary لرفع صور الملاعب
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)