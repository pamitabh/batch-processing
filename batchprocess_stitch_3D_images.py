# %% [markdown]
# Author(s): Piyush Amitabh
# 
# Details: batchprocesses 3D images using notes.txt file and saves the stitched images in stitched_3D folder
# 
# Created: Jan 15, 2024
# 
# License: GNU GPL v3.0

import os
import tifffile as tiff
from natsort import natsorted
from tqdm import tqdm
import re

import batchprocessing_functions_v1 as bpf

print('''Instructions for stitching:
    - Image stitching works by reading stage positions from the 'notes.txt' file generated during acquisition
    - Images MUST have:
        a. 'timepoint' substring in their names
        b. 'pos' or 'region' substring in their names
        c. channel substring(GFP/RFP) in their names''')
top_dir = os.path.normpath(input('Enter the top directory with ALL acquisitions: '))

#all unique GFP/RFP location gets added to the main_dir_list
main_dir_list = []
for root, subfolders, _ in os.walk(top_dir):
    if ('GFP' in subfolders) or ('RFP' in subfolders):
        main_dir_list.append(root)
main_dir_list = natsorted(main_dir_list)
print(f'Found these fish data:\n{main_dir_list}')

diff_savedir_flag = (input('Do you want to save the images in a different folder? (y/[n])') or 'n').casefold()=='y'
if diff_savedir_flag:
    print('''You have chosen to save stitched images in a different directory, 
          give ONE fish folder at a time to prevent overwriting.''')
    save_dir = os.path.normpath(input('Enter the save dir: '))

bg_sub_flag = (input('Do you want to subtract background? ([y]/n)') or 'y').casefold() == 'y'
pos_input_flag = input('Is the number of pos/regions in each folder above the same? ([y]/n)') or 'y'
if pos_input_flag.casefold()=='n':
    print('Error: Not implemented yet. This only works if the number of pos/regions in each folder is the same.')
    exit()
# if pos_input_flag.casefold()=='y':
#     pos_max_list = len(main_dir_list)* \
#     [int(input('Enter number of positions/regions of imaging per timepoint (default=4)') or '4')]
# else:
#     pos_max_list = []
#     while pos_max_list != len(main_dir_list):
#         pos_max_list = (input('Enter the list of positions/regions separated by space in the above order')).split()
#         if pos_max_list != len(main_dir_list):
#             print('entered list length is not same as the number of folders found above. Please re-enter.')
#             continue
#         else:
#             # convert each item to int type
#             for i in range(len(pos_max_list)):
#                 pos_max_list[i] = int(pos_max_list[i])

ch_names = ['GFP', 'RFP']

for main_dir in main_dir_list:  # main_dir = location of Directory containing ONE fish data
    print(f"Processing {main_dir}...")
    ch_3Dimg_flags, ch_3Dimg_paths, ch_3Dimg_lists = bpf.find_3D_images(main_dir)
    stage_coords = bpf.find_stage_coords_n_pixel_width_from_3D_images(ch_3Dimg_flags, ch_3Dimg_paths, ch_3Dimg_lists)
    global_coords_px = bpf.global_coordinate_changer(stage_coords)

    for ch_name, ch_3Dimg_flag, ch_3Dimg_path, ch_3Dimg_list in \
    zip(ch_names, ch_3Dimg_flags, ch_3Dimg_paths, ch_3Dimg_lists):
        if ch_3Dimg_flag:
            pos_max = bpf.pos_max
            print(f"Stitching {ch_name} 3D images...")
            if diff_savedir_flag:
                save_path = os.path.join(save_dir, f'{ch_name.casefold()}_zstack_stitched')
            else:
                save_path = os.path.join(ch_3Dimg_path, f'{ch_name.casefold()}_zstack_stitched')
            bpf.check_create_save_path(save_path)

            for i in tqdm(range(len(ch_3Dimg_list)//pos_max)):  # run once per timepoint
                # print(f"tp: {i+1}")

                img_list_per_tp = [0] * pos_max
                for j in range(0, pos_max):
                    loc = i * pos_max + j
                    # print(loc)
                    # save all pos images in a list
                    img = tiff.imread(os.path.join(ch_3Dimg_path, ch_3Dimg_list[loc]))
                    if len(img.shape)!=3:
                        print(f'{ch_3Dimg_list[loc]}: Image shape is not 3D... something is wrong. exiting...')
                        exit()
                    else:
                        img_list_per_tp[j] = img
                
                stitched_image = bpf.img_stitcher_3D(global_coords_px, img_list_per_tp, bg_sub_flag)

                if bg_sub_flag:
                    save_name = f"Timepoint{i+1}_{ch_name}_stitched_zstack_bg_sub.tif"
                else:
                    save_name = f"Timepoint{i+1}_{ch_name}_stitched_zstack.tif"

                tiff.imwrite(os.path.join(save_path, save_name), stitched_image, compression='LZW')
