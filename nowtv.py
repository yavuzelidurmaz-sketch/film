import cloudscraper
from bs4 import BeautifulSoup
import re
import time

# --- AYARLAR ---
BASE_URL = "https://www.nowtv.com.tr"

# Taranacak Kaynaklar
TARGET_URLS = [
    {"url": "/dizi-izle", "type": "DIZI"},
    {"url": "/dizi-arsivi", "type": "DIZI"},
    {"url": "/program-izle", "type": "PROGRAM"},
    {"url": "/program-arsivi", "type": "PROGRAM"}
]

def get_soup(scraper, url):
    """URL'den BeautifulSoup nesnesi döndürür."""
    try:
        resp = scraper.get(BASE_URL + url if not url.startswith('http') else url, timeout=15)
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        print(f"    Hata (Get Soup): {e}")
        return None

def get_shows_from_category(scraper, category_url):
    """Kategori sayfasındaki dizi/program kartlarını bulur."""
    shows = []
    print(f"\n📂 Kategori Taranıyor: {category_url}")
    soup = get_soup(scraper, category_url)
    
    if not soup:
        return []

    # NOW TV genelde kartları 'el-item' veya genel 'a' etiketleri içinde resimle sunar
    # Geniş kapsamlı bir tarama yapalım
    links = soup.find_all('a', href=True)
    
    seen_slugs = set()

    for link in links:
        href = link['href']
        
        # Sadece dizi/program linklerini filtrele
        # Genellikle /dizi-adi veya /program-adi şeklindedir ve resim içerir
        img = link.find('img')
        
        if img and href.count('/') == 1 and len(href) > 2: # Basit slug kontrolü
            if href in seen_slugs: continue
            
            # Yasaklı kelimeler
            if any(x in href for x in ['yayin-akisi', 'canli-yayin', 'haber', 'iletisim', 'kunye']):
                continue

            title = img.get('alt') or img.get('title') or href.strip('/').replace('-', ' ').title()
            poster = img.get('data-src') or img.get('src') or ""
            
            seen_slugs.add(href)
            
            shows.append({
                "title": title.strip(),
                "url": href, # /kizil-goncalar gibi
                "poster": poster
            })
            
    print(f"  -> {len(shows)} içerik bulundu.")
    return shows

def get_episodes(scraper, show_url):
    """Dizinin bölümler sayfasındaki Select Box'tan linkleri çeker"""
    episodes = []
    # Bölümler sayfası genelde /dizi-adi/bolumler şeklindedir
    bolumler_url = f"{show_url}/bolumler"
    
    soup = get_soup(scraper, bolumler_url)
    if not soup: return []

    # Select box'ı bul (NOW TV yapısı)
    select_box = soup.find('select', id='video-finder-changer')
    
    if select_box:
        options = select_box.find_all('option', {'data-target': True})
        
        # Sayfadaki tüm m3u8 linklerini de önbelleğe alalım (Regex ile)
        # Bazen data-target bir HTML sayfasıdır, m3u8 o sayfanın içindedir.
        # Bazen de direkt m3u8 linkidir.
        
        for opt in options:
            ep_name = opt.get_text(strip=True)
            target_link = opt['data-target'] # Bu bazen m3u8, bazen izleme sayfası linkidir
            
            real_link = None
            
            # 1. Eğer link direkt m3u8 ise
            if ".m3u8" in target_link:
                real_link = target_link
            else:
                # 2. Değilse, o sayfaya gidip m3u8 ara (Deep Scan)
                # Ancak her bölüm için istek atmak yavaşlatır. 
                # NOW TV'de genelde data-target içindeki sayfa açılınca m3u8 regex ile bulunur.
                try:
                    # Hız optimizasyonu: Eğer çok bölüm varsa hepsine istek atma, sadece son 5'e at
                    # Veya hepsine at (uzun sürer). Şimdilik hepsini deneyelim.
                    real_link = get_m3u8_from_page(scraper, target_link)
                except:
                    pass
            
            if real_link:
                episodes.append({
                    "name": ep_name,
                    "url": real_link
                })
    
    return episodes

def get_m3u8_from_page(scraper, url):
    """Tekil video sayfasından m3u8 regex ile çeker"""
    try:
        # Url tam değilse tamamla
        full_url = BASE_URL + url if not url.startswith('http') else url
        r = scraper.get(full_url, timeout=5)
        
        # Regex: https://... .m3u8
        match = re.search(r'https?://[^\s"\'\\,]+\.m3u8[^\s"\'\\,]*', r.text)
        if match:
            return match.group(0).replace('\\/', '/')
    except:
        pass
    return None

def create_m3u(data):
    filename = "nowtv.m3u"
    print(f"\n📝 {filename} dosyası oluşturuluyor...")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for show in data:
            group = show['type']
            title = show['title']
            poster = show['poster']
            
            for ep in show['episodes']:
                ep_name = ep['name']
                link = ep['url']
                
                full_title = f"{title} - {ep_name}"
                
                # M3U Formatı
                f.write(f'#EXTINF:-1 group-title="{group}" tvg-logo="{poster}",{full_title}\n')
                f.write(f'{link}\n')
                
    print("✅ M3U Tamamlandı!")

def run_scraper():
    print("🚀 NOW TV Scraper Başlatıldı (M3U Modu)...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    final_data = []

    for target in TARGET_URLS:
        shows = get_shows_from_category(scraper, target['url'])
        
        for i, show in enumerate(shows):
            print(f"  📺 [{i+1}/{len(shows)}] İşleniyor: {show['title']}")
            
            episodes = get_episodes(scraper, show['url'])
            
            if episodes:
                # Bölümleri ekle
                final_data.append({
                    "title": show['title'],
                    "type": target['type'],
                    "poster": show['poster'],
                    "episodes": episodes
                })
                print(f"     + {len(episodes)} bölüm eklendi.")
            else:
                print(f"     - Bölüm bulunamadı.")
                
    create_m3u(final_data)

if __name__ == "__main__":
    run_scraper()
