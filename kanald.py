import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import subprocess
import time

# Ayarlar
BASE_URL = "https://www.kanald.com.tr"
ARCHIVE_URL = "https://www.kanald.com.tr/diziler/arsiv?page="

def slugify(text):
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    text = text.lower()
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_real_m3u8(scraper, bolum_url):
    """M3U8 linkini bulma mantığı"""
    try:
        r1 = scraper.get(bolum_url, timeout=10)
        embed_match = re.search(r'<link[^>]+itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)
        if not embed_match: return bolum_url
        
        embed_url = embed_match.group(1)
        r2 = scraper.get(embed_url, timeout=10, headers={"Referer": BASE_URL})
        embed_html = r2.text
        
        patterns = [
            r'https?://vod[0-9]*\.cf\.dmcdn\.net/[^\s"\']+\.m3u8',
            r'https?://[^\s"\']+\.m3u8',
            r'["\']videoUrl["\']\s*:\s*["\']([^"\']+)["\']',
            r'src=["\']([^"\']+\.m3u8)["\']'
        ]
        
        for p in patterns:
            m = re.search(p, embed_html)
            if m:
                found_url = m.group(1) if "(" in p else m.group(0)
                return found_url.replace('\\/', '/')
        return embed_url
    except:
        return bolum_url

def commit_and_push(files):
    """Dosyaları GitHub'a yükler"""
    print(f"\n📤 Dosyalar GitHub'a gönderiliyor: {files}")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        
        for f in files:
            subprocess.run(["git", "add", f], check=True)
            
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout:
            subprocess.run(["git", "commit", "-m", "🔄 Kanal D Playlist Güncellendi (JSON & M3U)"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 GitHub'a yüklendi!")
        else:
            print("✨ Değişiklik yok, yükleme yapılmadı.")
    except Exception as e: print(f"❌ Git Hatası: {e}")

def create_outputs(series_data):
    files_to_push = []

    # 1. JSON OLUŞTURMA
    json_filename = "kanald.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(series_data, f, indent=4, ensure_ascii=False)
    files_to_push.append(json_filename)
    print(f"✅ {json_filename} oluşturuldu. Toplam Dizi: {len(series_data)}")

    # 2. M3U OLUŞTURMA
    m3u_filename = "kanald.m3u"
    with open(m3u_filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for dizi_id, data in series_data.items():
            dizi_adi = dizi_id.replace("-", " ").title()
            resim = data.get("resim", "")
            
            for bolum in data['bolumler']:
                baslik = bolum['ad']
                link = bolum['link']
                f.write(f'#EXTINF:-1 group-title="{dizi_adi}" tvg-logo="{resim}", {baslik}\n')
                f.write(f'{link}\n')
                
    files_to_push.append(m3u_filename)
    print(f"✅ {m3u_filename} oluşturuldu.")

    commit_and_push(files_to_push)

def run_scraper():
    print("🚀 Kanal D Scraper Başlatıldı (Gelişmiş Mod)...")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    series_data = {}

    # Sayfa sayısını artırabilirsin (1, 11) gibi
    for page in range(1, 6): 
        print(f"\n📄 Sayfa {page} taranıyor...")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.select('a.poster-card, .card-item, .item') # Ana liste seçicileri
            
            if not cards: 
                print("⚠️ Bu sayfada dizi bulunamadı.")
                break

            for card in cards:
                title_tag = card.get('title') or card.find('img').get('alt') if card.find('img') else None
                if not title_tag: continue
                
                title = str(title_tag)
                href = card.get('href')
                dizi_id = slugify(title)

                full_url = BASE_URL + href if href.startswith('/') else href
                print(f"  📺 {title} kontrol ediliyor...")

                # Bölüm sayfasına git
                b_url_main = full_url.rstrip('/') + "/bolumler"
                b_resp = scraper.get(b_url_main)
                b_soup = BeautifulSoup(b_resp.text, 'html.parser')

                # PLAN A: Standart Kartlar
                b_cards = b_soup.select('.story-card, .content-card, .video-card, .media-block, .card-item')
                
                # PLAN B: Eğer standart kart yoksa, tüm linkleri tara
                if not b_cards:
                    all_links = b_soup.find_all('a', href=True)
                    # İçinde 'bolum' geçen ve 'fragman' olmayan linkleri al
                    b_cards = [
                        a for a in all_links 
                        if '/bolum/' in a['href'] 
                        and ('izle' in a['href'] or 'bolum' in a.get_text().lower())
                        and 'fragman' not in a['href']
                    ]
                    # Tekrar edenleri temizle (set kullanarak)
                    seen = set()
                    unique_cards = []
                    for c in b_cards:
                        h = c['href']
                        if h not in seen:
                            seen.add(h)
                            unique_cards.append(c)
                    b_cards = unique_cards

                print(f"    🔎 {len(b_cards)} adet bölüm bulundu.")

                eps = []
                for bc in b_cards[:10]: # Her diziden son 10 bölüm
                    link_tag = bc if bc.name == 'a' else bc.find('a', href=True)
                    
                    # İsim bulmaya çalış
                    name_tag = bc.select_one('.title, h3, h2, .description') 
                    name_text = name_tag.get_text(strip=True) if name_tag else ""
                    
                    # Eğer isim yoksa linkin title'ına bak veya link metnini al
                    if not name_text and link_tag:
                        name_text = link_tag.get('title') or link_tag.get_text(strip=True)

                    if link_tag:
                        target_url = BASE_URL + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
                        m3u8_link = get_real_m3u8(scraper, target_url)
                        
                        # Bölüm adını temizle
                        clean_name = f"{title} - {name_text}" if title not in name_text else name_text
                        
                        eps.append({"ad": clean_name, "link": m3u8_link})

                if eps:
                    img = card.find('img')
                    poster = img.get('data-src') or img.get('src', '') if img else ""
                    series_data[dizi_id] = {"resim": poster, "bolumler": eps[::-1]}

        except Exception as e:
            print(f"❌ Hata: {e}")
            continue

    if series_data:
        create_outputs(series_data)
    else:
        print("\n⚠️ Hiçbir veri çekilemedi. Seçicileri veya site yapısını kontrol et.")

if __name__ == "__main__":
    run_scraper()
