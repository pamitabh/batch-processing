# %% [markdown]
# Author(s): Piyush Amitabh
# 
# Details: this code reads zstacks of images, downsamples and saves them as a single tiff file
# 
# Created: July 05, 2022
# 
# License: GNU GPL v3.0

# %% [markdown]
# Edited: Aug 19, 2022
# 
# comment: changed for working on chiron

# %% [markdown]
# made os agnostic and for running with custom file structures
# removed all print statements from the loops

# %%
import os, shutil
import numpy as np
import matplotlib.pyplot as plt

import skimage
import skimage.transform
from skimage import io
from PIL import Image, TiffTags
import tifffile as tiff

# %%
from tqdm import tqdm

# %% [markdown]
# # helper functions and constants

# %%
#function to enhance and show images
def show_image(img, img_title='', color=False, max_contrast=False):
    fig = plt.figure(figsize=(20,15))
    img = np.array(img)
    if max_contrast==True:
        enhance = skimage.exposure.equalize_hist(img)
    else:
        enhance = img
    if color==False:
        plt.imshow(enhance, cmap='gray')
    else:
        plt.imshow(enhance)
    plt.title(img_title)
    plt.colorbar()
    plt.axis("off")
    plt.show()

# %%
#find the stats of array (can take time)
def find_stats(ar):
    mean_xtrain = np.mean(ar)
    std_xtrain = np.std(ar)
    max_xtrain = np.max(ar)
    min_xtrain = np.min(ar)
    print(f'Stats: mean={mean_xtrain:.3f}, std={std_xtrain:.3f}, min={min_xtrain}, max={max_xtrain}')

# %% [markdown]
# The pixel spacing in this dataset is 1µm in the z (leading!) axis, and  0.1625µm in the x and y axes.

# %% [markdown]
# n is the downscaling factor in x and y, change it accordingly.

# %%
n = input('Enter downscaling factor for x and y dimensions (hit enter for default=4):') or 4
if type(n)!=int or n<=0:
    print('User Error: downscaling factor has to be a positive integer')
    exit()

zd, xd, yd = 1, 0.1625, 0.1625 #pixel width units = um/pixel
zd_new, xd_new, yd_new = zd, xd*n, yd*n
# orig_spacing = np.array([zd, xd, yd]) #change to the actual pixel spacing from the microscope
# new_spacing = np.array([zd, xd*n, yd*n]) #downscale x&y by n

# %% [markdown]
# # Define folder structure

# %% [markdown]
# Change below folder structure and specify the positions (e.g. 'Pos1' to 'Pos5'), and timepoints (e.g. 'Timepoint1' to 'Timepoint80')

# %% [markdown]
# Assuming the folder structure is of the form: 
# 
# main dir -> Acquisition dir -> {fish1 dir, fish2 dir, etc.} + notes.txt

# %%
main_dir =  r'Z:\Piyush_Galadriel\time lapse_10_12_22_night' #this should contain acquisition folder
poses = [f'Pos{x}' for x in range(1, 5+1)]
sub_dirs = [os.path.join('snap', 'BF'), 'zStack']
channels = ['GFP', 'RFP']
timepoints = [f'Timepoint{x}' for x in range(1, 80+1)]

# %%
save_path = r'G:\Piyush_Mowgli\piyush_data_conv_downsampled\time lapse_10_12_22_night'

print(f"Main Dir (should contain 'Acquisition' sub-dir): {main_dir}")
print(f'subdirs:\n {poses}\n {sub_dirs}\n {channels}\n {timepoints}')
print(f"Target Dir (save location for downsamp images): {save_path}")
flag = input('If this is incorrect, change it in the code. Continue? (y/n):')
if(flag.casefold()!='y'):
    print("ok, Sayonara!!")
    exit()

print(f"Sample folder structure below:")
print(os.path.join(main_dir, 'Acquisition', 'Fish1', poses[0], sub_dirs[0], timepoints[0]))
flag = input('If this is incorrect, change it in the code. Continue? (y/n):')
if(flag.casefold()!='y'):
    print("ok, Sayonara!!")
    exit()

# %%
src_path = os.path.join(main_dir, 'Acquisition') #copy all text file inside acquisition
files = os.listdir(src_path)

for filename in files:
    filename_list = filename.split('.')
    og_name = filename_list[0] #first of list=name
    ext = filename_list[-1] #last of list=extension

    if ext=="txt": #copy text files
        shutil.copy(os.path.join(src_path,filename), save_path)
        print(f'copied file: {filename}')

# %%
new_src_path = os.path.join(main_dir, 'Acquisition', 'Fish1') #this should contain the pos sub-dirs

# %% [markdown]
# # Check Sample Image

# %%
# check sample image
read_path = os.path.join(new_src_path, poses[0], sub_dirs[0], timepoints[0])
listfiles = []
for img_files in sorted(os.listdir(read_path)):
        if img_files.endswith(".tif"):
            listfiles.append(img_files)
     
print("Reading first image...")
first_image = tiff.imread(os.path.join(read_path, listfiles[0]))
# io.imshow(first_image)

