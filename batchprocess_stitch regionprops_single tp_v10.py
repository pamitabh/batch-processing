# %% [markdown]
# Author(s): Piyush Amitabh
# 
# Details: this code reads the csv files created by "segmentation_and_regionprops_v6_new.ipynb" and performs linking on it
# 
# Created: April 21, 2022
# 
# License: GNU GPL v3.0

# %% [markdown]
# Modified: May 9, 2022
# 
# Note: Added forward, backward check in time for NN and purged non-invertible NN functions

# %% [markdown]
# Modified: May 20, 2022
# 
# Note: Added graphs for keeping track of region-props in a trajectory

# %% [markdown]
# Modified: June 22, 2022
# 
# Note: cleaned code, added msd calculation for different time intervals

# %% [markdown]
# Modified: June 28, 2022
# 
# Note: read all position tables, and perform 3d volumetric stiching 
# also cleaned code

# %% [markdown]
# Modified: July 07, 2022
# 
# Note: processes new timelapse data, using the absolute reference positions given by the stage

# %% [markdown]
# Modified: Dec 15, 2022
# 
# Note: new axis system
# - Added the Global coordinates to the data frames as **"y-ap-um", "x-dv-um", "z-lr-um"** where ap is anterior to posterior axis, dv is dorsal to ventral axis, lr is left-right axis(*don't know the direction*, doesn't matter as long as the local and global are in the same direction)
# 
# - Changed NN algorithm to find the nearest neighbor based on spatial distance rather than pixel distance

# %% [markdown]
# Modified: Feb 22, 2023
# 
# Note: Removed all extra code. Purpose is to batchprocess and save df_super for each dataset

# %% [markdown]
# Modified: May 23, 2023
# 
# Note: changed to read data from the offset corrected caudal fin cut images
# added the code for finding the right notes.txt file for finding the stage coords and other automations

# %% [markdown]
# ----

# %% [markdown]
# Many parts rewritten and automated

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# %%
# from scipy import ndimage as ndi
# import napari
# from napari import layers
# from napari.utils.notebook_display import nbscreenshot #for screenshots of napari viewer
import skimage
# from PIL import Image, TiffTags
import tifffile as tiff
from scipy.spatial import distance

# %%
from tqdm import tqdm
import plotly.express as px
import plotly.graph_objects as go
# import dask
import seaborn as sns
import os
from natsort import natsorted
import configparser

# %% [markdown]
# # Read all tables

# %% [markdown]
# # User input

# %%
print('\nThis code will stitch the position of objects whose data is stored in regionprops tables')
print('Generate regionprops tables before running this')
print("Output will be saved in the 'stitched_regionprops' folder created inside the GFP/RFP_regionprops")
top_dir = input('\nEnter top directory containing ALL days of imaging data: ')
print("This directory contains\n", natsorted(os.listdir(top_dir)))

# %%
#all unique BF location gets added to the main_dir_list
main_dir_list = []
for root, subfolders, _ in os.walk(top_dir):
    if ('GFP' in subfolders) or ('RFP' in subfolders):
        main_dir_list.append(root)
print("Detected sub-folders with data:\n", main_dir_list)

# %%
pos_same_flag = input('Is the number of positions in all of above directories the same?(default-y/n) ') or 'y'

if pos_same_flag.casefold()=='y':
    pos_max = int(input('Enter number of positions/regions of imaging per timepoint (default=4): ') or '4')
    pos_max_list = [pos_max]*len(main_dir_list)
else:
    n= len(main_dir_list)
    # Below line read inputs from user using map() function
    pos_max_list = list(map(int, input("\nManually count and enter the pos numbers : ").strip().split()))[:n]

# %%
## Helping Functions
# check and create path
def check_create_save_path(save_path):
    save_path = os.path.normpath(save_path)
    if not os.path.exists(save_path):  # check if the dest exists
        print("Save path doesn't exist.")
        os.makedirs(save_path)
        print(f"Directory '{os.path.basename(save_path)}' created")
    else:
        print("Save path exists")
