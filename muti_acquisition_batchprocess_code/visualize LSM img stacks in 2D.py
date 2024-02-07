# %% [markdown]
# Author(s): Piyush Amitabh
#
# Details: this code generates mip and stitches them to visualize the img stacks
#
# Created: May 02, 2023
#
# License: GNU GPL v3.0

# %% [markdown]
# Comment: it is scope agnostic (KLA/WIL LSM) and os agnostic

# %% [markdown]
# Updated: 29 Sep, 23
#
# Detail: now this works with multi folder/multi acquisition

import configparser

import os
import re

import batchprocessing_functions_v2 as bpf
import numpy as np

import skimage

import tifffile as tiff
from natsort import natsorted

from tqdm import tqdm

# import pandas as pd
# import matplotlib.pyplot as plt

top_dir = os.path.normpath(input("Enter the top directory with ALL acquisitions: "))
action_flag = 0

while action_flag == 0:
    action_flag = int(
        input(
            """Do you want to:
                        1. Find Max Intensity Projection AND Stitch (default)
                        2. Only find Max Intensity Projection
                        3. Only Stitch\n"""
        )
        or "1"
    )
    if action_flag == 1 or action_flag == 2 or action_flag == 3:
        break
    else:
        action_flag = 0
        print("Invalid value: Re-Enter")

if action_flag != 2:  # more info for stitching
    print(
        """Instructions for stitching:
        - Image stitching works by reading stage positions from the 'notes.txt' file generated during acquisition
        - Images MUST have:
            a. 'timepoint' substring in their names
            b. 'pos' or 'region' substring in their names
            c. channel substring(BF/GFP/RFP) in their names"""
    )

    user_check = input("Do you want to continue? (y/[n])") or "n"
    if user_check.casefold() == "n":
        print("Okay, bye!")
        exit()

#     # all unique BF location gets added to the main_dir_list
#     main_dir_list = []
#     for root, subfolders, _ in os.walk(top_dir):
#         if "BF" in subfolders:
#             main_dir_list.append(root)
#     print(f"Found these fish data:\n{main_dir_list}")
#     pos_input_flag = input("Is the number of pos/regions in each folder above the same? (y-default/n)") or "y"
#     if pos_input_flag.casefold() == "y":
#         pos_max_list = len(main_dir_list) * [
#             int(input("Enter number of positions/regions of imaging per timepoint (default=4)") or "4")
#         ]
#     else:
#         pos_max_list = []
#         while len(pos_max_list) != len(main_dir_list):
#             pos_max_list = (input("Enter the list of positions/regions separated by space in the above order")).split()
#             if len(pos_max_list) != len(main_dir_list):
#                 print("entered list length is not same as the number of folders found above. Please re-enter.")
#                 continue
#             else:
#                 # convert each item to int type
#                 for i in range(len(pos_max_list)):
#                     pos_max_list[i] = int(pos_max_list[i])

# %%
if action_flag != 3:
    bpf.batchprocess_mip(main_dir=top_dir)

# # Stitching
if action_flag == 2:  # don't stitch and exit
    exit()

## Stitching
# all unique BF/GFP/RFP location gets added to the main_dir_list
main_dir_list = []
for root, subfolders, _ in os.walk(top_dir):
    if ("BF" in subfolders) or ("GFP" in subfolders) or ("RFP" in subfolders):
        main_dir_list.append(root)
main_dir_list = natsorted(main_dir_list)
print(f"Found these fish data:\n{main_dir_list}")

ch_names = ["BF", "GFP_mip", "RFP_mip"]

for main_dir in main_dir_list:  # main_dir = location of Directory containing ONE fish data
    print(f"Processing {main_dir}...")
    ch_2Dimg_flags, ch_2Dimg_paths, ch_2Dimg_lists = bpf.find_2D_images(main_dir)
    stage_coords = bpf.find_stage_coords_n_pixel_width_from_2D_images(ch_2Dimg_flags, ch_2Dimg_paths, ch_2Dimg_lists)
    global_coords_px = bpf.global_coordinate_changer(stage_coords)

    for ch_name, ch_2Dimg_flag, ch_2Dimg_path, ch_2Dimg_list in zip(
        ch_names, ch_2Dimg_flags, ch_2Dimg_paths, ch_2Dimg_lists
    ):
        if ch_2Dimg_flag:
            pos_max = bpf.pos_max
            print(f"Stitching {ch_name} images...")
            save_path = os.path.join(ch_2Dimg_path, f"{ch_name.casefold()}_stitched")
            save_path_bgsub = os.path.join(ch_2Dimg_path, f"{ch_name.casefold()}_bgsub_stitched")
            bpf.check_create_save_path(save_path)
            bpf.check_create_save_path(save_path_bgsub)

            for i in tqdm(range(len(ch_2Dimg_list) // pos_max)):  # run once per timepoint
                # print(f"tp: {i+1}")
                img_list_per_tp = [0] * pos_max
                for j in range(0, pos_max):
                    loc = i * pos_max + j
                    # print(loc)
                    # save all pos images in 3D array
                    img = tiff.imread(os.path.join(ch_2Dimg_path, ch_2Dimg_list[loc]))
                    if len(img.shape) != 2:
                        print(f"{ch_2Dimg_list[loc]}: Image shape is not 2D... something is wrong. exiting...")
                        exit()
                    else:
                        img_list_per_tp[j] = img

                stitched_img, stitched_img_bgsub = bpf.img_stitcher_2D(global_coords_px, img_list_per_tp)

                skimage.io.imsave(
                    os.path.join(save_path, f"Timepoint{i+1}_{ch_name}_stitched.png"),
                    stitched_img,
                    check_contrast=False,
                )  # save the stitched image
                skimage.io.imsave(
                    os.path.join(save_path_bgsub, f"Timepoint{i+1}_{ch_name}_stitched.png"),
                    stitched_img_bgsub,
                    check_contrast=False,
                )  # save the bg subtracted stitched image
