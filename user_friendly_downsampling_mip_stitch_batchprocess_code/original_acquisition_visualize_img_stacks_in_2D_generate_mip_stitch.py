# Author(s): Piyush Amitabh
#
# Details: this code generates mip and stitches them to visualize the img stacks
#          Only works with Original Images (no processing) acquired in RPLab LSM 
#
# Created: July 29, 2023

import os
import shutil

import batchprocessing_functions_v5 as bpf
import numpy as np
import skimage as ski
from natsort import natsorted
from tqdm import tqdm

action_flag = 0

while action_flag == 0:
    action_flag = int(input(
    """This code will find Max intensity projections of `z-stacks` and stitch the resulting images using the metadata found in `notes`
        Run this *ONLY* on the original acquisition folder of LSM images as it uses the folder structure to find the images
        Warning: This code ONLY works with single channel z-stack tiff images. It will give unpredictable results with >3 dimensions
        Number of fish, positions and timepoints can be different in each folder, but channel names should be consistent
         
        Do you want to:
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

## find MIP
if action_flag != 3: # find MIP
    #get source and target directories
    src, trg = "", ""
    while src == trg or src == "" or trg == "":
        src = os.path.normpath(
            input("Enter the Parent folder for original images (should contain 'Acquisition' folders): ")
        )
        trg = os.path.normpath(input("Enter the Destination folder: "))
        if src == trg:
            print("Parent and Destination folders cannot be empty or have the same location. Re-Enter..")
    #get ch_list to process mips
    user_ch_list = None
    while user_ch_list is None:
        user_input = input("""Enter the channel numbers to process MIPs: 
                            0: Brightfield, 1: GFP, 2: RFP (e.g. '012' for all 3 channels):\n""")
        user_ch_list = [int(ch.strip()) for ch in user_input if ch.strip().isdigit() and int(ch.strip()) in [0, 1, 2]]
        if not user_ch_list:
            print("Invalid input. Please enter valid channel numbers.")
    ch_list = [os.path.join('snap','BF') if ch == 0 
            else os.path.join('zstack','GFP') if ch == 1 
            else os.path.join('zstack','RFP') for ch in user_ch_list]

    new_trg = os.path.join(trg, src.split(os.sep)[-1]+"_mip_stitched")

    acq_list = [acq for acq in os.listdir(src) if os.path.isdir(os.path.join(src, acq)) and 'Acquisition' in acq]
    acq_list = natsorted(acq_list)

    # Function to copy notes.txt from src/acq to trg/acq
    def copy_notes(src, trg, acq):
        src_file = os.path.join(src, acq, 'notes.txt')
        trg_file = os.path.join(trg, acq, 'notes.txt')
        if os.path.exists(src_file):
            shutil.copy(src_file, trg_file)
        else:
            print(f"Source file {src_file} does not exist.")
            print("FATAL ERROR: notes.txt not found in the source acquisition folder. It is required for stitching.")
            exit()

    # Iterate over the acquisition list and copy notes.txt
    for acq in acq_list:
        print(f"Copying `notes.txt` for {acq} folder..")
        trg_acq_dir = os.path.join(new_trg, acq)
        if not os.path.exists(trg_acq_dir):
            os.makedirs(trg_acq_dir)
            print(f"Created folder: {trg_acq_dir}")
        copy_notes(src, new_trg, acq)
        print('copied!')

    # user_input_3d_stiching = input("""Do you want to stitch 3D images?
    #                             Warning: requires a lot of RAM and disk space!! (y/[n]):""") or "n"

    # if user_input_3d_stiching.lower() == "y":
    #     # Perform 3D stitching and display the images
    #     # Add your code here to perform 3D stitching and display the images
    #     print("Sorry not implemented yet! Send me an email to remind me.")
    #     pass
    # elif user_input_3d_stiching.lower() == "n":
    #     print("Okay, 3D stitching will not be performed.")
    # else:
    #     print("Invalid input. Please enter 'y' or 'n'.")

    print("Finding Max Intensity Projections...")
    #Process MIPs
    for acq in acq_list:
        fish_list = [fish for fish in os.listdir(os.path.join(src, acq)) if os.path.isdir(os.path.join(src, acq, fish))]
        fish_list = natsorted(fish_list)
        for fish in fish_list:
            for ch in ch_list:
                #continue only if: ch has 'zstack' sub-sting
                if 'zstack' not in ch:
                    print(f"Skipping {os.path.join(acq, fish, ch)} as it is not a z-stack image")
                    continue
                
                pos_list = [pos for pos in os.listdir(os.path.join(src, acq, fish)) if os.path.isdir(os.path.join(src, acq, fish, pos))]    
                pos_list = natsorted(pos_list)
                for pos in pos_list:
                    timepoint_list = [timepoint for timepoint in os.listdir(os.path.join(src, acq, fish, pos, ch)) if os.path.isdir(os.path.join(src, acq, fish, pos, ch, timepoint))]
                    timepoint_list = natsorted(timepoint_list)
                    for timepoint in timepoint_list:
                            img_folder = os.path.join(src, acq, fish, pos, ch, timepoint)
                            print(f"Processing MIP for: {img_folder}")
                            
                            trg_folder = os.path.join(new_trg, acq, fish, ch)
                            if not os.path.exists(trg_folder):
                                os.makedirs(trg_folder)
                            
                            for filename in os.listdir(img_folder):
                                filename_list = filename.split(".")
                                og_name = filename_list[0]  # first of list=name
                                ext = filename_list[-1]  # last of list=extension

                                if (ext == "tif" or ext == "tiff") and (not bpf.check_overflowed_stack(og_name)):
                                    read_image = ski.io.imread(os.path.join(img_folder, filename))
                                    arr_mip = np.max(read_image, axis=0)  # create MIP                  
                                    img_mip = np.round(arr_mip).astype(read_image.dtype)
                                    save_name = f"{og_name.replace('_MMStack', '')}_mip.tif"
                                    ski.io.imsave(os.path.join(trg_folder, save_name), img_mip, check_contrast=False)
        
    # copy BF images
    for acq in acq_list:
        fish_list = [fish for fish in os.listdir(os.path.join(src, acq)) if os.path.isdir(os.path.join(src, acq, fish))]
        fish_list = natsorted(fish_list)
        for fish in fish_list:
            for ch in ch_list:
                if 'BF' not in ch:
                    continue
                pos_list = [pos for pos in os.listdir(os.path.join(src, acq, fish)) if os.path.isdir(os.path.join(src, acq, fish, pos))]    
                pos_list = natsorted(pos_list)
                for pos in pos_list:
                    timepoint_list = [timepoint for timepoint in os.listdir(os.path.join(src, acq, fish, pos, ch)) if os.path.isdir(os.path.join(src, acq, fish, pos, ch, timepoint))]
                    timepoint_list = natsorted(timepoint_list)
                    for timepoint in timepoint_list:
                            img_folder = os.path.join(src, acq, fish, pos, ch, timepoint)
                            print(f"Copying BF images for: {img_folder}")
                            trg_folder = os.path.join(new_trg, acq, fish, ch)
                            if not os.path.exists(trg_folder):
                                os.makedirs(trg_folder)
                            
                            for filename in os.listdir(img_folder):
                                filename_list = filename.split(".")
                                og_name = filename_list[0]  # first of list=name
                                ext = filename_list[-1]  # last of list=extension

                                if (ext == "tif" or ext == "tiff") and (not bpf.check_overflowed_stack(og_name)):
                                    save_name = f"{og_name.replace('_MMStack', '')}.tif"
                                    shutil.copy(src=os.path.join(img_folder, filename),
                                                dst=os.path.join(trg_folder, save_name))

if action_flag == 3:  # only stitch, so take the input from the user as it wasn't taken before
    new_trg = os.path.normpath(
        input("""Enter the folder with images to stitch:
              Note- it must have the notes.txt, can have multiple `Acquisition` folders\n"""))
    acq_list = [acq for acq in os.listdir(new_trg) if os.path.isdir(os.path.join(new_trg, acq)) and 'Acquisition' in acq]
    acq_list = natsorted(acq_list)

## Stitching
if action_flag != 2: # not 'only mip' so stitch
    ch_names = ["BF", "GFP_mip", "RFP_mip"]

    for acq in acq_list:
        fish_list = [fish for fish in os.listdir(os.path.join(new_trg, acq)) if os.path.isdir(os.path.join(new_trg, acq, fish))]
        fish_list = natsorted(fish_list)
        for fish in fish_list:
            print(f"Processing: {os.path.join(new_trg, acq, fish)}")
            ch_2Dimg_flags, ch_2Dimg_paths, ch_2Dimg_lists = bpf.find_2D_images(os.path.join(new_trg, acq, fish))
            stage_coords = bpf.find_stage_coords_n_pixel_width_from_2D_images(ch_2Dimg_flags, ch_2Dimg_paths, ch_2Dimg_lists)
            global_coords_px = bpf.global_coordinate_changer(stage_coords)

            for ch_name, ch_2Dimg_flag, ch_2Dimg_path, ch_2Dimg_list in zip(
                ch_names, ch_2Dimg_flags, ch_2Dimg_paths, ch_2Dimg_lists
            ):
                if ch_2Dimg_flag:
                    pos_max = bpf.pos_max
                    print(f"Stitching {ch_name} images...")
                    save_path_stitched_img = os.path.join(ch_2Dimg_path, f"{ch_name.casefold()}_stitched")
                    save_path_stitched_edited_img = os.path.join(ch_2Dimg_path, f"{ch_name.casefold()}_stitched_bgsub_rescaled")
                    bpf.check_create_save_path(save_path_stitched_img)
                    bpf.check_create_save_path(save_path_stitched_edited_img)

                    for i in tqdm(range(len(ch_2Dimg_list) // pos_max)):  # run once per timepoint
                        # print(f"tp: {i+1}")
                        img_list_per_tp = [0] * pos_max
                        for j in range(0, pos_max):
                            loc = i * pos_max + j
                            # print(loc)
                            # save all pos images in 3D array
                            img = ski.io.imread(os.path.join(ch_2Dimg_path, ch_2Dimg_list[loc]))
                            if len(img.shape) != 2:
                                print(f"{ch_2Dimg_list[loc]}: Image shape is not 2D... something is wrong. exiting...")
                                exit()
                            else:
                                img_list_per_tp[j] = img

                        stitched_img, stitched_img_bgsub = bpf.img_stitcher_2D(global_coords_px, img_list_per_tp)
                        # By default, the min/max intensities of the input image are stretched to the limits allowed by the image’s dtype,
                        # since in_range defaults to ‘image’ and out_range defaults to ‘dtype’:
                        # stitched_img_bgsub_rescaled = ski.exposure.rescale_intensity(stitched_img_bgsub) #produces images with pulsing mean intensity

                        og_datatype = stitched_img_bgsub.dtype
                        # use histogram matching using the first image
                        if i == 0:  # set first stitched image as reference
                            ref_img_histogram = stitched_img_bgsub
                            stitched_img_bgsub_rescaled = stitched_img_bgsub
                        else:  # match remaining images histogram to the first image
                            stitched_img_bgsub_rescaled = (
                                ski.exposure.match_histograms(image=stitched_img_bgsub, reference=ref_img_histogram)
                            ).astype(og_datatype)

                        ski.io.imsave(
                            os.path.join(save_path_stitched_img, f"Timepoint{i+1}_{ch_name}_stitched.png"),
                            stitched_img,
                            check_contrast=False,
                        )  # save the stitched image
                        ski.io.imsave(
                            os.path.join(save_path_stitched_edited_img, f"Timepoint{i+1}_{ch_name}_stitched.png"),
                            stitched_img_bgsub_rescaled,
                            check_contrast=False,
                        )  # save the bg subtracted stitched image

print(f'Done! Processed images are in: {new_trg}')
#wait for user to close the window
input("Press Enter to close the program...")
exit()