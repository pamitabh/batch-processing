# batchprocessing functions
# created: Jan 15, 2024

import re
import numpy as np
import pandas as pd
import tifffile as tiff
import os
import configparser
from natsort import natsorted
# from scipy.spatial import distance
# import plotly.express as px

## CONSTANT
# The pixel spacing in our LSM image is 1µm in the z axis, and  0.1625µm in the x and y axes.
ZD, XD, YD = 1, 0.1625, 0.1625

## Get global variables
pos_max = 0
img_h, img_w = 0, 0
find_scope_flag = 0
new_spacing = [0, 0, 0]

## Small Helping Functions

# check and create path
def check_create_save_path(save_path):
    save_path = os.path.normpath(save_path)
    if not os.path.exists(save_path):  # check if the dest exists
        print("Save path doesn't exist.")
        os.makedirs(save_path)
        print(f"Directory '{os.path.basename(save_path)}' created")
    else:
        print("Save path exists")

#removes dir and non-image(tiff) files from a list
def remove_non_image_files(big_list, root_path):
    small_list = []
    for val in big_list:
        if os.path.isfile(os.path.join(root_path, val)): #file check
            filename_list = val.split('.')
            # og_name = filename_list[0] 
            ext = filename_list[-1] 
            if (ext=="tif" or ext=="tiff"): #img check
                small_list.append(val)
    return small_list

#removes dir and non-csv files from a list
def remove_non_csv_files(big_list, root_path):
    small_list = []
    for val in big_list:
        if os.path.isfile(os.path.join(root_path, val)): #file check
            filename_list = val.split('.')
            # og_name = filename_list[0] 
            ext = filename_list[-1] 
            if (ext=="csv"): #csv check
                small_list.append(val)
    return small_list

def reorder_files_by_pos_tp(file_list):
    file_list_arr = np.array(file_list)
    global pos_max
    raw_pos_arr = np.zeros_like(file_list_arr, dtype=int)
    raw_tp_arr = np.zeros_like(file_list_arr, dtype=int)
    for i, file_name in enumerate(file_list_arr):
        file_name_list = file_name.split('_')
        for substr in file_name_list:
            substr = substr.casefold()
            if 'pos' in substr:
                raw_pos_arr[i] = int(substr.removeprefix('pos'))
            if 'timepoint' in substr:
                raw_tp_arr[i] = int(substr.removeprefix('timepoint'))
    pos_max = np.max(raw_pos_arr) #get pos_max
    ind = np.lexsort((raw_pos_arr,raw_tp_arr)) # Sort by tp, then by pos
    return(file_list_arr[ind]) 

# Important functions
def find_3D_images(main_dir, ofc_flag=False):
    #very general and robust code which looks for the files with those names instead of depending upon just the folder names
    #3D images
    gfp_flag, rfp_flag = False, False #0 means not found, 1 mean found
    gfp_path, rfp_path = '', ''
    gfp_img_list, rfp_img_list = [], []
    for root, subfolders, filenames in os.walk(main_dir):
        for filename in filenames:
            # print(f'Reading: {filename}')
            # filepath = os.path.join(root, filename)
            # print(f'Reading: {filepath}')
            filename_list = filename.split('.')
            og_name = (filename_list[0]).casefold() #first of list=name
            ext = (filename_list[-1]).casefold() #last of list=extension
            if (ext == "tif" or ext == "tiff") and not(rfp_flag or gfp_flag): #just need one sample image
                if ("bf" not in og_name) and ("mip" not in og_name): #ignore BF and MIP
                    if "gfp" in og_name:  # find GFP
                        print("GFP images found at:" + root)
                        gfp_path = root
                        gfp_img_list = reorder_files_by_pos_tp(remove_non_image_files(natsorted(os.listdir(root)), root))
                        gfp_flag = True
                    elif "rfp" in og_name:  # find RFP
                        print("RFP images found at:" + root)
                        rfp_path = root
                        rfp_img_list = reorder_files_by_pos_tp(remove_non_image_files(natsorted(os.listdir(root)), root))
                        rfp_flag = True

    if not gfp_flag:
        print(f'*No* GFP images found in {main_dir}')
    if not rfp_flag:
        print(f'*No* RFP images found in {main_dir}')
    if not(rfp_flag or gfp_flag):
        print("Need at least one channel 3D images to work.. None found.. Exiting..")
        exit()
    return( 
        [gfp_flag, rfp_flag],
        [gfp_path, rfp_path],
        [gfp_img_list, rfp_img_list], 
        )

