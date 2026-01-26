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
    text = str(text).lower() # String olduğundan emin ol
    mapping = {'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','İ':'i'}
    for tr, en in mapping.items(): text = text.replace(tr, en)
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')

def get_real_m3u8(scraper, bolum_url):
    try:
        r1 = scraper.get(bolum_url, timeout=10)
        # Embed URL'yi daha geniş bir regex ile ara
        embed_match = re.search(r'embedURL["\']\s*:\s*["\']([^"\']+)["\']', r1.text) or \
                      re.search(r'itemprop=["\']embedURL["\'][^>]+href=["\']([^"\']+)["\']', r1.text)

        if not embed_match: return bolum_url
        
        embed_url = embed_match.group(1).replace('\\/', '/')
        r2 = scraper.get(embed_url, timeout=10, headers={"Referer": BASE_URL})
        embed_html = r2.text
        
        patterns = [
            r'src=["\']([^"\']+\.m3u8[^"\']*)["\']', # Geniş M3U8 arama
            r'file["\']\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'["\']videoUrl["\']\s*:\s*["\']([^"\']+)["\']'
        ]
        
        for p in patterns:
            m = re.search(p, embed_html)
            if m:
                return m.group(1).replace('\\/', '/')
        return embed_url
    except:
        return bolum_url

def commit_and_push(files):
    print(f"\n📤 Dosyalar GitHub'a gönderiliyor...")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        for f in files: subprocess.run(["git", "add", f], check=True)
        # Değişiklik varsa commit at
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout:
            subprocess.run(["git", "commit", "-m", "Veriler Güncellendi"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 Başarıyla Yüklendi!")
    except Exception as e: print(f"Git Hatası (Önemli Değil): {e}")

def create_outputs(series_data):
    if not series_data:
        print("❌ HİÇ VERİ BULUNAMADI! Dosya oluşturulmuyor.")
        return

    # JSON Kaydet
    with open("kanald.json", "w", encoding="utf-8") as f:
        json.dump(series_data, f, indent=4, ensure_ascii=False)
    
    # M3U Kaydet
    with open("kanald.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for dizi_id, data in series_data.items():
            dizi_adi = dizi_id.replace("-", " ").title()
            resim = data.get("resim", "")
            for bolum in data['bolumler']:
                f.write(f'#EXTINF:-1 group-title="{dizi_adi}" tvg-logo="{resim}", {bolum["ad"]}\n')
                f.write(f'{bolum["link"]}\n')

    print(f"✅ {len(series_data)} adet dizi için dosyalar oluşturuldu.")
    commit_and_push(["kanald.json", "kanald.m3u"])

def run_scraper():
    print("🚀 Kanal D Scraper Başlatıldı (Fix Versiyon)...")
    scraper = cloudscraper.create_scraper()
    series_data = {}

    for page in range(1, 6): # İlk 5 sayfa
        print(f"\n📄 Sayfa {page} taranıyor...")
        try:
            resp = scraper.get(f"{ARCHIVE_URL}{page}", timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # HATA DUZELTME 1: Daha genel seçim yap ve linki olmayanları atla
            cards = soup.select('a.poster-card, .card-item a, .item a')
            
            for card in cards:
                href = card.get('href')
                # HATA DUZELTME 2: Eğer href None ise (boşsa) döngüyü pas geç, çökme!
                if not href: continue 
                
                title = card.get('title') or card.get_text(strip=True)
                if not title: continue

                dizi_id = slugify(title)
                full_url = BASE_URL + href if href.startswith('/') else href
                
                print(f"  📺 {title} kontrol ediliyor...")

                # Bölüm sayfasına git
                try:
                    # Bazı dizilerde /bolumler sayfası yok, direkt ana sayfayı tara
                    b_url = full_url.rstrip('/') + "/bolumler"
                    b_resp = scraper.get(b_url)
                    if b_resp.status_code == 404: # Eğer bölümler sayfası yoksa ana sayfaya dön
                        b_url = full_url
                        b_resp = scraper.get(b_url)
                    
                    b_soup = BeautifulSoup(b_resp.text, 'html.parser')
                    
                    # HATA DUZELTME 3: CSS sınıfı arama! İçinde 'bolum' geçen tüm linkleri bul
                    all_links = b_soup.find_all('a', href=True)
                    episode_links = []
                    
                    for a in all_links:
                        link = a['href']
                        text = a.get_text(strip=True).lower()
                        # Linkin içinde 'bolum' geçiyorsa VE 'fragman' geçmiyorsa al
                        if '/bolum/' in link and 'fragman' not in link:
                            # Tekrarı önlemek için kontrol
                            if link not in [x['href'] for x in episode_links]:
                                episode_links.append(a)

                    eps = []
                    # İlk 5 bölümü al (Hızlı olsun diye)
                    for link_tag in episode_links[:5]:
                        ep_url = BASE_URL + link_tag['href'] if link_tag['href'].startswith('/') else link_tag['href']
                        ep_name = link_tag.get('title') or link_tag.get_text(strip=True)
                        
                        # Eğer isim çok kısaysa (örn: "İzle") dizi adını ekle
                        if len(ep_name) < 5: ep_name = f"{title} - Bölüm"

                        print(f"    found: {ep_name[:15]}...")
                        m3u8 = get_real_m3u8(scraper, ep_url)
                        eps.append({"ad": ep_name, "link": m3u8})

                    if eps:
                        img_tag = card.find('img')
                        poster = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                        series_data[dizi_id] = {"resim": poster, "bolumler": eps}
                        print(f"    ✅ {len(eps)} bölüm eklendi.")
                    else:
                        print("    ⚠️ Bölüm bulunamadı.")

                except Exception as inner_e:
                    print(f"    Dizi hatası: {inner_e}")
                    continue

        except Exception as e:
            print(f"❌ Sayfa Hatası: {e}")
            continue

    create_outputs(series_data)

if __name__ == "__main__":
    run_scraper()
