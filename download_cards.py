"""
Laddar ner Rider-Waite tarotkort från Wikimedia Commons (public domain).
Kör: python download_cards.py
"""
import os, time, requests

SAVE_DIR = os.path.join("static", "images", "cards")
os.makedirs(SAVE_DIR, exist_ok=True)

WIKI_API = "https://commons.wikimedia.org/w/api.php"
HEADERS  = {"User-Agent": "JJUniverse-TarotApp/1.0 (educational project)"}

# Wikimedia Commons filnamn (verifierade)
CARD_FILES = {
    # Major Arcana — format: "RWS Tarot XX Name.jpg"
    "major_00.jpg": "RWS Tarot 00 Fool.jpg",
    "major_01.jpg": "RWS Tarot 01 Magician.jpg",
    "major_02.jpg": "RWS Tarot 02 High Priestess.jpg",
    "major_03.jpg": "RWS Tarot 03 Empress.jpg",
    "major_04.jpg": "RWS Tarot 04 Emperor.jpg",
    "major_05.jpg": "RWS Tarot 05 Hierophant.jpg",
    "major_06.jpg": "RWS Tarot 06 Lovers.jpg",
    "major_07.jpg": "RWS Tarot 07 Chariot.jpg",
    "major_08.jpg": "RWS Tarot 08 Strength.jpg",
    "major_09.jpg": "RWS Tarot 09 Hermit.jpg",
    "major_10.jpg": "RWS Tarot 10 Wheel of Fortune.jpg",
    "major_11.jpg": "RWS Tarot 11 Justice.jpg",
    "major_12.jpg": "RWS Tarot 12 Hanged Man.jpg",
    "major_13.jpg": "RWS Tarot 13 Death.jpg",
    "major_14.jpg": "RWS Tarot 14 Temperance.jpg",
    "major_15.jpg": "RWS Tarot 15 Devil.jpg",
    "major_16.jpg": "RWS Tarot 16 Tower.jpg",
    "major_17.jpg": "RWS Tarot 17 Star.jpg",
    "major_18.jpg": "RWS Tarot 18 Moon.jpg",
    "major_19.jpg": "RWS Tarot 19 Sun.jpg",
    "major_20.jpg": "RWS Tarot 20 Judgement.jpg",
    "major_21.jpg": "RWS Tarot 21 World.jpg",
    # Minor Arcana — format: "RWS1909 - Suit NN.jpeg"
    **{f"wands_{i:02d}.jpg":    f"RWS1909 - Wands {i:02d}.jpeg"    for i in range(1,15)},
    **{f"cups_{i:02d}.jpg":     f"RWS1909 - Cups {i:02d}.jpeg"     for i in range(1,15)},
    **{f"swords_{i:02d}.jpg":   f"RWS1909 - Swords {i:02d}.jpeg"   for i in range(1,15)},
    **{f"pentacles_{i:02d}.jpg":f"RWS1909 - Pentacles {i:02d}.jpeg" for i in range(1,15)},
}


def get_image_url(wiki_filename):
    params = {
        "action": "query", "titles": f"File:{wiki_filename}",
        "prop": "imageinfo", "iiprop": "url", "format": "json"
    }
    r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=15)
    for page in r.json().get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [])
        if info:
            return info[0]["url"]
    return None


def download_card(save_name, wiki_filename, attempt=1):
    save_path = os.path.join(SAVE_DIR, save_name)
    if os.path.exists(save_path):
        print(f"  ✓ Finns: {save_name}")
        return True

    print(f"  → {wiki_filename} ...", end=" ", flush=True)
    url = get_image_url(wiki_filename)
    if not url:
        print("❌ Hittades inte")
        return False

    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(r.content)
        print(f"✅ ({len(r.content)//1024}KB)")
        return True
    elif r.status_code == 429 and attempt <= 3:
        print(f"⏳ Väntar (försök {attempt}/3)...")
        time.sleep(5 * attempt)
        return download_card(save_name, wiki_filename, attempt + 1)
    else:
        print(f"❌ HTTP {r.status_code}")
        return False


if __name__ == "__main__":
    print(f"Laddar ner {len(CARD_FILES)} tarotkort till {SAVE_DIR}/\n")
    ok = fail = 0
    for i, (save_name, wiki_name) in enumerate(CARD_FILES.items()):
        if download_card(save_name, wiki_name):
            ok += 1
        else:
            fail += 1
        time.sleep(1.5)  # Schysst mot Wikimedia

    print(f"\n✅ Klart! {ok} nedladdade, {fail} misslyckades.")
    if fail:
        print("Kör skriptet igen för att försöka om de som misslyckades.")
