from DrissionPage import ChromiumPage, ChromiumOptions
import json
import time

# --- KULLANICI BİLGİLERİ ---
EMAIL = "Yigitefealadag@gmail.com"
PASSWORD = "Sa42758170+-++"

class AniziumBot:
    def __init__(self):
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []
        
        # --- TARAYICI AYARLARI (Botu Gizleme) ---
        co = ChromiumOptions()
        co.set_argument('--no-sandbox') 
        co.set_argument('--lang=tr-TR')
        # Bu ayar Cloudflare'in bot olduğumuzu anlamasını zorlaştırır
        co.set_pref('credentials_enable_service', False)
        
        # Tarayıcıyı başlat
        self.page = ChromiumPage(addr_driver_opts=co)

    def run(self):
        print("🌍 Siteye bağlanılıyor (DrissionPage)...")
        
        # 1. Giriş Sayfasına Git
        self.page.get("https://anizium.co/login")
        time.sleep(5) # Cloudflare kontrolü için bekle

        # Engel Kontrolü
        if "blocked" in self.page.title.lower() or "sorry" in self.page.html.lower():
            print("❌ HATA: IP Adresi hala engelli. Ekran görüntüsü alınıyor.")
            self.page.get_screenshot(path='hata_engelli.jpg', full_page=True)
            return

        # 2. Giriş Yap
        print(f"👤 Giriş yapılıyor: {EMAIL}")
        if self.page.ele('input[name="email"]'):
            self.page.ele('input[name="email"]').input(EMAIL)
            self.page.ele('input[name="password"]').input(PASSWORD)
            self.page.ele('button[type="submit"]').click()
            time.sleep(5)
        else:
            print("⚠️ Giriş kutuları bulunamadı (Sayfa farklı yüklendi).")
            self.page.get_screenshot(path='hata_giris_yok.jpg')
        
        # 3. Anime Listesini API'den Çek
        print("📋 Anime listesi isteniyor...")
        self.page.get("https://api.anizium.co/page/top?platform=all&page=1")
        
        try:
            # Sayfadaki saf metni al (JSON)
            json_text = self.page.ele("tag:body").text
            
            # API Dönüşü HTML ise (Yani yine Cloudflare engeli varsa)
            if "<html" in json_text or "Cloudflare" in json_text:
                print("❌ API Cloudflare'e takıldı.")
                self.page.get_screenshot(path='hata_api.jpg')
            else:
                data = json.loads(json_text)
                anime_list = []
                
                if "data" in data and isinstance(data["data"], list):
                    anime_list = data["data"]
                elif "data" in data and "items" in data["data"]:
                    anime_list = data["data"]["items"]

                print(f"✅ Bulunan Anime Sayısı: {len(anime_list)}")

                # 4. Video Linklerini Topla
                for anime in anime_list:
                    name = anime.get("name", "Bilinmeyen")
                    a_id = anime.get("id")
                    poster = anime.get("poster", "")
                    if poster and not poster.startswith("http"):
                        poster = f"https://anizium.co{poster}"

                    # Kaynak URL'ye git
                    src_url = f"https://api.anizium.co/anime/source?id={a_id}&season=1&episode=1&server=1&plan=standart&lang=tr"
                    self.page.get(src_url)
                    
                    try:
                        src_text = self.page.ele("tag:body").text
                        src_json = json.loads(src_text)
                        
                        if "data" in src_json:
                            sources = src_json["data"].get("sources", [])
                            for s in sources:
                                f = s.get("file", "")
                                if "m3u8" in f or "mp4" in f:
                                    self.m3u_content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Anime",{name}\n{f}\n'
                                    self.json_data.append({"name": name, "image": poster, "url": f})
                                    print(f"➕ Eklendi: {name}")
                                    break
                    except:
                        pass
                    
                    time.sleep(0.5)

        except Exception as e:
            print(f"❌ Veri işleme hatası: {e}")
            self.page.get_screenshot(path='hata_genel.jpg')

        # 5. Kaydet
        with open("anizium.m3u", "w", encoding="utf-8") as f:
            f.write(self.m3u_content)
        
        with open("anizium.json", "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4, ensure_ascii=False)
            
        print("✅ İşlem tamamlandı.")
        self.page.quit()

if __name__ == "__main__":
    AniziumBot().run()
