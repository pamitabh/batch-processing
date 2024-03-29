# Author(s): Piyush Amitabh

# Details: this code generates mip and stitches them to visualize the tracks

# Created: May 10, 2023

# License: GNU GPL v3.0
# Comment: it is scope agnostic (KLA/WIL LSM) and os agnostic

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
# from scipy import ndimage as ndi
# import pickle
import skimage
from PIL import Image
import tifffile as tiff
from natsort import natsorted
from tqdm import tqdm

import configparser
import re


print("Instructions for stitching:")
print("Image stitching works by reading stage positions from the 'notes.txt' file generated during acquisition")
print("-Images MUST have 'timepoint' substring in their names")
print("-Images MUST have 'pos' or 'region' substring in their names")
print("-Images MUST have channel substring(BF/GFP/RFP) in their names\n")

stitch_dir = input("Enter the location of Directory containing ONE fish data \n(this must contain BF/MIPs and notes.txt file inside): ")
findscope_flag = 0 #this is a global var

def find_lsm_scope(img_h, img_w):
    '''Finds LSM Scope and downscaling factor automatically using image height and width.
    Returns: 
    ds_factor_h = downscaling factor in height, 
    ds_factor_w = downscaling factor in width'''

    global findscope_flag #refer to the global var

    if img_w==img_h: # probably KLA LSM
        findscope_flag = 1

        ds_factor_h = 2048//img_h
        ds_factor_w = 2048//img_w
        r = 2048%img_h

        if r>0: #implying downscaling factor is in fraction
            findscope_flag = 0
            print("Downscaling factor in fraction. Can't process automatically.")

    elif img_w>img_h: # probably WIL LSM
        findscope_flag = 2

        ds_factor_h = 2160//img_h
        ds_factor_w = 2560//img_w

        if ds_factor_h!=ds_factor_w:
            findscope_flag=0

        r_h = 2160%img_h
        r_w = 2560%img_w
        
        if r_h>0 or r_w>0 : #implying downscaling factor is in fraction
            findscope_flag = 0
            print("Downscaling factor in fraction. Can't process automatically.")

    if findscope_flag==1:
        print('LSM Scope used: KLA')
        print(f'Downscaling factor = {ds_factor_w}')
    elif findscope_flag==2:
        print('LSM Scope used: WIL')
        print(f'Downscaling factor = {ds_factor_w}')

    user_check = input('Is the above information correct?(y-default/n): ') or 'y'
    if user_check.casefold()=='n':
        findscope_flag = 0

    if findscope_flag==0: #couldn't find scope, enter manually
        print("ERROR: Failed to determine LSM scope automatically.\nEnter manually")
        findscope_flag = int(input('Enter the scope used:\n1 - KLA LSM Scope\n2 - WIL LSM Scope\nInput (1/2): '))
        if findscope_flag==1 or findscope_flag==2:
            ds_factor_h = int(input('Enter the downscaling factor in height: '))
            ds_factor_w = int(input('Enter the downscaling factor in width: '))
        else:
            print("Fatal Error: Exiting")
            exit()

    return(ds_factor_h, ds_factor_w)

pos_max = int(input('Enter number of positions/regions of imaging per timepoint (default=4): ') or "4")

#removes dir and non-image(tiff) files from a list
def remove_non_image_files(big_list, root_path):
    small_list = []
    for val in big_list:
        if os.path.isfile(os.path.join(root_path, val)): #file check
            filename_list = val.split('.')
            og_name = filename_list[0] 
            ext = filename_list[-1] 
            if (ext=="tif" or ext=="tiff"): #img check
                small_list.append(val)
    return small_list
    