print(f"First Image Succesfully Read!. Shape = {first_image.shape}")

# %% [markdown]
# # Downsample and Save all Images

# %%
def read_zstack_v2(read_path): #reads image at read_path returning the downsampled image, v2 can take care of single images or image stacks
    listfiles =[]
    for img_files in sorted(os.listdir(read_path)):
        if img_files.endswith(".tif"):
            listfiles.append(img_files)

    print(f'Reading: {os.path.join(read_path, listfiles[0])}')
    samp_img = tiff.imread(os.path.join(read_path, listfiles[0]))
    # print(samp_img.shape)

    if len(samp_img.shape)==2: #2 dimensional image, e.g. BF image or multiple z slice
        print('single-stack image')
        stack_full = np.zeros((len(listfiles),samp_img.shape[0]//n,samp_img.shape[1]//n))#,np.uint16)
        if len(listfiles)==1:
            img_downscaled = skimage.transform.downscale_local_mean(samp_img, (n, n)) #as already read that image
            stack_full[0,:,:] = img_downscaled
            print(f'Shape of image {stack_full.shape}')
        else:
            for i, val in enumerate(listfiles):
                print(f'Reading: {os.path.join(read_path, val)}')
                img = tiff.imread(os.path.join(read_path, val))
                img_downscaled = skimage.transform.downscale_local_mean(img, (n, n)) #use a kernel of nxn, this will downscale by a factor of n in both x & y
                stack_full[i,:,:] = img_downscaled
            print(f'Shape of image {stack_full.shape}')

    elif len(samp_img.shape)==3: #z stack
        print('multi-stack image')
        stack_full = np.zeros((samp_img.shape[0],samp_img.shape[1]//n,samp_img.shape[2]//n))

        if len(listfiles)==1: #there is only one img file and read in samp
            img_downscaled = skimage.transform.downscale_local_mean(samp_img, (1, n, n)) #use a kernel of nxn, this will downscale by a factor of n in both x & y
            stack_full = img_downscaled
        else:
            print("Change looping sequence to process a folder with multiple 3d images")
            return

    else:
        print("Can't process images with >3dimensions")
        return    

    if stack_full.shape[0]==1: #single page image, e.g. BF image
        return((np.squeeze(stack_full, axis=0)).astype('uint16'))
    else: #image zstack, multi-page tiff
        return(stack_full.astype('uint16'))

# %%
for pos in tqdm(poses, desc=' pos') : 
    for sub_dir in tqdm(sub_dirs, desc=' subdir(snap/zStack)'):
        for channel in tqdm(channels, desc=' channel'):
            for tp in tqdm(timepoints, desc=' timepoints'):
                if 'Snap'.casefold() in sub_dir.casefold(): #check if its brightfield folder
                    read_path = os.path.join(new_src_path, pos, sub_dir, tp)
                    save_name = tp+'_'+pos+'_'+'BF'+'_ds.ome.tif'
                else:
                    read_path = os.path.join(new_src_path, pos, sub_dir, channel, tp)
                    save_name = tp+'_'+pos+'_'+channel+'_ds.ome.tif'
        
                img_stack = read_zstack_v2(read_path)
                if len(img_stack.shape)==2:
                    m_data = {'axes': 'YX'}
                else: 
                    m_data = {'axes': 'ZYX', 'spacing': 1/10000, 'unit': 'CENTIMETER'}
                tiff.imwrite(os.path.join(save_path, save_name), read_zstack_v2(read_path), resolution=(1./(yd_new/10000), 1./(xd_new/10000)), resolutionunit='CENTIMETER', dtype=img_stack.dtype, shape=img_stack.shape, ome=True);

# %% [markdown]
# ---

# %% [markdown]
# # Appendix

# %% [markdown]
# check different downscaling algorithms

# %%
# from skimage.transform import rescale, resize, downscale_local_mean

# image = tiff.imread(dir+listfiles[250])


# image_rescaled = rescale(image, 0.25, anti_aliasing=False)
# image_resized = resize(image, (image.shape[0] // 4, image.shape[1] // 4),
#                        anti_aliasing=True)
# image_downscaled = downscale_local_mean(image, (4, 4))

# fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15,15))

# ax = axes.ravel()

# ax[0].imshow(image, cmap='gray')
# ax[0].set_title("Original image")

# ax[1].imshow(image_rescaled, cmap='gray')
# ax[1].set_title("Rescaled image (aliasing)")

# ax[2].imshow(image_resized, cmap='gray')
# ax[2].set_title("Resized image (no aliasing)")

# ax[3].imshow(image_downscaled, cmap='gray')
# ax[3].set_title("Downscaled image (no aliasing)")

# ax[0].set_xlim(0, 512)
# ax[0].set_ylim(512, 0)
# plt.tight_layout()
# plt.show()
# io.imsave('./rescaled_alias.png', image_rescaled)
# io.imsave('./resized_no alias.png', image_resized)
# io.imsave('./downscaled_mean.png', image_downscaled)


