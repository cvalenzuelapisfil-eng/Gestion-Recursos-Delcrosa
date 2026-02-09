import requests

SUPABASE_URL = "https://folviontmigjpmjfmaxr.supabase.co"
SUPABASE_KEY = "sb_publishable_dcx0H3tSyj3UiZ8Mc9OGjw_qRcU4eVq"

url = f"{SUPABASE_URL}/rest/v1/personal"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Accept": "application/json"
}

print("🔌 Conectando a Supabase vía REST...")

resp = requests.get(url, headers=headers)

if resp.status_code == 200:
    print("✅ Conexión exitosa")
    print("📦 Datos:")
    print(resp.json())
else:
    print("❌ Error")
    print(resp.status_code, resp.text)
