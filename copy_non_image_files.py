# Simple code to copy non-image files while preserving the folder structure

import os
import shutil

src, trg = "", ""
while src == trg:
    src = os.path.normpath(input("Enter Source folder containing images and other files: "))
    trg = os.path.normpath(input("Enter Destination folder: "))
    if src == trg:
        print("Source and Target cannot be same location. Re-Enter..")

new_folder_name = os.path.split(src)[-1] + "_non_img_files"
new_trg_path = os.path.join(trg, new_folder_name)
if not os.path.exists(new_trg_path):
    os.mkdir(new_trg_path)
    print(f"made dir: {new_trg_path}")

# e.g. formats: ND2 for Nikon, LIF or SCN for Leica, OIB or OIF for Olympus, CZI, LSM or ZVI for Zeiss
img_ext = [
    "tmp*",
    "*.tif",
    "*.tiff",
    "*.ome",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.nd2",
    "*.lif",
    "*.scn",
    "*.oib",
    "*.oif",
    "*.czi",
    "*.lsm",
    "*.zvi",
]
# copy all files except the tiff image files
shutil.copytree(src, new_trg_path, ignore=shutil.ignore_patterns(*img_ext))
print(
    f"Success: Directory structure and all non-image files copied from \
    \nsource:{src} to \ndestination:{new_trg_path}"
)
