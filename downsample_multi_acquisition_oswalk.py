from pathlib import Path
import shutil
import os
import numpy as np
import skimage
from skimage import io

# from PIL import Image, TiffTags
import tifffile as tiff

# %%
# get user input for source and dest
src, trg = '', ''
while src==trg:
    src = os.path.normpath(input("Enter the Parent folder for original images: "))
    trg = os.path.normpath(input("Enter the Destination folder: "))
    if src==trg:
        print('Source and Target cannot be same location. Re-Enter..')

# print(f"Source Dir: {src}")
# print(f"Target Dir: {trg}")
# flag = input("Continue? (y/n):")
# if flag.casefold() != "y":
#     exit()

# n is the downscaling factor in x and y, change it accordingly.
n = (
    input("Enter downscaling factor for x and y dimensions (default=4):")
    or 4
)
if type(n)!=int or n<=0:
    print("User Error: downscaling factor MUST be a positive integer. Exiting")
    exit()

# single_fish_flag is used to find if single acquisitions have single fish or not
single_fish_flag = input("Is there ONLY 1 fish per Acquisition? (y-default/n):") or "y"
if single_fish_flag.casefold() not in ('y', 'n'):
    print("User Error: Need to enter 'y' or 'n'. Exiting")
    exit()

# %%
def read_n_downscale_image(read_path):
    print(f"Reading: {read_path}")
    img = tiff.imread(read_path)
    print(f"Shape of read image {img.shape}")
    if len(img.shape) == 2:  # 2 dimensional image, e.g. BF image
        # use a kernel of nxn, ds by a factor of n in x & y
        img_downscaled = skimage.transform.downscale_local_mean(img, (n, n))
    elif len(img.shape) == 3:  # image zstack
        # use a kernel of 1xnxn, no ds in z
        img_downscaled = skimage.transform.downscale_local_mean(img, (1, n, n))
    else:
        print("Can't process images with >3dimensions")
        return None
    
    return skimage.util.img_as_uint(
        skimage.exposure.rescale_intensity(img_downscaled)
        )

# %%
new_folder_name = os.path.split(src)[-1] + "_downsampled"
trg_path = os.path.join(trg, new_folder_name)
os.mkdir(trg_path)
print(f"Made dir: {trg_path}")

# %%
def single_acquisition_downsample(acq_path, new_trg_path):

# Assuming the acq_path has the acquisition dir:
# acq_path = Acquisition dir -> {fish1 dir, fish2 dir, etc.} + notes.txt
    files = os.listdir(acq_path)
    for filename in files:
        filename_list = filename.split(".")
        og_name = filename_list[0]  #first of list=name
        ext = filename_list[-1]  #last of list=extension
        if ext == "txt":  #copy text files
            shutil.copy(os.path.join(acq_path, filename), new_trg_path)
            print(f"copied file: {filename}")
        elif(single_fish_flag.casefold()=='n'):  #make fish num folders
            os.mkdir(os.path.join(new_trg_path, filename))
            print(f"made dir: {filename}")

    for root, subfolders, filenames in os.walk(acq_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            filename_list = filename.split(".")
            og_name = filename_list[0]  # first of list=name
            ext = filename_list[-1]  # last of list=extension

            if (ext == "tif" or ext == "tiff"):  # only compress tiff files
                if single_fish_flag.casefold()=='n':  # save the ds images in fish folder
                    fish_num = og_name[og_name.casefold().find("fish") + len("fish")]
                    save_path = os.path.join(new_trg_path, "fish" + str(fish_num))
                else:
                    save_path = new_trg_path

                if og_name.endswith("_MMStack"):  # remove 'MMStack' in saved name
                    save_name = og_name[: -len("_MMStack")] + "_ds." + ext
                else:
                    save_name = og_name + "_ds." + ext
                tiff.imwrite(
                    os.path.join(save_path, save_name),
                    read_n_downscale_image(read_path=filepath),
                )
# %%
#oswalk to find all acquisition folders
for root, subfolders, filenames in os.walk(src):
    # print(subfolders)
    for sub in subfolders: #separate by acquisitions
        if 'acquisition' in sub.casefold(): 
            single_acq_path = os.path.join(root,sub)
            single_trg_path = root.replace(src, trg_path)

            #copy entire folder structure
            path = Path(single_trg_path)
            path.mkdir(parents=True, exist_ok=True)

            single_acquisition_downsample(single_acq_path, single_trg_path)
