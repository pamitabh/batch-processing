# Author(s): Piyush Amitabh
# Details: this code uses os.walk to traverse the parent directory and generates mip for all zstacks in it
# Created: May 02, 2023
# License: GNU GPL v3.0
# Comment: it is os agnostic

import os
import numpy as np
import skimage
import tifffile as tiff

#ask the user for the inputs
print('Warning: This code ONLY works with single channel z-stack tiff images. It will give unpredictable results with >3 dimensions')
main_dir = os.path.normpath(input('Enter the Parent directory where ALL the image stacks are stored: '))
bg_sub_flag = ''
while bg_sub_flag!='y' or bg_sub_flag!='n':
    bg_sub_flag = input('do you want median background subtraction? (y/n)')
    print('enter a valid value')

# Batchprocess MIP
channel_names = ['GFP', 'RFP']
for root, subfolders, filenames in os.walk(main_dir):
    for filename in filenames:
        # print(f'Reading: {filename}')
        filepath = os.path.join(root, filename)
        # print(f'Reading: {filepath}')
        filename_list = filename.split('.')
        og_name = filename_list[0] #first of list=name
        ext = filename_list[-1] #last of list=extension

        if ext=="tif" or ext=="tiff": #tiff files
            read_image = tiff.imread(filepath)

            if len(read_image.shape)==3: #check if 3D images
                print(f'Processing MIP for: {filepath}')
                if bg_sub_flag=='y':
                    arr_mip_wo_bg_sub = np.max(read_image, axis=0) #create MIP
                    arr_mip = arr_mip_wo_bg_sub - np.median(arr_mip_wo_bg_sub) #subtract median
                    arr_mip[arr_mip<0] = 0 #make all negative values zero
                else:
                    arr_mip = np.max(read_image, axis=0) #create MIP

                for ch_name in channel_names: #save mip array in right directory with correct channel name
                    if ch_name.casefold() in og_name.casefold():
                        dest = os.path.join(root, ch_name.casefold()+'_mip')
                        if not os.path.exists(dest): #check if the dest exists
                            print("Write path doesn't exist.")
                            os.makedirs(dest)
                            print(f"Directory '{ch_name.casefold()}_mip' created")

                        img_mip = skimage.util.img_as_uint(skimage.exposure.rescale_intensity(arr_mip))
                        if og_name.endswith('_MMStack_1'): #skip file
                            continue
                        elif og_name.endswith('_MMStack'): #remove 'MMStack' in saved name
                            save_name = og_name[:-len('_MMStack')]+'_mip.'+ext
                        else:
                            save_name = og_name+'_mip.'+ext
                        tiff.imwrite(os.path.join(dest, save_name), img_mip)