import json
import os
import datetime

# Klasör yoksa oluştur
if not os.path.exists('data'):
    os.makedirs('data')

def fetch_sports_data():
    """
    GERÇEK PROJEDE: Burada requests ve BeautifulSoup kullanarak 
    Maçkolik, Sofascore gibi yerlerden veri çekeceksin.
    Şu an API sisteminin sorunsuz çalışması için formatı hazırlıyoruz.
    """
    
    now = datetime.datetime.now().strftime("%H:%M")
    
    # Tüm sitenin besleneceği devasa JSON veritabanı
    db = {
        "football": {
            "leagues": ["Süper Lig", "Premier League", "La Liga"],
            "standings": {
                "Süper Lig": [
                    {"rank": 1, "team": "Galatasaray", "p": 38, "w": 33, "d": 3, "l": 2, "pts": 102},
                    {"rank": 2, "team": "Fenerbahçe", "p": 38, "w": 31, "d": 6, "l": 1, "pts": 99},
                    {"rank": 3, "team": "Trabzonspor", "p": 38, "w": 21, "d": 4, "l": 13, "pts": 67},
                    {"rank": 4, "team": "Başakşehir", "p": 38, "w": 18, "d": 7, "l": 13, "pts": 61}
                ]
            },
            "matches": [
                {"id": 1, "league": "Süper Lig", "home": "Galatasaray", "away": "Fenerbahçe", "scoreH": 2, "scoreA": 1, "status": "live", "time": "76'", "date": "Bugün", "isToday": True},
                {"id": 2, "league": "Premier League", "home": "Arsenal", "away": "Man City", "scoreH": 0, "scoreA": 0, "status": "live", "time": "12'", "date": "Bugün", "isToday": True},
                {"id": 3, "league": "Süper Lig", "home": "Beşiktaş", "away": "Trabzonspor", "scoreH": 1, "scoreA": 1, "status": "finished", "time": "MS", "date": "Dün", "isToday": False},
                {"id": 4, "league": "La Liga", "home": "Real Madrid", "away": "Barcelona", "scoreH": "-", "scoreA": "-", "status": "upcoming", "time": "22:00", "date": "Yarın", "isToday": False}
            ]
        },
        "basketball": {
            "leagues": ["NBA", "EuroLeague"],
            "standings": {
                "EuroLeague": [
                    {"rank": 1, "team": "Real Madrid", "p": 34, "w": 27, "d": 0, "l": 7, "pts": 54},
                    {"rank": 2, "team": "Panathinaikos", "p": 34, "w": 23, "d": 0, "l": 11, "pts": 46}
                ]
            },
            "matches": [
                {"id": 11, "league": "NBA", "home": "Lakers", "away": "Warriors", "scoreH": 105, "scoreA": 102, "status": "live", "time": "4. Çeyrek", "date": "Bugün", "isToday": True},
                {"id": 12, "league": "EuroLeague", "home": "Fenerbahçe", "away": "Olympiakos", "scoreH": 82, "scoreA": 78, "status": "finished", "time": "MS", "date": "Dün", "isToday": False}
            ]
        },
        "news": [
            {"id": 1, "tag": "ÖZEL HABER", "title": "Büyük Derbi Öncesi Kritik Gelişme", "summary": "Takımların son antrenmanlarında neler yaşandı?", "time": f"Bugün {now}"},
            {"id": 2, "tag": "ŞAMPİYONLAR LİGİ", "title": "Kura Çekimi Tamamlandı", "summary": "İşte dev eşleşmeler belli oldu.", "time": "2 Saat Önce"}
        ],
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # JSON dosyasına kaydet
    with open('data/db.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
        
    print("Veriler basariyla data/db.json dosyasina yazildi.")

if __name__ == "__main__":
    fetch_sports_data()