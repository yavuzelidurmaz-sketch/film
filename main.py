from seleniumbase import SB
import json
import time

# --- KULLANICI BİLGİLERİ ---
EMAIL = "Yigitefealadag@gmail.com"
PASSWORD = "Sa42758170+-++"

class AniziumBot:
    def __init__(self):
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []

    def run(self):
        # uc=True -> Undetected Mode (Cloudflare'i aşan mod)
        # headless=False -> xvfb kullandığımız için False yapıyoruz (Linux'ta sanal ekranda çalışacak)
        with SB(uc=True, headless=False) as sb:
            print("🌍 Site açılıyor...")
            sb.open("https://anizium.co/login")
            
            # Sayfanın yüklenmesini bekle
            sb.sleep(4)
            
            # --- GİRİŞ YAPMA ---
            print(f"👤 Giriş yapılıyor: {EMAIL}")
            try:
                # Login inputlarını bul ve yaz
                sb.type('input[name="email"]', EMAIL)
                sb.type('input[name="password"]', PASSWORD)
                
                # Giriş butonuna tıkla (Genel buton seçicisi)
                sb.click('button[type="submit"]')
                
                # Giriş sonrası yönlendirmeyi bekle
                sb.sleep(6)
            except Exception as e:
                print(f"⚠️ Giriş ekranında sorun: {e}")
                # Belki zaten giriş yapılıdır, devam et

            # --- ANIME LİSTESİNİ ÇEKME ---
            print("📋 Anime listesi alınıyor...")
            # API'ye tarayıcı üzerinden gidiyoruz (Cookie sorunu olmasın diye)
            sb.open("https://api.anizium.co/page/top?platform=all&page=1")
            
            # Ekranda yazan JSON verisini al (pre etiketi içinde olur genelde)
            try:
                json_text = sb.get_text("body")
                data = json.loads(json_text)
                
                # Veri yapısını çöz
                anime_list = []
                if "data" in data and isinstance(data["data"], list):
                    anime_list = data["data"]
                elif "data" in data and "items" in data["data"]:
                    anime_list = data["data"]["items"]
                
                print(f"✅ Bulunan Anime: {len(anime_list)}")
                
                # --- VİDEO LİNKLERİNİ TOPLAMA ---
                for anime in anime_list:
                    name = anime.get("name", "Bilinmeyen")
                    a_id = anime.get("id")
                    poster = anime.get("poster", "")
                    if poster and not poster.startswith("http"):
                        poster = f"https://anizium.co{poster}"
                    
                    # Kaynak URL'sine git
                    source_url = f"https://api.anizium.co/anime/source?id={a_id}&season=1&episode=1&server=1&plan=standart&lang=tr"
                    sb.open(source_url)
                    
                    try:
                        src_text = sb.get_text("body")
                        src_data = json.loads(src_text)
                        
                        if src_data and "data" in src_data:
                            sources = src_data["data"].get("sources", [])
                            video_url = None
                            
                            for s in sources:
                                f_path = s.get("file", "")
                                if "m3u8" in f_path or "mp4" in f_path:
                                    video_url = f_path
                                    break
                            
                            if video_url:
                                self.m3u_content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Anime",{name}\n{video_url}\n'
                                self.json_data.append({
                                    "name": name,
                                    "image": poster,
                                    "url": video_url,
                                    "referer": "https://anizium.co/"
                                })
                                print(f"➕ Eklendi: {name}")
                    except:
                        pass
                    
                    # Çok hızlı istek atıp banlanmamak için bekle
                    sb.sleep(0.5)

            except Exception as e:
                print(f"❌ Veri çekme hatası: {e}")

            # --- DOSYALARI KAYDET ---
            with open("anizium.m3u", "w", encoding="utf-8") as f:
                f.write(self.m3u_content)
            
            with open("anizium.json", "w", encoding="utf-8") as f:
                json.dump(self.json_data, f, indent=4, ensure_ascii=False)
                
            print("✅ Dosyalar başarıyla oluşturuldu.")

if __name__ == "__main__":
    AniziumBot().run()