def find_lsm_scope(img_h, img_w):
    '''Finds LSM Scope and downscaling factor automatically using image height and width.
    Returns: 
    ds_factor_h = downscaling factor in height, 
    ds_factor_w = downscaling factor in width'''

    global findscope_flag #refer to the global var
    ds_factor_w, ds_factor_h = 1, 1

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

def find_stage_coords_n_pixel_width_from_2D_images(ch_flags, ch_paths, ch_img_lists):
    '''Send channel flags and paths in the order [bf, gfp, rfp]'''
    #change global image_height and image_width
    global img_h, img_w, new_spacing
    #unpack variables
    bf_flag, gfp_flag, rfp_flag = ch_flags 
    bf_path, rfp_mip_pathstack = ch_paths
    bf_img_list, gfp_img_list, rfp_img_list = ch_img_lists
    #find the nearest notes.txt
    config = configparser.ConfigParser()
    start_path = ''
    img_path = '' #dummy
    #get start_path for search
    #get sample image to find scope and downscaling factor
    if bf_flag:
        start_path = bf_path
        img_path = os.path.join(bf_path, bf_img_list[0])
    elif gfp_flag:
        start_path = gfp_mip_path
        img_path = os.path.join(gfp_mip_path, gfp_img_list[0])
    elif rfp_flag:
        start_path = rfp_mip_path
        img_path = os.path.join(rfp_mip_path, rfp_img_list[0])

    #get sample image dimensions
    img = tiff.imread(img_path)
    img_h, img_w = img.shape[0], img.shape[1]
    (ds_h, ds_w) = find_lsm_scope(img_h, img_w)
    new_spacing = np.array([ZD, YD*ds_h, XD*ds_w]) #downscale x&y by n, skimage coords = z, y, x plane, row, col
    print(f"Pixel width (plane, row, col): {new_spacing}\n")

    #find the fish number from the image path
    fish_num = int(img_path[img_path.casefold().rfind("fish") + len("fish")])  # find fish number starting from the img_name
    print(f'found fish_num = {fish_num}')
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
    # config_prop_list = ["x_pos", "y_pos", "z_pos"]
        config_prop_list = ["x_pos", "y_pos", "z_stack_start_pos"] #wil and kla stores in this format
        print(f'abbreviated props... reading {config_prop_list}')
    else:
    # config_prop_list = ["x_position", "y_position", "z_position"]
        config_prop_list = ["x_position", "y_position", "z_start_position"]
        print(f'not abbreviated props... reading {config_prop_list}')
    stage_coords = np.zeros(shape=(pos_max,3))
    for i in range(1, pos_max+1):
        for j, val in enumerate(config_prop_list): #x/y/z axes
            stage_coords[i-1][j] = config.getfloat(f"Fish {fish_num} Region {i}", val)
    print(f"Found stage_coords: \n{stage_coords}")
    return(stage_coords)

