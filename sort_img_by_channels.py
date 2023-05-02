import os
import shutil

#this code will only work to sort images if the filename has the channel name(BF/GFP/RFP)

sub_dirs = ['BF', 'GFP', 'RFP']
print('This code will sort images ONLY if the filename has the channel name(BF/GFP/RFP)')
flag = input('Sort Images into different directories by channel? (y/n)')
if flag.casefold().startswith("y"):
    print("ok, creating directories and sorting images..")
else:
    print('Okay, bye!')
    exit()

read_dir = input('Enter the Root directory containing ALL images to be sorted: ')

for root, subfolders, filenames in os.walk(read_dir):
    for filename in filenames:        
        filepath = os.path.join(root, filename)
        # print(f'Reading: {filepath}')
        filename_list = filename.split('.')
        og_name = filename_list[0] #first of list=name
        ext = filename_list[-1] #last of list=extension

        if ext=="tif" or ext=="tiff": #only if tiff file
            #check image channel and create directory if it doesn't exist
            for sub in sub_dirs:
                if sub.casefold() in og_name.casefold():
                    dest = os.path.join(root, sub)
                    if not os.path.exists(dest): #check if the subdir exists
                        print("Read path doesn't exist.")
                        os.makedirs(dest)
                        print(f"Directory '{sub}' created")

                    shutil.move(filepath, dest) #move files