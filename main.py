import requests
import json
import os

# --- KULLANICI BİLGİLERİ (BURAYA GÖMÜLDÜ) ---
EMAIL = "Yigitefealadag@gmail.com"
PASSWORD = "Sa42758170+-++"

# --- AYARLAR ---
BASE_URL = "https://api.anizium.co"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://anizium.co",
    "Referer": "https://anizium.co/",
    "Content-Type": "application/json"
}

class AniziumScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.token = None
        self.user_id = "81086288" # Varsayılan olarak verdiğin ID
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []

    def login(self):
        # Olası Giriş Adresleri
        endpoints = ["/auth/login", "/api/auth/login", "/login", "/user/login"]
        payload = {"email": EMAIL, "password": PASSWORD}

        print(f"Giriş deneniyor: {EMAIL}...")
        
        for ep in endpoints:
            try:
                r = self.session.post(f"{BASE_URL}{ep}", json=payload)
                if r.status_code == 200:
                    data = r.json()
                    # Token yakalama
                    if "token" in data:
                        self.token = data["token"]
                    elif "data" in data and "token" in data["data"]:
                        self.token = data["data"]["token"]
                    
                    if self.token:
                        print(f"✅ Giriş Başarılı! (Endpoint: {ep})")
                        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                        return True
            except Exception as e:
                print(f"Hata ({ep}): {e}")
        
        print("⚠️ Giriş yapılamadı, ancak herkese açık içerikler deneniyor...")
        return False # Giriş başarısız olsa da devam etmeyi dener

    def get_anime_list(self):
        # Anime listesi çekme
        url = f"{BASE_URL}/anime/filter?page=1&limit=50&sort=newest"
        try:
            print("Anime listesi çekiliyor...")
            r = self.session.get(url)
            if r.status_code == 200:
                data = r.json()
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                return data.get("data", {}).get("items", [])
        except Exception as e:
            print(f"Liste hatası: {e}")
        return []

    def get_source(self, anime_id):
        # Video kaynağı çekme
        url = f"{BASE_URL}/anime/source"
        params = {
            "id": anime_id, "season": 1, "episode": 1,
            "server": 1, "plan": "standart", "u": self.user_id, "lang": "tr"
        }
        try:
            r = self.session.get(url, params=params)
            if r.status_code == 200:
                return r.json()
        except:
            pass
        return None

    def run(self):
        self.login() # Giriş yapmayı dene
        
        animes = self.get_anime_list()
        print(f"Bulunan içerik sayısı: {len(animes)}")

        for anime in animes:
            name = anime.get("name", "Bilinmeyen Anime")
            a_id = anime.get("id")
            poster = anime.get("poster", "")
            if poster and not poster.startswith("http"):
                poster = f"https://anizium.co{poster}"

            source = self.get_source(a_id)
            if source and "data" in source:
                sources_list = source["data"].get("sources", [])
                video_url = None
                
                # M3U8 veya MP4 bul
                for item in sources_list:
                    f_path = item.get("file", "")
                    if "m3u8" in f_path or "mp4" in f_path:
                        video_url = f_path
                        break
                
                if video_url:
                    # M3U Ekleme
                    self.m3u_content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Anime",{name}\n{video_url}\n'
                    # JSON Ekleme
                    self.json_data.append({
                        "name": name,
                        "image": poster,
                        "url": video_url,
                        "referer": "https://anizium.co/"
                    })
                    print(f"Eklendi: {name}")

        # Dosyaları kaydet
        with open("anizium.m3u", "w", encoding="utf-8") as f:
            f.write(self.m3u_content)
        
        with open("anizium.json", "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4, ensure_ascii=False)
            
        print("✅ Dosyalar oluşturuldu: anizium.m3u, anizium.json")

if __name__ == "__main__":
    AniziumScraper().run()