#correct the image list ordering
def reorder_image_by_pos_tp(img_list):
    ordered_img_list = []
    for tp in range(1, (len(img_list)//pos_max) + 1):
        for pos in range(1, pos_max+1):
            for img_name in img_list: #find the location in img_list with pos and tp
                if (f'pos{pos}_' in img_name.casefold()) and (f'timepoint{tp}_' in img_name.casefold()):
                    ordered_img_list.append(img_name)
    return(ordered_img_list)

#make a list of all img files by channel for stitching
sub_names = ['BF', 'GFP', 'RFP']
bf_flag, gfp_flag, rfp_flag = False, False, False #0 means not found, 1 mean found
bf_path, gfp_mip_path, rfp_mip_path = '', '', ''
bf_img_list, gfp_img_list, rfp_img_list = [], [], []

for root, subfolders, filenames in os.walk(stitch_dir):
    for filename in filenames:
        # print(f'Reading: {filename}')
        filepath = os.path.join(root, filename)
        # print(f'Reading: {filepath}')
        filename_list = filename.split('.')
        og_name = filename_list[0] #first of list=name
        ext = filename_list[-1] #last of list=extension

        if (ext=="tif" or ext=="tiff"):
            if (not bf_flag) and ('bf' in og_name.casefold()): #find BF
                print('BF images found at:'+root)
                bf_path = root
                bf_img_list = reorder_image_by_pos_tp(remove_non_image_files(natsorted(os.listdir(root)), root))
                bf_flag = True
            elif 'mip' in og_name.casefold():
                if (not gfp_flag) and ('gfp' in og_name.casefold()):
                    print('GFP MIP images found at:'+root)
                    gfp_mip_path = root
                    gfp_img_list = reorder_image_by_pos_tp(remove_non_image_files(natsorted(os.listdir(root)), root))
                    gfp_flag = True
                elif (not rfp_flag) and ('rfp' in og_name.casefold()):
                    print('RFP MIP images found at:'+root)
                    rfp_mip_path = root
                    rfp_img_list = reorder_image_by_pos_tp(remove_non_image_files(natsorted(os.listdir(root)), root))
                    rfp_flag = True

#find the nearest notes.txt
config = configparser.ConfigParser()
#get start_path for search
#get sample image to find scope and downscaling factor
if gfp_flag:
    start_path = gfp_mip_path
    img = tiff.imread(os.path.join(gfp_mip_path, gfp_img_list[0]))
elif rfp_flag:
    start_path = rfp_mip_path
    img = tiff.imread(os.path.join(rfp_mip_path, rfp_img_list[0]))
elif bf_flag:
    start_path = bf_path
    img = tiff.imread(os.path.join(bf_path, bf_img_list[0]))
#find the fish number from the image path
fish_num = int(start_path[start_path.casefold().rfind('fish')+len('fish')]) #find fish number starting from the child dir
print(f'Found fish_num = {fish_num}')
user_check = input('Continue if correct? (y-default/n)') or 'y'
if user_check.casefold()=='n':
    fish_num = int(input('Enter fish_num: '))

target1 = 'notes.txt'
target2 = 'Notes.txt'
while True:
    if os.path.isfile(os.path.join(start_path,target1)):
        #found
        print(f'found {target1} at:'+start_path)
        config.read(os.path.join(start_path,target1))
        break
    elif os.path.isfile(os.path.join(start_path,target2)):
        #found
        print(f'found {target2} at:'+start_path)
        config.read(os.path.join(start_path,target2))
        break

    if os.path.dirname(start_path)==start_path: #reached root
        #not found
        print("Error: Can't find notes.txt, Enter manually")
        notes_path = input('Enter complete path (should end with .txt): ')
        config.read(notes_path)
        break    
    start_path=os.path.dirname(start_path)
# print(config.sections())

abbrev = config.getfloat(f"Fish {fish_num} Region 1", "x_pos", fallback=False)
if (abbrev):
    # print('abbreviated')
    config_prop_list = ["x_pos", "y_pos", "z_pos"]
else:
    # print('not abbreviated')
    config_prop_list = ["x_position", "y_position", "z_position"]
stage_coords = np.zeros(shape=(pos_max,3))
for i in range(1, pos_max+1):
    for j, val in enumerate(config_prop_list): #x/y/z axes
        stage_coords[i-1][j] = config.getfloat(f"Fish {fish_num} Region {i}", val)
print(f"Found stage_coords: \n{stage_coords}")

(ds_h, ds_w) = find_lsm_scope(img.shape[0], img.shape[1])
# The pixel spacing in our LSM image is 1µm in the z axis, and  0.1625µm in the x and y axes.
zd, xd, yd = 1, 0.1625, 0.1625 #zeroth dimension is z in skimage coords
orig_spacing = np.array([zd, xd, yd]) #change to the actual pixel spacing from the microscope
new_spacing = np.array([zd, xd*ds_w, yd*ds_h]) #downscale x&y by n

# %% [markdown]
# **KLA**
# Global Y_AP = stage y =  ax0
# Global X_DV = - (stage x) = ax1
# stitch along Y_AP - ax0
# **WIL**
# Global Y_AP = stage y =  ax1
# Global X_DV = - (stage x) = -(ax0)
# stitch along Y_AP - ax1

def img_stitcher(stage_coords, img_list):
    """accept a list of 2D images in img_list and use stage_coords read from notes.txt to stitch images
    Returns: 2D np.array containing the stitched image
    """
    if findscope_flag == 0:
        print("ERROR: Couldn't find the LSM scope")
        exit()
    # poses = np.shape(img_list)[0]
    img_height = np.shape(img_list)[1]
    img_width = np.shape(img_list)[2]

    stage_origin = stage_coords[0].copy()
    global_coords_um = stage_coords - stage_origin
    global_coords_um[:, 0] = global_coords_um[:, 0] * -1  # flip x axis

    # change global coords to px
    global_coords_px_1 = (np.ceil(global_coords_um[:, 0] / new_spacing[1])).astype(int)
    global_coords_px_2 = (np.ceil(global_coords_um[:, 1] / new_spacing[2])).astype(int)
    global_coords_px = np.vstack((global_coords_px_1, global_coords_px_2)).T
    
    #stitched image ax0 is going down, ax1 is to the right
    if findscope_flag == 2: #wil lsm, stitch horizontally
        ax0_offset = global_coords_px[:, 0] * -1  # ax0 = -Global X_DV
        ax1_offset = global_coords_px[:, 1]       # ax1 = Global Y_AP
        ax0_offset = ax0_offset - np.min(ax0_offset) #find offset from min number
        ax1_offset = ax1_offset - np.min(ax1_offset)
    elif findscope_flag == 1:  # kla lsm, stitch vertically
        ax0_offset = global_coords_px[:, 1] # ax0 = Global Y_AP
        ax1_offset = global_coords_px[:, 0] # ax1 = Global X_DV
        ax0_offset = ax0_offset - np.min(ax0_offset) #find offset from min number
        ax1_offset = ax1_offset - np.min(ax1_offset)
        
    ax0_max = img_height + np.max(ax0_offset)
    ax1_max = img_width + np.max(ax1_offset)
    stitched_image = np.zeros([ax0_max, ax1_max]) #rows-height, cols-width

    for i, (h0, w0) in enumerate(zip(ax0_offset, ax1_offset)):
        stitched_image[h0 : h0 + img_height, w0 : w0 + img_width] = img_list[i]
    return(stitched_image)

#read all images per timepoint then stitch and save them at dest 
ch_flag_list = [bf_flag, gfp_flag, rfp_flag]
ch_path_list = [bf_path, gfp_mip_path, rfp_mip_path]
ch_img_list = [bf_img_list, gfp_img_list, rfp_img_list]

for k, ch_flag in enumerate(ch_flag_list):
    ch_path = ch_path_list[k]
    all_img_list = ch_img_list[k]
    ch_name = sub_names[k]

    if ch_flag:
        print(f"Stitching {ch_name} images...")
        save_path = os.path.join(ch_path, ch_name.casefold()+'_stitched')
        if not os.path.exists(save_path): #check if the dest exists
            print("Save path doesn't exist.")
            os.makedirs(save_path)
            print(f"Directory '{ch_name.casefold()}_stitched' created")
        else:
            print("Save path exists")

        for i in tqdm(range(len(all_img_list)//pos_max)): #run once per timepoint
            # print(f"tp: {i+1}")
            img_list_per_tp = [0]*pos_max
            for j in range(0, pos_max):
                loc = i*pos_max + j
                # print(loc)
                img_list_per_tp[j] = tiff.imread(os.path.join(ch_path, all_img_list[loc])) #save all pos images in 3D array

            stitched_img = img_stitcher(stage_coords, img_list_per_tp)
            stitched_img_uint = skimage.util.img_as_uint(skimage.exposure.rescale_intensity(stitched_img)) #rescale float and change dtype to uint16
            skimage.io.imsave(os.path.join(save_path, f'Timepoint{i+1}_{ch_name}_stitched.png'), \
                              stitched_img_uint, check_contrast=False) #save the image