def find_stage_coords_n_pixel_width_from_3D_images(ch_flags, ch_paths, ch_img_lists):
    '''Send channel flags and paths in the order [gfp, rfp]'''
    #change global image_height and image_width
    global img_h, img_w, new_spacing
    #unpack variables
    gfp_flag, rfp_flag = ch_flags 
    gfp_stack_path, rfp_stack_path = ch_paths
    gfp_img_list, rfp_img_list = ch_img_lists
    #find the nearest notes.txt
    config = configparser.ConfigParser()
    start_path = ''
    img_path = '' #dummy
    #get start_path for search
    #get sample image to find scope and downscaling factor
    if gfp_flag:
        start_path = gfp_stack_path
        img_path = os.path.join(start_path, gfp_img_list[0])
    elif rfp_flag:
        start_path = rfp_stack_path
        img_path = os.path.join(start_path, rfp_img_list[0])
    print(start_path)
    print(img_path)
    #get sample image dimensions
    img = (tiff.imread(img_path))[0] # type: ignore #get one z slice
    if img.ndim!=2:
        print(f'ERROR: Image dimension is {img.ndim + 1}, expected 3')
        exit()
    img_h, img_w = img.shape[0], img.shape[1]
    (ds_h, ds_w) = find_lsm_scope(img_h, img_w)
    new_spacing = np.array([ZD, YD*ds_h, XD*ds_w]) #downscale x&y by n, skimage coords = z, y, x plane, row, col
    print(f"Pixel width (plane, row, col): {new_spacing}\n")

    #find the fish number from the image path
    fish_num = int(img_path[img_path.casefold().rfind("fish") + len("fish")])  # find fish number starting from the img_name
    print(f'found fish_num = {fish_num}')
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
    # config_prop_list = ["x_pos", "y_pos", "z_pos"]
        config_prop_list = ["x_pos", "y_pos", "z_stack_start_pos"] #wil and kla stores in this format
        print(f'abbreviated props... reading {config_prop_list}')
    else:
    # config_prop_list = ["x_position", "y_position", "z_position"]
        config_prop_list = ["x_position", "y_position", "z_start_position"]
        print(f'not abbreviated props... reading {config_prop_list}')
    stage_coords = np.zeros(shape=(pos_max,3))
    for i in range(1, pos_max+1):
        for j, val in enumerate(config_prop_list): #x/y/z axes
            stage_coords[i-1][j] = config.getfloat(f"Fish {fish_num} Region {i}", val)
    print(f"Found stage_coords: \n{stage_coords}")
    return(stage_coords)

def global_coordinate_changer(stage_coords):
    ''' Parameters: stage_coords: read from notes.txt to stitch images
                    new_spacing: contains pixel width of the images
        Returns: 2D np.array same shape as stage_coords
    '''
    # original camera pixel width is 1µm in the z (leading!) axis, and  0.1625µm in the x and y axes.
    # for downsampled by 4, this will be orig pixel_width*4 
    # To correct for the offset and stitch different acquisition positions together, note the following:
    # - regionprops generates local coords of objects in the image as `axis-0,1 and 2`: this is our `Local coords system`
    # - stage positions is saved by micromanager and obtained from the metadata as `XPositionUm`, similarly for y and z. this is a `global coords system` in the sense that it is same for all the images for a given sample
    # - Finally we define our `Global coordinates` to the data frames as **"y-ap-um", "x-dv-um", "z-lr-um"** where ap is anterior to posterior axis, dv is dorsal to ventral axis, lr is left-right axis (*don't know the direction*, doesn't matter as long as the local and global are in the same direction)

    # The direction of Global coords system is different in Klamath LSM and Willamette LSM:

    # Klamath LSM:
    # - Stage +Z <-> Global +Z_lr <-> Local axis-0: (so same direction) needs to be ensured that it is same for each acquisition 
    # - Stage +Y <-> Global +Y_ap <-> Local axis-1: (so same direction) same for all acquisition
    # - Stage -X <-> Global +X_dv <-> Local axis-2: (so inverse direction) same for all acquisition

    # To resolve the inverse directions between global x and local axis-2, I am flipping the global coordinate system's x axis.

    # Willamete LSM:
    # - Stage +Z <-> Global +Z_lr <-> Local axis-0: (so same direction) needs to be verified for each acquisition 
    # - Stage +Y <-> Global +Y_ap <-> Local axis-1: (so same direction) same for all acquisition
    # - Stage +X <-> Global -X_dv <-> Local axis-2: (so inverse direction) same for all acquisition

    # To resolve the flipped axes between global x/y and stage x/y, I am exchanging the global coordinate system's axis.

    stage_origin = stage_coords[0].copy()
    global_coords_um = stage_coords - stage_origin #set first stage position as zero
    global_coords_um[:, 0] = global_coords_um[:, 0] * -1 #flip x axis
    #um to pixels: 1px = (1/pixel width) um
    #as the stage position is in x (col:axis-2), y(row:axis-1), z(plane:axis-0) format
    global_coords_px = global_coords_um/ [new_spacing[2], new_spacing[1], new_spacing[0]]
    return(global_coords_px)

