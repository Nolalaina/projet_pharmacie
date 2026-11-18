from PIL import Image

im = Image.open(r'd:\Licence3\Framework_python\Projet_pharmacie\extracted_media\word\media\image5.jpeg')
# Crop the table header and first two rows
# Size is (1200, 750)
table_crop = im.crop((30, 220, 1170, 480))
table_crop.save(r'd:\Licence3\Framework_python\Projet_pharmacie\table_crop.png')
print("Saved table_crop.png")

