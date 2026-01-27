import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os

# Web sitesi kök adresi
BASE_URL = "https://www.startv.com.tr"
IMG_BASE_URL = "https://media.startv.com.tr/star-tv"
API_PATTERN = r'"apiUrl\\":\\"(.*?)\\"'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Yeniden deneme ayarları
MAX_RETRIES = 5
RETRY_DELAY = 2

def get_soup(url, retry_count=0):
    """URL'den BeautifulSoup nesnesi döndürür."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Timeout hatası! Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. URL atlanıyor: {url}")
            return None
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠ Hata: {e}. Yeniden deneniyor... ({retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            return get_soup(url, retry_count + 1)
        else:
            print(f"      ✗ Maksimum deneme sayısına ulaşıldı. Hata: {e}")
            return None

def slugify(text):
    """Metni ID olarak kullanılabilecek formata çevirir"""
    text = text.lower()
    text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def extract_episode_number(name):
    """Bölüm adından numarayı çeker (Sıralama için)."""
    match = re.search(r'(\d+)\.?\s*Bölüm', name, re.IGNORECASE)
    if match: return int(match.group(1))
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match: return int(match.group(1))
    match = re.search(r'\b(\d+)\b', name)
    if match: return int(match.group(1))
    return 9999

def extract_episode_number_only(name):
    """Bölüm adından sadece sayıyı çıkarır ve formatlar."""
    match = re.search(r'(\d+)\.\s*Bölüm', name, re.IGNORECASE)
    if match: return f"{match.group(1)}. Bölüm"
    match = re.search(r'Bölüm\s*(\d+)', name, re.IGNORECASE)
    if match: return f"{match.group(1)}. Bölüm"
    match = re.search(r'(\d+)\.\s*B[oö]l[üu]m', name, re.IGNORECASE)
    if match: return f"{match.group(1)}. Bölüm"
    match = re.search(r'\b(\d+)\b', name)
    if match: return f"{match.group(1)}. Bölüm"
    return name

def clean_image_url(url):
    """Resim URL'sini temizle"""
    if not url: return ""
    if "?" in url: url = url.split("?")[0]
    return url.strip()

def get_content_list(category):
    """Belirtilen kategorideki (dizi veya program) linkleri ve resimleri al"""
    print(f"\n--- {category.upper()} Listesi Taranıyor ---")
    url = f"{BASE_URL}/{category}"
    soup = get_soup(url)
    if not soup: return []

    content_list = []
    seen = set()
    
    # Kategoriye göre regex oluştur (örn: /dizi/ veya /program/)
    pattern = re.compile(rf'^/{category}/')
    links = soup.find_all("a", href=pattern)

    for link in links:
        href = link.get("href")
        if not href or href in seen: continue
        seen.add(href)

        item_name = "Bilinmeyen İçerik"
        img_tag = link.find("img")
        poster_url = ""

        if img_tag:
            if img_tag.get("alt") and img_tag.get("alt") != "alt":
                item_name = img_tag.get("alt").strip()
            if img_tag.get("src"): poster_url = img_tag.get("src")
            elif img_tag.get("data-src"): poster_url = img_tag.get("data-src")
            poster_url = clean_image_url(poster_url)

        if item_name == "Bilinmeyen İçerik":
            parts = href.split("/")
            if len(parts) >= 3:
                slug = parts[-2]
                item_name = slug.replace("-", " ").title()

        content_list.append({
            "name": item_name,
            "slug": href.split("/")[-2] if "/" in href else "",
            "url": BASE_URL + href,
            "detail_url": BASE_URL + href + "/bolumler",
            "poster": poster_url,
            "type": category.upper() # DİZİ veya PROGRAM etiketi için
        })
    print(f"{category.upper()} kategorisinde {len(content_list)} adet içerik bulundu.")
    return content_list

def get_api_url_from_page(url):
    """Sayfadan apiUrl al"""
    print(f"    [i] API URL aranıyor...")
    soup = get_soup(url)
    if not soup: return None
    page_content = str(soup)
    results = re.findall(API_PATTERN, page_content)
    if results:
        return results[0].replace('\\/', '/')
    return None