#finds stats of the passed np array
def find_stats(arr):
    print(f'Mean    {np.mean(arr):.2f}')
    print(f'Median  {np.median(arr):.2f}')
    print(f'Std     {np.std(arr):.2f}')
    print(f'COV     {(np.std(arr)/np.mean(arr)):0.2f}')
    print(f'Min     {np.min(arr):.2f}')
    print(f'Max     {np.max(arr):.2f}\n')
    return()

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

#removes dir and non-csv files from a list
def remove_non_csv_files(big_list, root_path):
    small_list = []
    for val in big_list:
        if os.path.isfile(os.path.join(root_path, val)): #file check
            filename_list = val.split('.')
            og_name = filename_list[0] 
            ext = filename_list[-1] 
            if (ext=="csv"): #csv check
                small_list.append(val)
    return small_list

#correct the file list ordering
def reorder_files_by_pos_tp(file_list):
    if len(file_list)<2: #just return the same list if 0 or 1 elements
        return(file_list)
    ordered_file_list = []
    for tp in range(1, (len(file_list)//pos_max) + 1):
        for pos in range(1, pos_max+1):
            for file_name in file_list: #find the location in img_list with pos and tp
                if (f'pos{pos}_' in file_name.casefold()) and (f'timepoint{tp}_' in file_name.casefold()):
                    ordered_file_list.append(file_name)
    return(ordered_file_list)

#Other Important functions
#---
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

def global_coordinate_changer(stage_coords):
    ''' accept stage_coords read from notes.txt to stitch images
        Returns: 2D np.array same shape as stage_coords
    '''
    stage_origin = stage_coords[0].copy()
    global_coords_um = stage_coords - stage_origin #set first stage position as zero
    if findscope_flag==0:
        print("ERROR: Couldn't find the LSM scope")
        exit()
    elif findscope_flag==1: #KLA LSM
        global_coords_um[:, 0] = global_coords_um[:, 0] * -1 #flip x axis
    elif findscope_flag==2: #WIL LSM
        global_coords_um[:, [1,0]] = global_coords_um[:, [0,1]]#swap x and y axis = 1st and 2nd columns
    else:
        print('Error: Findscope_flag not found.. exiting.')
        exit()
    #um to pixels: 1px = (1/pixel width) um
    #as the stage position is in x (col:axis-2), y(row:axis-1), z(plane:axis-0) format
    global_coords_px = global_coords_um/ [new_spacing[2], new_spacing[1], new_spacing[0]]
    return(global_coords_px)

#---
#start loop
for main_dir, pos_max in tqdm(zip(main_dir_list, pos_max_list)):

    #very general and robust code which looks for the files with those names instead of depending upon just the folder names
    sub_names = ['GFP', 'RFP']
    #csv files
    gfp_csv_flag, rfp_csv_flag = False, False #0 means not found, 1 mean found
    gfp_csv_path, rfp_csv_path = '', ''
    gfp_csv_list, rfp_csv_list = [], []
    #make a list of all 2D img files by channel to get a sample image to find scope and downscaling factor
    bf_flag, gfp_flag, rfp_flag = False, False, False  # 0 means not found, 1 mean found
    bf_path, gfp_mip_path, rfp_mip_path = '', '', ''
    bf_img_list, gfp_img_list, rfp_img_list = [], [], []

    for root, subfolders, filenames in os.walk(main_dir):
        for filename in filenames:
            # print(f'Reading: {filename}')
            filepath = os.path.join(root, filename)
            # print(f'Reading: {filepath}')
            filename_list = filename.split('.')
            og_name = filename_list[0] #first of list=name
            ext = filename_list[-1] #last of list=extension

            # find csv with 'info' - regionprop tables and NOT 'ofc' - offset corrected
            if (ext=="csv") and ('_info' in og_name.casefold()) and not('_ofc' in og_name.casefold()):
                    if (not gfp_csv_flag) and ('gfp' in og_name.casefold()):
                        print('GFP regionprop non-offset corrected csv found at: '+root)
                        gfp_csv_path = root
                        gfp_csv_list = reorder_files_by_pos_tp(remove_non_csv_files(natsorted(os.listdir(root)), root))
                        gfp_csv_flag = True
                    elif (not rfp_csv_flag) and ('rfp' in og_name.casefold()):
                        print('RFP regionprop non-offset corrected csv found at: '+root)
                        rfp_csv_path = root
                        rfp_csv_list = reorder_files_by_pos_tp(remove_non_csv_files(natsorted(os.listdir(root)), root))
                        rfp_csv_flag = True
            elif (ext == "tif" or ext == "tiff") and not(bf_flag or rfp_flag or gfp_flag): #just need one sample image
                if "bf" in og_name.casefold():  # find BF
                    print("BF images found at:" + root)
                    bf_path = root
                    bf_img_list = reorder_files_by_pos_tp(
                        remove_non_image_files(natsorted(os.listdir(root)), root)
                    )
                    bf_flag = True
                elif "mip" in og_name.casefold(): 
                    if "gfp" in og_name.casefold():
                        print("GFP MIP images found at:" + root)
                        gfp_mip_path = root
                        gfp_img_list = reorder_files_by_pos_tp(
                            remove_non_image_files(natsorted(os.listdir(root)), root)
                        )
                        gfp_flag = True
                    elif "rfp" in og_name.casefold():
                        print("RFP MIP images found at:" + root)
                        rfp_mip_path = root
                        rfp_img_list = reorder_files_by_pos_tp(
                            remove_non_image_files(natsorted(os.listdir(root)), root)
                        )
                        rfp_flag = True
    if not(bf_flag or rfp_flag or gfp_flag):
        print('''*NO* sample image (BF/GFP mip/RFP mip) found in {main_dir}
        Need a sample image to find scope parameters. Exiting..''')
        exit()
    if not gfp_csv_flag:
        print(f'*No* GFP regionprop non-offset corrected csv found in {main_dir}')
    if not rfp_csv_flag:
        print(f'*No* RFP regionprop non-offset corrected csv found in {main_dir}')
    if not(gfp_csv_flag or rfp_csv_flag):
        print("Need at least one channel csv tables to work.. None found.. Exiting..")

    # %%
    #read all region_prop csv and save in dict
    df_dict_gfp, df_dict_rfp = {}, {}
    ch_flag_list = [gfp_csv_flag, rfp_csv_flag]
    regionprop_path_list = [gfp_csv_path, rfp_csv_path]
    ch_csv_list = [gfp_csv_list, rfp_csv_list]

    for k, ch_flag in enumerate(ch_flag_list):
        all_csv_list = ch_csv_list[k]
        ch_name = sub_names[k]
        regionprop_path = regionprop_path_list[k]
        
        if ch_flag:
            for i in range(len(all_csv_list)//pos_max): #run once per timepoint
                df_dict_per_tp = {} #stores df for one tp

                for j in range(0, pos_max):
                    pos = j+1
                    loc = i*pos_max + j
                    csv_name = all_csv_list[loc]
                    print(f"Reading: {csv_name}")
                    df = pd.read_csv(os.path.join(regionprop_path, csv_name))
                    df['pos'] = pos #add a new column for storing positions
                    df_dict_per_tp[pos] = df
                
                if 'gfp' == ch_name.casefold(): #concat all csv per timepoint and save in dict
                    df_dict_gfp[i] = pd.concat(df_dict_per_tp, ignore_index=True)
                    print('save GFP timepoint now!')
                elif 'rfp' == ch_name.casefold(): #concat all csv per timepoint and save in dict
                    df_dict_rfp[i] = pd.concat(df_dict_per_tp, ignore_index=True)
                    print('save RFP timepoint now!')
                else:
                    print("Error: no GFP or RFP in channel name")

    # %% [markdown]
    # all the region-prop csv tables have been saved as dict values:
    # - all pos per tp concatenated and saved as single df
    # - key corresponding to timepoints (starting from 0)

    # %%
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    #     display(df_dict_gfp[1])

    # %% [markdown]
    # # Shift to Global Coords
    
    #find the nearest notes.txt
    config = configparser.ConfigParser()
    start_path = ''
    img = np.zeros((1,1)) #dummy
    #get start_path for search
    #get sample image to find scope and downscaling factor
    if gfp_flag:
        start_path = gfp_mip_path
        img_path = os.path.join(gfp_mip_path, gfp_img_list[0])
    elif rfp_flag:
        start_path = rfp_mip_path
        img_path = os.path.join(rfp_mip_path, rfp_img_list[0])
    elif bf_flag:
        start_path = bf_path
        img_path = os.path.join(bf_path, bf_img_list[0])
    img = tiff.imread(img_path)

    #find the fish number from the image path
    fish_num = int(
        img_path[img_path.casefold().rfind("fish") + len("fish")]
    )  # find fish number starting from the img_nameprint(f'Found fish_num = {fish_num}')
    print(f'Found fish_num = {fish_num}')

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
    orig_spacing = np.array([zd, yd, xd]) #change to the actual pixel spacing from the microscope
    new_spacing = np.array([zd, yd*ds_h, xd*ds_w]) #downscale x&y by n
    print("Pixel width (plane, row, col): ", new_spacing)

    # %% [markdown]
    # original camera pixel width is 1µm in the z (leading!) axis, and  0.1625µm in the x and y axes.
    # 
    # for downsampled by 4, this will be orig pixel_width*4 

    # %% [markdown]
    # #df.loc[condition, column_name] = new_val

    # %% [markdown]
    # To correct for the offset and stitch different acquisition positions together, note the following:
    # - regionprops generates local coords of objects in the image as *axis-0,1 and 2*: this is our our **Local coords system**
    # - stage positions is saved by micromanager and obtained from the metadata as *XPositionUm*, similarly for y and z: this is our **Global coords system**
    # 
    # The direction of Global coords system is different in Klamath LSM and Willamette LSM. 
    # Klamath LSM:
    # - Global +Z <-> Local axis-0 (same direction) needs to be verified for each acquisition 
    # - Global +Y <-> Local axis-1 (same direction) same for all acquisition as it corresponds to fish AP axis and in conventional setup fishes are held vertically w head-up
    # - Global -X <-> Local axis-2 (inverse direction) same for all acquisition
    # 
    # To resolve the inverse directions between global x and local axis-2, I am flipping the global coordinate system's x axis.
    # 
    # #update this
    # Willamete LSM:
    # - Global +Z <-> Local axis-0 (same direction) needs to be verified for each acquisition 
    # - Global +X <-> Local axis-2 (same direction) same for all acquisition as it corresponds to fish AP axis and in conventional setup fishes are held vertically w head-up
    # - Global +Y <-> Local axis-1 (same direction) same for all acquisition
    # 
    # To resolve the flipped axes between global x/y and stage x/y, I am exchanging the global coordinate system's axis.

    # %% [markdown]
    # Finally add the Global coordinates to the data frames as **"y-ap-um", "x-dv-um", "z-lr-um"** where ap is anterior to posterior axis, dv is dorsal to ventral axis, lr is left-right axis(*don't know the direction*, doesn't matter as long as the local and global are in the same direction)

    global_coords_px = global_coordinate_changer(stage_coords)

    # %%
    #read all df
    for k, ch_flag in enumerate(ch_flag_list):
        ch_name = sub_names[k]

        if (ch_flag==True) and (ch_name.casefold()=='gfp'):
            for i in df_dict_gfp.keys():
                df = df_dict_gfp[i]
                for j in range(pos_max):
                    df.loc[df.pos==j+1, 'shifted-centroid_weighted-0']= df['centroid_weighted-0'] + global_coords_px[j][2] #z
                    df.loc[df.pos==j+1, 'shifted-centroid_weighted-1']= df['centroid_weighted-1'] + global_coords_px[j][1] #y
                    df.loc[df.pos==j+1, 'shifted-centroid_weighted-2']= df['centroid_weighted-2'] + global_coords_px[j][0] #x

        elif (ch_flag==True) and (ch_name.casefold()=='rfp'):
            for i in df_dict_rfp.keys():
                df = df_dict_rfp[i]
                for j in range(pos_max):
                    df.loc[df.pos==j+1, 'shifted-centroid_weighted-0']= df['centroid_weighted-0'] + global_coords_px[j][2] #z
                    df.loc[df.pos==j+1, 'shifted-centroid_weighted-1']= df['centroid_weighted-1'] + global_coords_px[j][1] #y
                    df.loc[df.pos==j+1, 'shifted-centroid_weighted-2']= df['centroid_weighted-2'] + global_coords_px[j][0] #x

    # %%
    #add x-dv, y-ap, z-lr to the df
    for k, ch_flag in enumerate(ch_flag_list):
        ch_name = sub_names[k]

        if (ch_flag==True) and (ch_name.casefold()=='gfp'):
            for i in df_dict_gfp.keys():
                df = df_dict_gfp[i]
                #add global coords value in pixels
                df['x-dv-px'] = df['shifted-centroid_weighted-2']
                df['y-ap-px'] = df['shifted-centroid_weighted-1']
                df['z-lr-px'] = df['shifted-centroid_weighted-0']
                #add global coords value in um
                df['x-dv-um'] = df['x-dv-px']*new_spacing[2]
                df['y-ap-um'] = df['y-ap-px']*new_spacing[1]
                df['z-lr-um'] = df['z-lr-px']*new_spacing[0]
                
        elif (ch_flag==True) and (ch_name.casefold()=='rfp'):
            for i in df_dict_rfp.keys():
                df = df_dict_rfp[i]
                #add global coords value in pixels
                df['x-dv-px'] = df['shifted-centroid_weighted-2']
                df['y-ap-px'] = df['shifted-centroid_weighted-1']
                df['z-lr-px'] = df['shifted-centroid_weighted-0']
                #add global coords value in um
                df['x-dv-um'] = df['x-dv-px']*new_spacing[2]
                df['y-ap-um'] = df['y-ap-px']*new_spacing[1]
                df['z-lr-um'] = df['z-lr-px']*new_spacing[0]

    # %%
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    #     display(df_dict_gfp[1])

    # %% [markdown]
    # # df Super Sever
    # %%
    if gfp_csv_flag:
        # make df_super
        if len(df_dict_gfp)!=1:
            print('This code only works for single tp images, use batchprocess linking for time lapse data')
            exit()
        df_super_gfp = df_dict_gfp[0]
        # save in the same directory as the regionprops path in a new folder
        gfp_results_save_path = os.path.join(gfp_csv_path, 'stitched_regionprops')
        check_create_save_path(gfp_results_save_path)
        # save df_super
        df_super_gfp.to_csv(os.path.join(gfp_results_save_path, 'df_super_gfp.csv'))
    else:
        print('Could not save gfp df_super')
        
    if rfp_csv_flag:
        if len(df_dict_gfp)!=1:
            print('This code only works for single tp images, use batchprocess linking for time lapse data')
            exit()
        df_super_rfp = df_dict_rfp[0]
        rfp_results_save_path = os.path.join(rfp_csv_path, 'stitched_regionprops')
        check_create_save_path(rfp_results_save_path)
        # save df_super
        df_super_rfp.to_csv(os.path.join(rfp_results_save_path, 'df_super_rfp.csv'))
    else:
        print('Could not save rfp df_super')

    # %% [markdown]
    # Now df_super has:
    # - all properties mentioned above
    # - severed tracks by volume variation
    # 
    # and it is saved in the stitched_regionprops folder
    gfp_html_name = 'neutrophil_3d scatter.html'
    rfp_html_name = 'macrophage_3d scatter.html'
    if gfp_csv_flag:
        fig2 = px.scatter_3d(df_super_gfp, z='x-dv-um', y='y-ap-um', x='z-lr-um') #type:ignore
        fig2.update_layout(
            autosize=True,
            scene=dict(aspectmode='data'))
        fig2.write_html(os.path.join(gfp_results_save_path, gfp_html_name))
        print(f"saved  {gfp_html_name}")
        
    if rfp_csv_flag:        
        fig2 = px.scatter_3d(df_super_rfp, z='x-dv-um', y='y-ap-um', x='z-lr-um') #type:ignore
        fig2.update_layout(
            autosize=True,
            scene=dict(aspectmode='data'))
        fig2.write_html(os.path.join(rfp_results_save_path, rfp_html_name))
        print(f"saved {rfp_html_name}")    