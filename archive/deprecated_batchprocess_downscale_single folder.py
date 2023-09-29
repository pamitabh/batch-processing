# %% [markdown]
# Author(s): Piyush Amitabh
# 
# Details: this code reads tiff images from a folder, downsamples and saves them as a single tiff file
# 
# Created: Jan 10, 2023
# 
# License: GNU GPL v3.0

# %%
import os
import numpy as np
import skimage
from skimage import io
# from PIL import Image, TiffTags
import tifffile as tiff

# %%
from tqdm import tqdm

# %% [markdown]
# # helper functions and constants

# %% [markdown]
# The pixel spacing in this dataset is 1µm in the z (leading!) axis, and  0.1625µm in the x and y axes.

# %% [markdown]
# n is the downscaling factor in x and y, change it accordingly.

# %%
n = input('Enter downscaling factor for x and y dimensions (none for default=4):') or 4
if type(n)!=int or n<=0:
    print('User Error: downscaling factor has to be a positive integer')
    exit()

# %%
# n = 4 #downscaling factor in x and y
zd, xd, yd = 1, 0.1625, 0.1625
orig_spacing = np.array([zd, xd, yd]) #change to the actual pixel spacing from the microscope
new_spacing = np.array([zd, xd*n, yd*n]) #downscale x&y by n

# %%
print(f'Original pixel spacing in z,x,y is {zd, xd, yd}')
flag = input('If this is incorrect, change it in the code. Continue? (y/n):')
if(flag.casefold()!='y'):
    exit()

# %% [markdown]
# # Input Image location

# %%
# flag = input('Is this a (a)2D image or (b)3D image?')
# if(flag.casefold()=='a'):
#     num_dimensions = 2
# elif(flag.casefold()=='b'): 
#     num_dimensions = 3
# else: 
#     print('User Error: Wrong option entered.. exiting.')
#     exit()

# %%
source_path = input('Enter the directory with images to be downscaled:\n')

source_path = source_path+'/' if source_path[-1] != '/' else source_path #standardize path names
# source_dir = source_path.split('/')[-2]

default_loc = source_path+'downscaled'
save_dir = input('Enter the location where you want to save the Downscaled images (None for default location):\n') or default_loc
save_dir = save_dir+'/' if save_dir[-1] != '/' else save_dir #standardize path names

print(f'Images will be downscaled\nFrom: {source_path}\nTo  : {save_dir}')

# %%
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# %% [markdown]
# # Downsample and Save all Images

# %%
# check sample image
listfiles = []
for img_files in sorted(os.listdir(source_path)):
        if img_files.endswith(".tif"):
            listfiles.append(img_files)

# %%
def read_n_downscale_image(read_path):
    # stack_full = np.zeros((len(listfiles),first_image.shape[0]//n,first_image.shape[1]//n))#,np.uint16)

    print(f'Reading: {read_path}')
    img = tiff.imread(read_path)
    # stack_full[i,:,:] = img_downscaled
    print(f'Shape of read image {img.shape}')
    if img.shape[0]==1: #single page image, e.g. BF image
        img_downscaled = skimage.transform.downscale_local_mean(img, (n, n)) #use a kernel of nxn, this will downscale by a factor of n in both x & y
    else: #image zstack, multi-page tiff
        img_downscaled = skimage.transform.downscale_local_mean(img, (1, n, n)) #use a kernel of nxn, this will downscale by a factor of n in both x & y
    
    return(img_downscaled)

# %%
for filename in tqdm(listfiles):
    read_path = source_path + filename

    filename_list = filename.split('.')
    name = filename_list[0] #first of list=name
    ext = filename_list[-1] #last of list=extension
    # break
    tiff.imwrite(save_dir+name+'_ds.'+ext, read_n_downscale_image(read_path))

# %% [markdown]
# ---
