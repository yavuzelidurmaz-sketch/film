import requests
from bs4 import BeautifulSoup
import re
import json
import time

# --- AYARLAR ---
BASE_URL = "https://www.filmmodu.ws"
ARCHIVE_URL = "https://www.filmmodu.ws/arsiv-filmler"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": BASE_URL,
    "X-Requested-With": "XMLHttpRequest"
}

def get_csrf_token(soup):
    """HTML içindeki CSRF token'ı bulur."""
    token_tag = soup.find("meta", {"name": "csrf-token"})
    if token_tag:
        return token_tag.get("content")
    return ""

def parse_m3u8_qualities(master_url):
    """Master m3u8 linkinden alt kaliteleri (1080p, 720p vs) ayrıştırır."""
    qualities = {}
    try:
        response = requests.get(master_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            lines = response.text.split('\n')
            for i, line in enumerate(lines):
                if "#EXT-X-STREAM-INF" in line:
                    # Çözünürlük bilgisini çek (örn: RESOLUTION=1920x1080)
                    res_match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
                    if res_match:
                        height = res_match.group(2) + "p"
                        url = lines[i+1]
                        # Eğer URL relative ise domain ekle (Genelde tam link gelir ama önlem)
                        if not url.startswith("http"):
                            base_uri = master_url.rsplit('/', 1)[0]
                            url = f"{base_uri}/{url}"
                        qualities[height] = url
        
        # Eğer master m3u8 parse edilemezse veya tek dosya ise master'ı döndür
        if not qualities:
            qualities["auto"] = master_url
            
    except Exception as e:
        print(f"M3U8 Parse Hatası: {e}")
        qualities["auto"] = master_url
        
    return qualities

def get_movie_source(movie_id, source_type, csrf_token):
    """
    API'den kaynak linkini çeker.
    source_type: '' (Dublaj) veya 'en' (Altyazı)
    """
    api_url = f"{BASE_URL}/get-source"
    # User'ın belirttiği GET parametre yapısı veya POST yapısı denenebilir.
    # HTML kodunda POST kullanıldığı görülüyor, ancak URL parametresi de çalışabilir.
    # Burada en güvenilir yöntem parametreleri göndererek denemektir.
    
    params = {
        "movie_id": movie_id,
        "type": source_type
    }
    
    # Header'a CSRF token ekliyoruz
    local_headers = HEADERS.copy()
    local_headers["X-CSRF-TOKEN"] = csrf_token

    try:
        # Site yapısına göre bu POST isteği olabilir
        response = requests.get(api_url, params=params, headers=local_headers)
        if response.status_code == 200:
            try:
                data = response.json()
                # Data içinde 'src' veya 'file' anahtarı aranır
                video_url = data.get("src") or data.get("file")
                subs = data.get("tracks", [])
                
                # Altyazıları formatla
                subtitle_url = None
                for sub in subs:
                    if sub.get("kind") == "captions" or sub.get("label") == "Turkish":
                        subtitle_url = sub.get("file")
                        # Eğer relative link ise tamamla
                        if subtitle_url and not subtitle_url.startswith("http"):
                            subtitle_url = BASE_URL + subtitle_url
                        break
                        
                return video_url, subtitle_url
            except json.JSONDecodeError:
                return None, None
    except Exception as e:
        print(f"Kaynak çekme hatası ID {movie_id}: {e}")
    return None, None

def main():
    print("Fanatik Play için Filmmodu taranıyor...")
    
    # 1. Arşiv Sayfasını Çek
    response = requests.get(ARCHIVE_URL, headers=HEADERS)
    soup = BeautifulSoup(response.content, "html.parser")
    csrf_token = get_csrf_token(soup)
    
    movies_data = []
    m3u_content = "#EXTM3U\n"
    
    # 2. Filmleri Listele
    movie_divs = soup.select(".movie")
    
    for div in movie_divs:
        try:
            link_tag = div.find("a")
            poster_tag = div.find("img")
            
            if not link_tag: continue
            
            page_url = link_tag.get("href")
            # Link tam değilse tamamla
            if not page_url.startswith("http"):
                page_url = BASE_URL + page_url
                
            title = div.select_one(".original-name").text.strip() if div.select_one(".original-name") else "Bilinmeyen Film"
            tr_title = div.select_one(".turkish-name").text.strip() if div.select_one(".turkish-name") else ""
            poster_url = poster_tag.get("data-src") or poster_tag.get("src")
            
            # 3. Detay Sayfasına Git ve ID'yi al
            print(f"İşleniyor: {title}")
            detail_res = requests.get(page_url, headers=HEADERS)
            detail_soup = BeautifulSoup(detail_res.content, "html.parser")
            
            # Script içinden videoId'yi regex ile bul
            script_content = str(detail_soup)
            id_match = re.search(r"var videoId = '(\d+)';", script_content)
            
            if id_match:
                movie_id = id_match.group(1)
                
                # --- KAYNAKLARI KONTROL ET (Dublaj ve Altyazı) ---
                sources = []
                
                # 1. Türkçe Dublaj (type='')
                dub_url, _ = get_movie_source(movie_id, "", csrf_token)
                if dub_url and ".m3u8" in dub_url:
                    qualities = parse_m3u8_qualities(dub_url)
                    sources.append({
                        "type": "TR Dublaj",
                        "qualities": qualities,
                        "master": dub_url
                    })
                    
                    # M3U Ekleme
                    m3u_content += f'#EXTINF:-1 group-title="Filmler" tvg-logo="{poster_url}", {title} (TR Dublaj)\n'
                    m3u_content += f'{dub_url}\n'

                # 2. Türkçe Altyazılı (type='en')
                sub_video_url, sub_file_url = get_movie_source(movie_id, "en", csrf_token)
                if sub_video_url and ".m3u8" in sub_video_url:
                    qualities = parse_m3u8_qualities(sub_video_url)
                    
                    # Kullanıcı vtt linki istemiş, eğer API dönmezse manuel url oluşturma denenebilir
                    # Ancak en sağlıklısı API'den gelen track verisidir.
                    
                    sources.append({
                        "type": "TR Altyazılı",
                        "qualities": qualities,
                        "master": sub_video_url,
                        "subtitle": sub_file_url
                    })
                    
                    # M3U Ekleme
                    m3u_content += f'#EXTINF:-1 group-title="Filmler" tvg-logo="{poster_url}", {title} (TR Altyazılı)\n'
                    m3u_content += f'{sub_video_url}\n'

                if sources:
                    movies_data.append({
                        "id": movie_id,
                        "title": title,
                        "tr_title": tr_title,
                        "poster": poster_url,
                        "sources": sources
                    })
            
            time.sleep(1) # Siteye yüklenmemek için bekleme
            
        except Exception as e:
            print(f"Hata oluştu ({div}): {e}")
            continue

    # 4. Dosyaları Kaydet
    with open("fanatik_movies.json", "w", encoding="utf-8") as f:
        json.dump(movies_data, f, ensure_ascii=False, indent=4)
        
    with open("fanatik_playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print("İşlem tamamlandı. 'fanatik_movies.json' ve 'fanatik_playlist.m3u' oluşturuldu.")

if __name__ == "__main__":
    main()
