import requests
import json
import os

# GitHub Secrets'tan veya environment'tan verileri al
EMAIL = os.environ.get("ANIZIUM_EMAIL")
PASSWORD = os.environ.get("ANIZIUM_PASSWORD")

# Sabitler
BASE_URL = "https://api.anizium.co"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://anizium.co",
    "Referer": "https://anizium.co/"
}

class AniziumScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.token = None
        self.user_id = None

    def login(self):
        """
        Siteye giriş yaparak Token alır.
        NOT: '/auth/login' kısmı tahminidir. Network tabından kontrol etmelisin.
        """
        login_url = f"{BASE_URL}/auth/login"  # BURAYI KONTROL ET
        payload = {
            "email": EMAIL,
            "password": PASSWORD
        }
        
        try:
            print(f"Giriş yapılıyor: {EMAIL}")
            # Eğer site JSON bekliyorsa json=payload, form bekliyorsa data=payload
            response = self.session.post(login_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                # Token ve User ID'nin döndüğü yeri response yapısına göre düzenle:
                self.token = data.get("token") 
                self.user_id = data.get("user", {}).get("id") # Örn: 81086288
                print("Giriş başarılı!")
                return True
            else:
                print(f"Giriş hatası: {response.text}")
                return False
        except Exception as e:
            print(f"Login exception: {e}")
            return False

    def get_anime_list(self):
        """
        Sitedeki animeleri listeler.
        NOT: '/anime/filter' veya '/home' olabilir.
        """
        list_url = f"{BASE_URL}/anime/filter?page=1&limit=20" # Örnek URL
        print("Anime listesi çekiliyor...")
        response = self.session.get(list_url)
        if response.status_code == 200:
            return response.json().get("data", []) # Yapıya göre değişebilir
        return []

    def get_source(self, anime_id, season=1, episode=1):
        """
        Verdiğin örnek link yapısına göre kaynak çeker.
        Örnek: https://api.anizium.co/anime/source?id=...
        """
        # Senin verdiğin user id parametresi (u=81086288) login'den gelmeli.
        # Eğer login çalışmazsa manuel olarak buraya yazabilirsin.
        uid = self.user_id if self.user_id else "81086288"
        
        source_url = f"{BASE_URL}/anime/source"
        params = {
            "id": anime_id,
            "season": season,
            "episode": episode,
            "server": 1,
            "plan": "standart",
            "u": uid,
            "lang": "tr" # veya 'en'
        }
        
        try:
            response = self.session.get(source_url, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Source error: {e}")
        return None

    def generate_playlists(self):
        if not self.login():
            print("Login olunamadı, işlem durduruluyor.")
            return

        animes = self.get_anime_list()
        m3u_content = "#EXTM3U\n"
        json_data = []

        for anime in animes:
            # API yanıtındaki key isimlerini kontrol et (name, id, cover vb.)
            title = anime.get("name", "Bilinmeyen Anime")
            anime_id = anime.get("id")
            cover = anime.get("poster", "") 
            
            # Sadece 1. Sezon 1. Bölüm örneği. Döngüye sokulabilir.
            source_data = self.get_source(anime_id, 1, 1)
            
            if source_data and "data" in source_data:
                # Video URL'sini bulma (m3u8 veya mp4)
                video_url = ""
                # Genelde sources dizisi içinde olur
                sources = source_data.get("data", {}).get("sources", [])
                for src in sources:
                    if "m3u8" in src.get("file", ""):
                        video_url = src["file"]
                        break
                    elif "mp4" in src.get("file", ""):
                        video_url = src["file"]
                
                if video_url:
                    # M3U Formatı
                    m3u_content += f'#EXTINF:-1 tvg-id="{anime_id}" tvg-logo="{cover}" group-title="Anime",{title}\n'
                    m3u_content += f'{video_url}\n'
                    
                    # JSON Formatı
                    json_data.append({
                        "name": title,
                        "image": cover,
                        "url": video_url,
                        "category": "Anime"
                    })
                    print(f"Eklendi: {title}")

        # Dosyaları yaz
        with open("anizium.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
            
        with open("anizium.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
            
        print("Playlists oluşturuldu.")

if __name__ == "__main__":
    scraper = AniziumScraper()
    scraper.generate_playlists()
