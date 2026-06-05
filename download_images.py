import os
import urllib.request
import time

# Create assets/images directory if it doesn't exist
os.makedirs("assets/images", exist_ok=True)

# Mapping of all 78 vocabulary words to their CDN sources
# Emojis are U+ hex strings (Twemoji CDN)
# Special items are prefixed with material_ or wikimedia_
word_image_sources = {
    # Aa
    "apple": "1f34e",
    "ant": "1f41c",
    "axe": "1fa93",
    # Bb
    "ball": "26bd",
    "bee": "1f41d",
    "book": "1f4d6",
    # Cc
    "car": "1f697",
    "cat": "1f431",
    "cow": "1f42e",
    # Dd
    "duck": "1f986",
    "dog": "1f436",
    "drum": "1f941",
    # Ee
    "elephant": "1f418",
    "egg": "1f95a",
    "ear": "1f442",
    # Ff
    "flag": "1f6a9",
    "fish": "1f41f",
    "fox": "1f98a",
    # Gg
    "gift": "1f381",
    "goat": "1f410",
    "glass": "1f95b",
    # Hh
    "hand": "270b",
    "hen": "1f414",
    "hair": "1f487",
    # Ii
    "ice cream": "1f366",
    "iron": "material_places_iron",
    "insect": "1f41b",
    # Jj
    "jam": "1f36f",
    "jacket": "1f9e5",
    "juice": "1f9c3",
    # Kk
    "key": "1f511",
    "king": "1f451",
    "kite": "1fa81",
    # Ll
    "lemon": "1f34b",
    "lion": "1f981",
    "leg": "1f9b5",
    # Mm
    "monkey": "1f412",
    "man": "1f468",
    "moon": "1f319",
    # Nn
    "nose": "1f443",
    "nurse": "1f469-200d-2695-fe0f",
    "nest": "1fab0",
    # Oo
    "orange": "1f34a",
    "oil": "1f6e2",
    "olives": "1fad2",
    # Pp
    "plane": "2708",
    "pen": "1f58a",
    "pencil": "270f",
    # Qq
    "queen": "1f478",
    "quarter": "1fa99",
    "quiet": "1f92b",
    # Rr
    "ruler": "1f4cf",
    "rabbit": "1f430",
    "ring": "1f48d",
    # Ss
    "sun": "2600",
    "snake": "1f40d",
    "star": "2b50",
    # Tt
    "tree": "1f333",
    "table": "material_search_table_restaurant",
    "train": "1f682",
    # Uu
    "umbrella": "2602",
    "up": "2b06",
    "uncle": "1f468",
    # Vv
    "vegetable": "1f966",
    "violin": "1f3bb",
    "vase": "1f3fa",
    # Ww
    "watermelon": "1f349",
    "window": "1fa9f",
    "watch": "231a",
    # Xx
    "x-ray": "1fa7b",
    "xylophone": "wikimedia_xylophone",
    "box": "1f4e6",
    # Yy
    "yellow": "1f7e1",
    "yoyo": "1fa80",
    "yacht": "26f5",
    # Zz
    "zoo": "1f981",
    "zebra": "1f993",
    "zipper": "1f910"
}

def download_file(url, output_path):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r:
            with open(output_path, "wb") as f:
                f.write(r.read())
        print(f"  [SUCCESS] Downloaded {os.path.basename(output_path)}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to download {url}: {e}")
        return False

def main():
    print("Starting download of 78 vector SVG clipart files...")
    success_count = 0
    
    for word, source in word_image_sources.items():
        # Sanitize filename (replace spaces with underscores)
        filename = f"{word.replace(' ', '_')}.svg"
        output_path = os.path.join("assets/images", filename)
        
        # Build download URL
        if source.startswith("material_"):
            parts = source.split("_")
            cat = parts[1]
            name = "_".join(parts[2:])
            url = f"https://raw.githubusercontent.com/google/material-design-icons/master/src/{cat}/{name}/materialicons/24px.svg"
        elif source == "wikimedia_xylophone":
            url = "https://upload.wikimedia.org/wikipedia/commons/c/cc/Xylophone_(colourful).svg"
        else:
            # Google Noto Color Emoji SVG URL (with hyphen to underscore fallback for compound emojis, stripping variation selector fe0f)
            source_clean = source.replace("-", "_").replace("_fe0f", "").replace("_fe0f".upper(), "")
            url = f"https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u{source_clean}.svg"
            
        print(f"Downloading '{word}' from {url}...")
        if download_file(url, output_path):
            success_count += 1
            
        # Add small delay to be friendly to CDNs
        time.sleep(0.1)
        
    print(f"\nDownload Complete! Successfully downloaded {success_count} / {len(word_image_sources)} images.")

if __name__ == "__main__":
    main()
