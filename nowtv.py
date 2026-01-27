import cloudscraper
from bs4 import BeautifulSoup
import re
import socket

# --- ZAMAN AŞIMI AYARI ---
# Scriptin takılmasını önler (30 saniye cevap gelmezse atlar)
socket.setdefaulttimeout(30)

BASE_URL = "https://www.nowtv.com.tr"

# Taranacak Ana Sayfalar
CATEGORIES = [
    {"url": "/dizi-izle", "type": "DIZI"},
    {"url": "/dizi-arsivi", "type": "DIZI"},
    {"url": "/program-izle", "type": "PROGRAM"},
    {"url": "/program-arsivi", "type": "PROGRAM"}
]

def get_soup(scraper, url):
    try:
        full_url = BASE_URL + url if not url.startswith("http") else url
        resp = scraper.get(full_url, timeout=20)
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        print(f"    Hata (Erişim): {e}")
        return None

def get_all_links(scraper, category_url):
    """Kategori sayfasındaki potansiyel dizi linklerini toplar"""
    links_found = []
    soup = get_soup(scraper, category_url)
    if not soup: return []

    print(f"📂 Kategori taranıyor: {category_url}")
    
    # Tüm linkleri al
    all_a_tags = soup.find_all('a', href=True)
    
    for a in all_a_tags:
        href = a['href']
        
        # Gereksiz linkleri ele
        if any(x in href for x in ['yayin-akisi', 'canli-yayin', 'haber', 'iletisim', 'kunye', 'giris', 'facebook', 'twitter']):
            continue
            
        # Sadece kök dizin linklerini al (/kizil-goncalar gibi) - alt sayfaları alma
        # Link '/' ile başlamalı ve içinde başka '/' olmamalı (sondaki hariç)
        clean_href = href.strip('/')
        if '/' not in clean_href and len(clean_href) > 3:
            
            # Resim bulmaya çalış
            img = a.find('img')
            poster = ""
            title = clean_href.replace('-', ' ').title()
            
            if img:
                poster = img.get('data-src') or img.get('src') or ""
                if img.get('alt'): title = img.get('alt')

            # Benzersizlik kontrolü
            if not any(x['url'] == href for x in links_found):
                links_found.append({
                    "title": title,
                    "url": "/" + clean_href,
                    "poster": poster
                })

    print(f"  -> {len(links_found)} adet potansiyel içerik bulundu.")
    return links_found

def get_m3u8_link(scraper, page_url):
    """Video sayfasından m3u8 bulur"""
    try:
        full_url = BASE_URL + page_url if not page_url.startswith("http") else page_url
        r = scraper.get(full_url, timeout=10)
        
        # Regex ile m3u8 ara
        match = re.search(r'https?://[^\s"\'\\,]+\.m3u8[^\s"\'\\,]*', r.text)
        if match:
            return match.group(0).replace('\\/', '/')
    except:
        pass
    return None

def main():
    print("🚀 NOW TV Scraper Başlatıldı...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    m3u_content = "#EXTM3U\n"
    total_videos = 0

    # 1. Tüm Kategorileri Gez
    for cat in CATEGORIES:
        shows = get_all_links(scraper, cat['url'])
        
        # 2. Her Dizinin İçine Gir
        for show in shows:
            # Bölümler sayfasına git
            bolumler_url = show['url'] + "/bolumler"
            
            # Hızlı kontrol: Eğer arşivse url yapısı farklı olabilir ama genelde /bolumler çalışır
            soup = get_soup(scraper, bolumler_url)
            if not soup: continue

            # Select Box'ı Bul (En güvenilir yöntem NOW TV için)
            select = soup.find('select', id='video-finder-changer')
            
            if select:
                print(f"  📺 İşleniyor: {show['title']}")
                options = select.find_all('option', {'data-target': True})
                
                # Sadece son 5 bölümü al (Hız için) - İstersen [:5] kısmını kaldırabilirsin
                for opt in options[:10]: 
                    ep_name = opt.get_text(strip=True)
                    target = opt['data-target']
                    
                    link = None
                    if ".m3u8" in target:
                        link = target
                    else:
                        link = get_m3u8_link(scraper, target)
                    
                    if link:
                        full_title = f"{show['title']} - {ep_name}"
                        m3u_content += f'#EXTINF:-1 group-title="{cat["type"]}" tvg-logo="{show["poster"]}",{full_title}\n'
                        m3u_content += f'{link}\n'
                        total_videos += 1
                        print(f"    + Eklendi: {ep_name}")
            else:
                # Select box yoksa belki tek bölümdür veya sayfa yapısı farklıdır, atla.
                pass

    if total_videos > 0:
        with open("nowtv.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        print(f"\n✅ Toplam {total_videos} video bulundu ve kaydedildi.")
    else:
        print("\n❌ Hiç video bulunamadı! Site yapısı değişmiş olabilir.")
        # Boş dosya oluştur ki hata vermesin
        with open("nowtv.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")

if __name__ == "__main__":
    main()
