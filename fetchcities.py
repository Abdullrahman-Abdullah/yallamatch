import requests
from core.config import supabase

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# استعلام يعتمد على مستطيل جغرافي يغطي دمشق وريفها بالكامل
# الإحداثيات (جنوب، غرب، شمال، شرق)
BBOX = "33.20,35.80,33.90,36.60" 

OVERPASS_QUERY = f"""
[out:json][timeout:60];
(
  node["place"~"city|town|village|suburb|neighbourhood"]({BBOX});
  way["place"~"city|town|village|suburb|neighbourhood"]({BBOX});
);
out center;
"""

def sync_local_data():
    print("جاري سحب بيانات الأحياء والمناطق في دمشق وريفها...")
    
    headers = {
        'User-Agent': 'YallaMatch_Data_Fetcher/1.0',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(OVERPASS_URL, data={'data': OVERPASS_QUERY}, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ خطأ من السيرفر: {response.status_code}")
            return

        data = response.json()
        elements = data.get('elements', [])
        
        if not elements:
            print("⚠️ لم يتم العثور على بيانات. قد تكون الإحداثيات بحاجة لضبط أو السيرفر لم يستجب.")
            return

        print(f"✅ تم العثور على {len(elements)} منطقة.")

        added_count = 0
        for element in elements:
            tags = element.get('tags', {})
            name_ar = tags.get('name:ar') or tags.get('name')
            name_en = tags.get('name:en', '')
            
            # في حال كان النوع 'node' نأخذ lat/lon، وفي حال 'way' نأخذ center
            lat = element.get('lat') or element.get('center', {}).get('lat')
            lon = element.get('lon') or element.get('center', {}).get('lon')

            if not name_ar or not lat: continue

            try:
                supabase.table("cities").upsert({
                    "name_ar": name_ar,
                    "name_en": name_en,
                    "location": f"POINT({lon} {lat})",
                    "province_name": "دمشق وريفها"
                }, on_conflict="name_ar").execute()
                added_count += 1
            except Exception:
                continue

        print(f"🚀 تم تخزين {added_count} منطقة بنجاح في قاعدة البيانات!")

    except Exception as e:
        print(f"❌ حدث خطأ: {e}")

if __name__ == "__main__":
    sync_local_data()