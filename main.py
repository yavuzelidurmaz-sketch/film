from seleniumbase import SB
import json
import time
import os

EMAIL = "Yigitefealadag@gmail.com"
PASSWORD = "Sa42758170+-++"

class AniziumBot:
    def __init__(self):
        self.m3u_content = "#EXTM3U\n"
        self.json_data = []

    def run(self):
        # reconnect_time: Cloudflare takılırsa sayfayı yenileme süresi
        with SB(uc=True, headless=False) as sb:
            print("🌍 Site açılıyor (Cloudflare Korumalı)...")
            
            try:
                # 1. Cloudflare'i atlatarak açmayı dene
                sb.uc_open_with_reconnect("https://anizium.co/login", reconnect_time=6)
                
                # 2. Eğer Cloudflare kutucuğu varsa tıkla
                if sb.is_element_visible('iframe[src*="cloudflare"]'):
                    print("🛡️ Cloudflare tespit edildi, tıklanıyor...")
                    sb.uc_gui_click_captcha()
                
                sb.sleep(5) # Sayfanın oturmasını bekle
                
                # Başlık kontrolü (Nereye geldik?)
                print(f"📍 Mevcut Sayfa Başlığı: {sb.get_title()}")

                # 3. Giriş Yap
                print(f"👤 Giriş yapılıyor: {EMAIL}")
                
                # Eğer input yoksa fotoğraf çek ve hata ver
                if not sb.is_element_visible('input[name="email"]'):
                    print("⚠️ Email kutusu bulunamadı! Ekran görüntüsü alınıyor...")
                    sb.save_screenshot("hata_ekrani.png")
                    # Sayfa kaynağını da yazdıralım ki ne var görelim
                    print("Sayfa Kaynağı Özeti:", sb.get_text("body")[:200])
                else:
                    sb.type('input[name="email"]', EMAIL)
                    sb.type('input[name="password"]', PASSWORD)
                    sb.click('button[type="submit"]')
                    sb.sleep(5)

                # 4. Verileri Çek
                print("📋 Anime listesi API'den isteniyor...")
                sb.open("https://api.anizium.co/page/top?platform=all&page=1")
                
                # JSON hatası almamak için metni saf haliyle al
                json_text = sb.get_text("body")
                
                # Eğer Cloudflare engeli hala varsa HTML döner, kontrol et
                if "Cloudflare" in json_text or "<html" in json_text:
                    print("❌ API hala Cloudflare engeline takılıyor.")
                    sb.save_screenshot("api_engeli.png")
                else:
                    try:
                        data = json.loads(json_text)
                        anime_list = []
                        if "data" in data and isinstance(data["data"], list):
                            anime_list = data["data"]
                        elif "data" in data and "items" in data["data"]:
                            anime_list = data["data"]["items"]

                        print(f"✅ Bulunan Anime: {len(anime_list)}")

                        for anime in anime_list:
                            name = anime.get("name", "Bilinmeyen")
                            a_id = anime.get("id")
                            poster = anime.get("poster", "")
                            if poster and not poster.startswith("http"):
                                poster = f"https://anizium.co{poster}"

                            # Kaynağa git
                            src_url = f"https://api.anizium.co/anime/source?id={a_id}&season=1&episode=1&server=1&plan=standart&lang=tr"
                            sb.open(src_url)
                            try:
                                src_body = sb.get_text("body")
                                src_json = json.loads(src_body)
                                if "data" in src_json:
                                    sources = src_json["data"].get("sources", [])
                                    for s in sources:
                                        f = s.get("file", "")
                                        if "m3u8" in f or "mp4" in f:
                                            self.m3u_content += f'#EXTINF:-1 tvg-logo="{poster}" group-title="Anime",{name}\n{f}\n'
                                            self.json_data.append({"name": name, "image": poster, "url": f})
                                            print(f"➕ {name}")
                                            break
                            except:
                                pass
                            
                    except json.JSONDecodeError:
                        print(f"❌ JSON okunamadı. Gelen veri: {json_text[:100]}")

            except Exception as e:
                print(f"❌ Genel Hata: {e}")
                sb.save_screenshot("genel_hata.png")

            # Dosyaları kaydet
            with open("anizium.m3u", "w", encoding="utf-8") as f:
                f.write(self.m3u_content)
            with open("anizium.json", "w", encoding="utf-8") as f:
                json.dump(self.json_data, f, indent=4, ensure_ascii=False)
            print("✅ Dosyalar güncellendi.")

if __name__ == "__main__":
    AniziumBot().run()
