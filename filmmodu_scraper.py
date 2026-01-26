import requests
from bs4 import BeautifulSoup
import re
import json
import time

# --- AYARLAR ---
BASE_URL = "https://www.filmmodu.ws"
ARCHIVE_URL = "https://www.filmmodu.ws/arsiv-filmler"
MAX_PAGES = 1  # Test için 1 sayfa. İstersen artırabilirsin.
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

def fetch_sources_from_api(session, movie_id, source_type, csrf_token):
    """
    API'den kaynakları yeni JSON formatına göre çeker.
    """
    api_url = f"{BASE_URL}/get-source"
    params = {
        "movie_id": movie_id,
        "type": source_type  # '' -> Dublaj, 'en' -> Altyazı
    }
    
    local_headers = HEADERS.copy()
    local_headers["X-CSRF-TOKEN"] = csrf_token

    try:
        response = session.get(api_url, params=params, headers=local_headers)
        if response.status_code == 200:
            try:
                data = response.json()
                
                # --- YENİ JSON YAPISINA GÖRE PARSE İŞLEMİ ---
                # "sources": [ {"src": "...", "label": "1080p"}, ... ]
                
                sources_list = data.get("sources", [])
                subtitle_path = data.get("subtitle")
                
                qualities = {}
                
                # Linkleri topla
                for item in sources_list:
                    label = item.get("label", "auto") # 1080p, 720p vs.
                    src = item.get("src")
                    if src:
                        qualities[label] = src

                # Altyazı linkini düzelt (Relative ise tam link yap)
                full_subtitle_url = None
                if subtitle_path:
                    if subtitle_path.startswith("http"):
                        full_subtitle_url = subtitle_path
                    else:
                        full_subtitle_url = BASE_URL + subtitle_path

                return qualities, full_subtitle_url
                
            except json.JSONDecodeError:
                print(f"JSON Decode Hatası (ID: {movie_id})")
                return None, None
    except Exception as e:
        print(f"API İstek Hatası (ID: {movie_id}): {e}")
    
    return None, None

def main():
    print(f"Fanatik Play Botu Başlatılıyor... Hedef: {MAX_PAGES} Sayfa")
    
    # Session başlat (Cookie'leri tutmak için önemli)
    session = requests.Session()
    session.headers.update(HEADERS)

    movies_data = []
    m3u_content = "#EXTM3U\n"
    
    for page in range(1, MAX_PAGES + 700):
        url = f"{ARCHIVE_URL}?page={page}"
        print(f"--- Sayfa {page} taranıyor: {url} ---")
        
        try:
            response = session.get(url)
            if response.status_code != 200:
                print(f"Sayfa {page} açılamadı.")
                continue
                
            soup = BeautifulSoup(response.content, "html.parser")
            csrf_token = get_csrf_token(soup)
            
            movie_divs = soup.select(".movie")
            if not movie_divs:
                print("Bu sayfada film bulunamadı.")
                break

            for div in movie_divs:
                try:
                    link_tag = div.find("a")
                    poster_tag = div.find("img")
                    
                    if not link_tag: continue
                    
                    page_url = link_tag.get("href")
                    if not page_url.startswith("http"):
                        page_url = BASE_URL + page_url
                        
                    title = div.select_one(".original-name").text.strip() if div.select_one(".original-name") else "İsimsiz"
                    tr_title = div.select_one(".turkish-name").text.strip() if div.select_one(".turkish-name") else ""
                    
                    # Poster URL Düzeltme
                    poster_url = poster_tag.get("data-src") or poster_tag.get("src")
                    if poster_url and "data:image" in poster_url:
                         poster_url = poster_tag.get("data-srcset") or poster_tag.get("srcset") or ""
                         poster_url = poster_url.split(" ")[0]

                    print(f" > {title} ({page_url}) işleniyor...")
                    
                    # Detay sayfasına girip ID alma
                    detail_res = session.get(page_url)
                    detail_soup = BeautifulSoup(detail_res.content, "html.parser")
                    script_content = str(detail_soup)
                    id_match = re.search(r"var videoId = '(\d+)';", script_content)
                    
                    if id_match:
                        movie_id = id_match.group(1)
                        movie_sources = []
                        
                        # --- 1. TÜRKÇE DUBLAJ (type='') ---
                        dub_qualities, _ = fetch_sources_from_api(session, movie_id, "", csrf_token)
                        if dub_qualities:
                            # En yüksek kaliteyi bul (M3U için)
                            best_quality_url = dub_qualities.get("1080p") or dub_qualities.get("720p") or dub_qualities.get("480p") or list(dub_qualities.values())[0]
                            
                            movie_sources.append({
                                "type": "TR Dublaj",
                                "qualities": dub_qualities
                            })
                            
                            # M3U Listesine Ekle
                            m3u_content += f'#EXTINF:-1 group-title="Filmler" tvg-logo="{poster_url}", {title} (TR Dublaj)\n'
                            m3u_content += f'{best_quality_url}\n'

                        # --- 2. TÜRKÇE ALTYAZILI (type='en') ---
                        sub_qualities, subtitle_url = fetch_sources_from_api(session, movie_id, "en", csrf_token)
                        if sub_qualities:
                            # En yüksek kaliteyi bul
                            best_quality_url = sub_qualities.get("1080p") or sub_qualities.get("720p") or sub_qualities.get("480p") or list(sub_qualities.values())[0]

                            source_entry = {
                                "type": "TR Altyazılı",
                                "qualities": sub_qualities
                            }
                            if subtitle_url:
                                source_entry["subtitle"] = subtitle_url
                            
                            movie_sources.append(source_entry)
                            
                            # M3U Listesine Ekle
                            m3u_content += f'#EXTINF:-1 group-title="Filmler" tvg-logo="{poster_url}", {title} (TR Altyazılı)\n'
                            m3u_content += f'{best_quality_url}\n'

                        # Eğer herhangi bir kaynak bulunduysa listeye ekle
                        if movie_sources:
                            movies_data.append({
                                "id": movie_id,
                                "title": title,
                                "tr_title": tr_title,
                                "poster": poster_url,
                                "sources": movie_sources
                            })
                        else:
                             print(f"   ! Kaynak bulunamadı (ID: {movie_id})")
                    
                    time.sleep(0.5) # Bekleme
                    
                except Exception as e:
                    print(f"Film işleme hatası: {e}")
                    continue
            
            time.sleep(1) # Sayfa beklemesi

        except Exception as e:
            print(f"Genel Hata: {e}")

    # Dosyaları Kaydet
    print(f"Toplam {len(movies_data)} film kaydediliyor...")
    
    with open("fanatik_movies.json", "w", encoding="utf-8") as f:
        json.dump(movies_data, f, ensure_ascii=False, indent=4)
        
    with open("fanatik_playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

    print("Tamamlandı.")

if __name__ == "__main__":
    main()
