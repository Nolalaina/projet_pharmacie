from PIL import Image
import os

medicaments = ['Doliprane', 'Amoxil', 'Coartem', 'Vitamine C', 'Bétadine']
media_root = os.path.join('media', 'medicaments')

for name in medicaments:
    bmp_path = os.path.join(media_root, f'{name}.bmp')
    jpg_path = os.path.join(media_root, f'{name}.jpg')
    
    if os.path.exists(bmp_path):
        with Image.open(bmp_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(jpg_path, 'JPEG', quality=85)
        print(f'Converted: {name}.bmp -> {name}.jpg')
    else:
        print(f'Not found: {name}.bmp')

print('Conversion terminée !')