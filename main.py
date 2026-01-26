from curl_cffi import requests
import json
import time

# --- AYARLAR ---
# Cloudflare'i aşmak için gerçek tarayıcı headerları
HEADERS = {
    'authority': 'api.anizium.co',
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'origin': 'https://anizium.co',
    'referer': 'https://anizium.co/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # SENİN GÖNDERDİĞİN AUTH BİLGİLERİ:
    'user-profile': '69938938',
    'user-session': '0856040a5459555a6e060006515a50000c6e0c42011f070a4e451254170a415f4341041803084243454e0718115b585b'
}

BASE_URL = "https://api.anizium.co"

class AniziumScraper:
    def __init__(self):
        # impersonate="chrome120" -> Cloudflare'i kandıran sihirli kısım
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update(HEADERS)
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []

    def get_top_anime(self):
        url = f"{BASE_URL}/page/top?platform=all&page=1"
        print(f"Liste çekiliyor (Bypass Modu): {url}")
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                elif "data" in data and "items" in data["data"]:
                    return data["data"]["items"]
                return []
            else:
                print(f"❌ HATA: {response.status_code}")
                # Cloudflare hala engelliyorsa HTML döner, onu görmeyelim.
                if "Cloudflare" in response.text:
                    print("Cloudflare engeli devam ediyor.")
                return []
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            return []

    def get_source(self, anime_id):
        url = f"{BASE_URL}/anime/source"
        params = {
            "id": anime_id, "season": 1, "episode": 1,
            "server": 1, "plan": "standart", "lang": "tr"
        }
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Kaynak hatası (ID: {anime_id}): {e}")
        return None

    def run(self):
        print("Bot başlatılıyor (Cloudflare Bypass Modu)...")
        
        animes = self.get_top_anime()
        print(f"✅ Bulunan Anime Sayısı: {len(animes)}")

        for anime in animes:
            name = anime.get("name", "Bilinmeyen Anime")
            a_id = anime.get("id")
            poster = anime.get("poster", "")
            if poster and not poster.startswith("http"):
                poster = f"https://anizium.co{poster}"

            # Kaynak Linkini Çek
            source_data = self.get_source(a_id)
            if source_data and "data" in source_data:
                sources = source_data["data"].get("sources", [])
                video_url = None
                
                for src in sources:
                    file_url = src.get("file", "")
                    if "m3u8" in file_url or "mp4" in file_url:
                        video_url = file_url
                        break
                
                if video_url:
                    self.m3u_content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Anime",{name}\n{video_url}\n'
                    self.json_data.append({"name": name, "image": poster, "url": video_url, "referer": "https://anizium.co/"})
                    print(f"Eklendi: {name}")
            
            time.sleep(0.2) # Nazik olalım

        # Dosyaları Kaydet
        with open("anizium.m3u", "w", encoding="utf-8") as f:
            f.write(self.m3u_content)
        
        with open("anizium.json", "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4, ensure_ascii=False)
            
        print("✅ İşlem Tamamlandı.")

if __name__ == "__main__":
    AniziumScraper().run()
