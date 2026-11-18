import urllib.request
import json
import os
import io
from PIL import Image

HEADERS = {'User-Agent': 'PharmaGest/1.0 (contact@pharmagest.mg)'}

medicines = [
    ("advil.jpg", ["Advil box", "Advil", "Ibuprofen box", "Ibuprofen"]),
    ("efferalgan.jpg", ["Efferalgan", "Paracetamol effervescent", "Doliprane", "Paracetamol box"]),
    ("augmentin.jpg", ["Augmentin", "Amoxicillin clavulanate", "Amoxicillin"]),
    ("zithromax.jpg", ["Zithromax", "Azithromycin", "Azithromycin 250"]),
    ("mopral.jpg", ["Omeprazole box", "Omeprazole", "Mopral"]),
    ("spasfon.jpg", ["Spasfon", "Phloroglucinol", "Antispasmodic medicine"]),
    ("smecta.jpg", ["Smecta", "Diosmectite", "Antidiarrheal medicine"]),
    ("gaviscon.jpg", ["Gaviscon", "Antacid suspension"]),
    ("ventoline.jpg", ["Ventolin inhaler", "Salbutamol inhaler", "Ventolin", "Salbutamol"]),
    ("zyrtec.jpg", ["Zyrtec", "Cetirizine box", "Cetirizine"]),
    ("amlor.jpg", ["Amlor", "Norvasc", "Amlodipine box", "Amlodipine"]),
    ("glucophage.jpg", ["Glucophage", "Metformin box", "Metformin"]),
    ("bepanthene.jpg", ["Bepanthen", "Bepanthene", "Dexpanthenol cream"]),
    ("biprofenid.jpg", ["Biprofenid", "Ketoprofen box", "Ketoprofen"]),
    ("daflon.jpg", ["Daflon", "Flavonoid medicine", "Phlebotonic"]),
]

os.makedirs("media/medicaments", exist_ok=True)

def find_wikimedia_image(query):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(query)}&gsrlimit=5"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            data = json.loads(resp.read().decode())
        pages = data.get('query', {}).get('pages', {})
        candidates = []
        for pid, pdata in pages.items():
            title = pdata.get('title', '')
            # Filter out icons, svgs, maps
            if any(ext in title.lower() for ext in ['.jpg', '.jpeg', '.png']):
                if not any(bad in title.lower() for bad in ['map', 'flag', 'logo', 'icon', 'diagram', 'chemical']):
                    candidates.append(title)
        
        for cand in candidates:
            info_url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url&titles={urllib.parse.quote(cand)}"
            req2 = urllib.request.Request(info_url, headers=HEADERS)
            with urllib.request.urlopen(req2, timeout=7) as resp2:
                d2 = json.loads(resp2.read().decode())
            p2 = d2.get('query', {}).get('pages', {})
            for _, pd in p2.items():
                ii = pd.get('imageinfo', [])
                if ii and 'url' in ii[0]:
                    return ii[0]['url'], cand
    except Exception as e:
        print(f"  Search error for '{query}': {e}")
    return None, None

def download_and_crop(img_url, dest_path):
    req = urllib.request.Request(img_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read()
    
    im = Image.open(io.BytesIO(data))
    if im.mode != 'RGB':
        im = im.convert('RGB')
    
    # Resize keeping aspect ratio or center crop to 400x300
    target_w, target_h = 400, 300
    w, h = im.size
    
    # Calculate crop
    target_ratio = target_w / target_h
    current_ratio = w / h
    
    if current_ratio > target_ratio:
        # Too wide, crop width
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        im_cropped = im.crop((left, 0, left + new_w, h))
    else:
        # Too tall, crop height
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        im_cropped = im.crop((0, top, w, top + new_h))
        
    im_resized = im_cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    im_resized.save(dest_path, "JPEG", quality=90)
    return True

print("Démarrage du téléchargement des vraies photos de médicaments...")
for filename, queries in medicines:
    dest = os.path.join("media/medicaments", filename)
    downloaded = False
    for q in queries:
        img_url, title = find_wikimedia_image(q)
        if img_url:
            print(f"-> Trouvé pour '{filename}' avec query '{q}': {title}")
            try:
                download_and_crop(img_url, dest)
                print(f"   ✅ Téléchargé et calibré: {dest}")
                downloaded = True
                break
            except Exception as e:
                print(f"   Erreur download: {e}")
    if not downloaded:
        print(f"   ⚠️ Aucune image Wikimedia trouvée pour {filename}")

print("\nTerminé !")

