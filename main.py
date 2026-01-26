from curl_cffi import requests
import json
import time

# --- EN ÖNEMLİ KISIM ---
# 1. Adımda kopyaladığın upuzun COOKIE kodunu tırnakların içine yapıştır.
# İçinde "cf_clearance" olduğundan emin ol.
COOKIE_VALUE = "_ga=GA1.1.1140573160.1769444242; _ga_HB4ZCY9JJC=GS2.1.s1769444241$o1$g1$t1769446564$j60$l0$h0"

HEADERS = {
    'authority': 'api.anizium.co',
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'origin': 'https://anizium.co',
    'referer': 'https://anizium.co/',
    # User-Agent'i sildik, curl_cffi kendi atayacak.
    # User-Profile ve Session zaten Cookie içinde varsa buraya ekstradan gerekmez ama kalsın.
    'user-profile': '69938938',
    'cookie': COOKIE_VALUE 
}

BASE_URL = "https://api.anizium.co"

class AniziumScraper:
    def __init__(self):
        # chrome110 bazen GitHub IP'lerinde 120'den daha iyi çalışır
        self.session = requests.Session(impersonate="chrome110")
        self.session.headers.update(HEADERS)
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []

    def get_top_anime(self):
        url = f"{BASE_URL}/page/top?platform=all&page=1"
        print(f"Liste taranıyor...")
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                # Bazen API HTML hata sayfası döner, kontrol edelim
                if "<!DOCTYPE html>" in response.text:
                    print("❌ HATA: Cookie geçersiz veya süresi dolmuş.")
                    print("Lütfen tarayıcıdan YENİ Cookie alıp koda yapıştır.")
                    return []
                
                data = response.json()
                if "data" in data and isinstance(data["data"], list):
                    return data["data"]
                elif "data" in data and "items" in data["data"]:
                    return data["data"]["items"]
                return []
            else:
                print(f"❌ Erişim Hatası: {response.status_code}")
                return []
        except Exception as e:
            print(f"Bağlantı sorunu: {e}")
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
        except:
            pass
        return None

    def run(self):
        print("Bot başlatılıyor (Cookie Yöntemi)...")
        
        animes = self.get_top_anime()
        print(f"✅ Bulunan Anime Sayısı: {len(animes)}")

        if len(animes) > 0:
            for anime in animes:
                name = anime.get("name", "Bilinmeyen Anime")
                a_id = anime.get("id")
                poster = anime.get("poster", "")
                if poster and not poster.startswith("http"):
                    poster = f"https://anizium.co{poster}"

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
                        self.json_data.append({
                            "name": name, 
                            "image": poster, 
                            "url": video_url, 
                            "referer": "https://anizium.co/"
                        })
                        print(f"Eklendi: {name}")
                
                time.sleep(0.3) 

        # Dosyaları Kaydet (Boş olsa bile)
        with open("anizium.m3u", "w", encoding="utf-8") as f:
            f.write(self.m3u_content)
        
        with open("anizium.json", "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4, ensure_ascii=False)
            
        print("✅ Dosyalar oluşturuldu.")

if __name__ == "__main__":
    AniziumScraper().run()