def get_episodes_from_api(api_path):
    """API'den bölümleri çek"""
    episodes = []
    api_params = {"sort": "episodeNo asc", "limit": "100"}
    skip = 0
    has_more = True
    url = BASE_URL + api_path

    while has_more:
        api_params["skip"] = skip
        try:
            print(f"    [i] API isteği yapılıyor (skip={skip})...")
            response = requests.get(url, params=api_params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])

            for item in items:
                heading = item.get("heading", "")
                title = item.get("title", "")
                if heading and title: name = f"{heading} {title}"
                elif title: name = title
                elif heading: name = heading
                else: name = "Bilinmeyen Bölüm"

                img = ""
                if item.get("image") and item["image"].get("fullPath"):
                    img = IMG_BASE_URL + item["image"]["fullPath"]
                    img = clean_image_url(img)

                stream_url = ""
                if "video" in item and item["video"].get("referenceId"):
                    stream_url = f'https://dygvideo.dygdigital.com/api/redirect?PublisherId=1&ReferenceId=StarTV_{item["video"]["referenceId"]}&SecretKey=NtvApiSecret2014*&.m3u8'

                if stream_url:
                    episodes.append({
                        "name": name,
                        "clean_name": extract_episode_number_only(name),
                        "img": img,
                        "link": stream_url,
                        "episode_num": extract_episode_number(name)
                    })

            if len(items) < 100: has_more = False
            else:
                skip += 100
                time.sleep(0.5)
        except Exception as e:
            print(f"    [✗] API hatası: {e}")
            has_more = False
    return episodes

def main():
    print("Star TV Tüm İçerik Taranıyor (M3U Modu)...")
    
    all_content = []
    
    # Hem DİZİ hem PROGRAM listelerini çekip birleştiriyoruz
    all_content.extend(get_content_list("dizi"))
    all_content.extend(get_content_list("program"))

    if not all_content:
        print("Hiç içerik bulunamadı!")
        return

    final_data = {}

    for idx, item in enumerate(all_content, 1):
        try:
            item_name = item["name"]
            item_id = slugify(item_name)
            
            print(f"\n[{idx}/{len(all_content)}] --> İşleniyor ({item['type']}): {item_name}")

            poster_url = item["poster"]
            # Eğer ana sayfada resim yoksa detay sayfasına bak
            if not poster_url:
                detail_soup = get_soup(item["url"])
                if detail_soup:
                    img_tag = detail_soup.find("img", src=re.compile(r'media\.startv\.com\.tr'))
                    if img_tag and img_tag.get("src"):
                        poster_url = clean_image_url(img_tag.get("src"))
                    elif detail_soup.find("meta", property="og:image"):
                        poster_url = clean_image_url(detail_soup.find("meta", property="og:image").get("content", ""))

            api_path = get_api_url_from_page(item["detail_url"])
            if not api_path:
                print(f"    [✗] API URL bulunamadı, atlanıyor.")
                continue

            episodes = get_episodes_from_api(api_path)

            if episodes:
                # Bölüm numarasına göre sırala
                episodes = sorted(episodes, key=lambda x: x['episode_num'])
                
                # Bölüm resmi kontrolü
                if not poster_url and episodes and episodes[0]["img"]:
                    poster_url = episodes[0]["img"]
                
                # Placeholder
                if not poster_url:
                    poster_url = "https://via.placeholder.com/300x450/15161a/ffffff?text=STAR+TV"

                final_data[item_id] = {
                    "title": item_name,
                    "resim": poster_url,
                    "bolumler": episodes,
                    "type": item['type']
                }
                print(f"    [✓] {len(episodes)} video eklendi.")
            else:
                print(f"    [✗] Hiç video bulunamadı.")

        except Exception as e:
            print(f"    [HATA] İçerik işlenirken hata: {e}")
            continue

    print("\n" + "="*50)
    print(f"Toplam {len(final_data)} içerik başarıyla işlendi!")
    print("="*50)

    create_m3u_file(final_data)

def create_m3u_file(data):
    """Verileri M3U formatına çevirip kaydeder."""
    filename = "startv.m3u"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for item_id, content in data.items():
            group_title = content['title']
            tvg_logo = content['resim']
            # Dilersen group-title'a "DİZİ" veya "PROGRAM" ekleyebilirsin, şu an başlığı kullanıyoruz.
            
            for bolum in content['bolumler']:
                bolum_adi = bolum['clean_name']
                link = bolum['link']
                
                # M3U satırını oluştur
                # Bölüm adını tam başlık ile birleştiriyoruz ki listede düzgün görünsün
                full_title = f"{group_title} - {bolum_adi}"
                
                f.write(f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{tvg_logo}",{full_title}\n')
                f.write(f'{link}\n')

    print(f"M3U dosyası '{filename}' oluşturuldu!")

if __name__ == "__main__":
    main()