def median_bg_subtraction(img_wo_bg_sub):
    img_bg_sub = img_wo_bg_sub - np.median(img_wo_bg_sub.flatten()) #subtract median
    img_bg_sub[img_bg_sub<0] = 0 #make all negative values zero
    return(img_bg_sub)

def check_overflowed_stack(filename):
    '''return True if the 'filename' is a overflowed_stack else False'''
    num = filename[filename.casefold().rfind("mmstack_") + len("mmstack_")]
    return(re.match(r'\d', num))

def img_stitcher_3D(global_coords_px, img_list, bg_sub=True):
    """accept a list of 3D images in img_list and use stage_coords read from notes.txt to stitch images
    Returns: 3D np.array containing the stitched image
    """
    if findscope_flag == 0:
        print("ERROR: Couldn't find the LSM scope")
        exit()

    img_height = np.shape(img_list[0])[1]
    img_width = np.shape(img_list[0])[2]
    z_width = [np.shape(img_list[i])[0] for i in range(pos_max)]
    
    #stitched image ax0 is going down, ax1 is to the right
    ax0_offset, ax1_offset, z_offset = [], [], []
    if findscope_flag == 2: #wil lsm, stitch horizontally
        ax0_offset = global_coords_px[:, 0] * -1  # ax0 = -Global X_DV
        ax1_offset = global_coords_px[:, 1]       # ax1 = Global Y_AP
    elif findscope_flag == 1:  # kla lsm, stitch vertically
        ax0_offset = global_coords_px[:, 1] # ax0 = Global Y_AP
        ax1_offset = global_coords_px[:, 0] # ax1 = Global X_DV
    z_offset = global_coords_px[:, 2]       # ax2 = Global Z_lr

    #find offset from min
    ax0_offset = np.ceil(ax0_offset - np.min(ax0_offset)).astype(int)
    ax1_offset = np.ceil(ax1_offset - np.min(ax1_offset)).astype(int)
    z_offset = np.ceil(z_offset - np.min(z_offset)).astype(int)

    #find max of each axis
    ax0_max = img_height + np.max(ax0_offset)
    ax1_max = img_width + np.max(ax1_offset)
    z_max = np.max(z_width) + np.max(z_offset)
    print(f'ax0_max: {ax0_max}, ax1_max: {ax1_max}, z_max: {z_max}')

    #create empty stitched image
    stitched_image = np.zeros([z_max, ax0_max, ax1_max], dtype=np.uint16) #plane - z, rows-height, cols-width
    
    if not bg_sub:
        #stitch images
        for i, (z0, h0, w0) in enumerate(zip(z_offset, ax0_offset, ax1_offset)):
            stitched_image[z0:z0+z_width[i], h0:h0+img_height, w0:w0+img_width] = img_list[i]
    else: #bg_sub
        #bg subtract all images to be stitched
        img_list_bg_sub = []
        for img in img_list:
            img_list_bg_sub.append(median_bg_subtraction(img))
        #stitch images
        for i, (z0, h0, w0) in enumerate(zip(z_offset, ax0_offset, ax1_offset)):
            stitched_image[z0:z0+z_width[i], h0:h0+img_height, w0:w0+img_width] = img_list_bg_sub[i]
    return(stitched_image)