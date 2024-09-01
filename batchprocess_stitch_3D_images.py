# %% [markdown]
# Author(s): Piyush Amitabh
#
# Details: batchprocesses 3D images using notes.txt file and saves the stitched images in stitched_3D folder
#
# Created: Jan 15, 2024
#
# License: GNU GPL v3.0

import os

from natsort import natsorted
from tqdm import tqdm

# import numpy as np
# import pickle
# import lzma
import user_friendly_downsampling_mip_stitch_batchprocess_code.batchprocessing_functions_v4 as bpf

print(
    """Instructions for stitching:
    - Image stitching works by reading stage positions from the 'notes.txt' file generated during acquisition
    - Images MUST have:
        a. 'timepoint' substring in their names
        b. 'pos' or 'region' substring in their names
        c. channel substring(GFP/RFP) in their names"""
)
top_dir = os.path.normpath(input("Enter the top directory with ALL acquisitions: "))

# all unique GFP/RFP location gets added to the main_dir_list
main_dir_list = []
for root, subfolders, _ in os.walk(top_dir):
    if ("GFP" in subfolders) or ("RFP" in subfolders):
        main_dir_list.append(root)
main_dir_list = natsorted(main_dir_list)
print(f"Found these fish data:\n{main_dir_list}")

diff_savedir_flag = (
    input("Do you want to save the images in a different folder? (y/[n])") or "n"
).casefold() == "y"
if diff_savedir_flag:
    user_save_dir = os.path.normpath(input("Enter the save dir: "))
    new_save_dir = os.path.join(
        user_save_dir, f"{os.path.basename(top_dir)}_3D_stitched"
    )
    bpf.check_create_save_path(new_save_dir)

bg_sub_flag = (
    input("Do you want to subtract background? (y/[n])") or "n"
).casefold() == "y"

# get compression type from user
compression_type = (
    input("Enter the compression type ([Deflate], LZW, LZMA, Zstd): ") or "Deflate"
)

ch_names = ["GFP", "RFP"]

for (
    main_dir
) in main_dir_list:  # main_dir = location of Directory containing ONE fish data
    print(f"Processing {main_dir}...")
    ch_3Dimg_flags, ch_3Dimg_paths, ch_3Dimg_lists = bpf.find_3D_images(main_dir)
    stage_coords = bpf.find_stage_coords_n_pixel_width_from_3D_images(
        ch_3Dimg_flags, ch_3Dimg_paths, ch_3Dimg_lists
    )
    global_coords_px = bpf.global_coordinate_changer(stage_coords)

    for ch_name, ch_3Dimg_flag, ch_3Dimg_path, ch_3Dimg_list in zip(
        ch_names, ch_3Dimg_flags, ch_3Dimg_paths, ch_3Dimg_lists
    ):
        if ch_3Dimg_flag:
            pos_max = bpf.pos_max
            print(f"Stitching {ch_name} 3D images...")
            if diff_savedir_flag:
                save_subdir = main_dir.replace(top_dir, "").strip(
                    os.sep
                )  # find and remove the top_dir from the main_dir
                save_path = os.path.join(
                    new_save_dir, save_subdir, f"{ch_name.casefold()}_3D_stitched"
                )
            else:
                save_path = os.path.join(
                    ch_3Dimg_path, f"{ch_name.casefold()}_3D_stitched"
                )
            bpf.check_create_save_path(save_path)

            for i in tqdm(
                range(len(ch_3Dimg_list) // pos_max)
            ):  # run once per timepoint
                # print(f"tp: {i+1}")
                img_path_list_per_tp = [0] * pos_max
                for j in range(0, pos_max):
                    loc = i * pos_max + j
                    # print(loc)
                    # save all pos image_path in a list
                    img_path_list_per_tp[j] = os.path.join(
                        ch_3Dimg_path, ch_3Dimg_list[loc]
                    )

                if bg_sub_flag:
                    save_name = f"Timepoint{i+1}_{ch_name}_stitched_3D_bg_sub.tif"
                else:
                    save_name = f"Timepoint{i+1}_{ch_name}_stitched_3D.tif"

                bpf.img_stitcher_3D(
                    global_coords_px,
                    img_path_list_per_tp,
                    bg_sub_flag,
                    os.path.join(save_path, save_name),
                    compression_type,
                )
