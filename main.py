import requests
import json
import time
import sys

# --- SİTEDEN ALDIĞIMIZ OTURUM BİLGİLERİ ---
# Bu bilgiler senin gönderdiğin cURL komutundan alındı.
HEADERS = {
    'authority': 'api.anizium.co',
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'cf-control': '134e1d13545c0f545508090657410003064a43015657570f',
    'content-type': 'application/json',
    'device': 'browser',
    'language': 'tr',
    'origin': 'https://anizium.co',
    'referer': 'https://anizium.co/',
    'site': 'main',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'user-profile': '69938938',
    'user-session': '0856040a5459555a6e060006515a50000c6e0c42011f070a4e451254170a415f4341041803084243454e0718115b585b'
}

BASE_URL = "https://api.anizium.co"

class AniziumScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []

    def get_top_anime(self):
        """Popüler animeleri veya ana sayfadaki listeyi çeker"""
        # Senin gönderdiğin cURL'deki çalışan adres:
        url = f"{BASE_URL}/page/top?platform=all&page=1" 
        
        print(f"Liste çekiliyor: {url}")
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                # API yapısına göre veriyi bul
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                elif "data" in data and "items" in data["data"]:
                    return data["data"]["items"]
                else:
                    print("Veri yapısı beklenildiği gibi değil:", str(data)[:100])
                    return []
            else:
                print(f"Liste çekilemedi. Kod: {response.status_code}")
                print("Cevap:", response.text)
                return []
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            return []

    def get_source(self, anime_id):
        """Videoların asıl linkini (m3u8) çeker"""
        url = f"{BASE_URL}/anime/source"
        # Standart parametreler (1. Sezon 1. Bölüm)
        params = {
            "id": anime_id,
            "season": 1,
            "episode": 1,
            "server": 1,
            "plan": "standart",
            "lang": "tr"
            # Header'da user-session olduğu için 'u' parametresine gerek kalmayabilir
            # ama garanti olsun diye header zaten yetkili.
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Kaynak hatası (ID: {anime_id}): {e}")
        return None

    def run(self):
        print("Bot başlatılıyor (Session Modu)...")
        
        # 1. Animeleri Listele
        animes = self.get_top_anime()
        print(f"Bulunan Anime Sayısı: {len(animes)}")

        if len(animes) == 0:
            print("⚠️ Hiç içerik bulunamadı. Session süresi dolmuş olabilir.")
        
        # 2. Her anime için video linki bul
        for anime in animes:
            name = anime.get("name", "Bilinmeyen Anime")
            a_id = anime.get("id")
            poster = anime.get("poster", "")
            
            # Poster linkini düzelt
            if poster and not poster.startswith("http"):
                poster = f"https://anizium.co{poster}"

            print(f"İşleniyor: {name} (ID: {a_id})")
            
            # Kaynak Linkini Çek
            source_data = self.get_source(a_id)
            
            if source_data and "data" in source_data:
                sources = source_data["data"].get("sources", [])
                video_url = None
                
                # m3u8 veya mp4 ara
                for src in sources:
                    file_url = src.get("file", "")
                    if "m3u8" in file_url or "mp4" in file_url:
                        video_url = file_url
                        break
                
                if video_url:
                    # M3U'ya Ekle
                    self.m3u_content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Anime",{name}\n'
                    self.m3u_content += f'{video_url}\n'
                    
                    # JSON'a Ekle
                    self.json_data.append({
                        "name": name,
                        "image": poster,
                        "url": video_url,
                        "category": "Anime"
                    })
                    print(f"✅ EKLENDİ: {name}")
                else:
                    print(f"❌ Video linki bulunamadı: {name}")
            
            # Sunucuyu yormamak için kısa bekleme
            time.sleep(0.5)

        # 3. Dosyaları Kaydet (Boş olsa bile oluştur)
        try:
            with open("anizium.m3u", "w", encoding="utf-8") as f:
                f.write(self.m3u_content)
            
            with open("anizium.json", "w", encoding="utf-8") as f:
                json.dump(self.json_data, f, indent=4, ensure_ascii=False)
            
            print("Dosyalar başarıyla oluşturuldu.")
        except Exception as e:
            print(f"Dosya yazma hatası: {e}")

if __name__ == "__main__":
    AniziumScraper().run()
