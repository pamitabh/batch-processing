import os
import pathlib

import pandas as pd
from natsort import natsorted

import misc_functions_rplab

#raw string path to Acquisition folder
top_dir = input("Enter the path of top dir with all Acquisition folders for original images: ")

#add all folders with Acquisition in the name to a list
acq_folder_path_list = []
for root, dirs, files in os.walk(top_dir):
    for dir in dirs:
        if 'Acquisition' in dir:
            acq_folder_path_list.append(os.path.join(root, dir))

save_directory_default = os.path.expanduser(os.path.join("~", "Documents"))
save_directory = input("Enter the Save folder for original images [default-Documents]: ") or save_directory_default

save_directory = pathlib.Path(save_directory).joinpath(f"{pathlib.Path(top_dir).name}_delta_t")
save_directory.mkdir(parents=True, exist_ok=True)

df_per_fish_list = []
for acq_folder_path in acq_folder_path_list:
    acq_folder = pathlib.Path(acq_folder_path)

    for fish in natsorted([dir for dir in acq_folder.iterdir() if dir.is_dir()]):
        # times = {}
        tp_list, acq_folder_path_list, fish_list, channel_list, imaging_list, pos_list = [], [], [], [], [], []
        fish_folder = acq_folder.joinpath(fish)
        print(f"Processing {fish_folder}..")
        for pos in natsorted([dir for dir in fish_folder.iterdir() if dir.is_dir()]):
            pos_folder = fish_folder.joinpath(pos)
            for imaging in natsorted([dir for dir in pos_folder.iterdir() if dir.is_dir()]):
                imaging_folder = pos_folder.joinpath(imaging)
                for channel in natsorted([dir for dir in imaging_folder.iterdir() if dir.is_dir()]):
                    channel_folder = imaging_folder.joinpath(channel)
                    channel_time = {}
                    for tp in natsorted([dir for dir in channel_folder.iterdir() if dir.is_dir()]):
                        tp_folder = channel_folder.joinpath(tp)
                        meta = misc_functions_rplab.MMMetadata(tp_folder)
                        image_meta = meta.get_image_metadata(0)
                        try:
                            time_received = image_meta.image_metadata["ReceivedTime"]
                        except KeyError:
                            try:
                                time_received = image_meta.image_metadata["UserData"]["TimeReceivedByCore"]["scalar"]
                            except KeyError:
                                try:
                                    time_received = meta.summary_metadata["StartTime"]
                                except KeyError:
                                    pass
                        channel_time[tp.name] = time_received
                    #get time
                    tp_list.append(channel_time)
                    #get other info
                    acq_folder_path_list.append(acq_folder_path)
                    fish_list.append(fish.name)
                    pos_list.append(pos.name)
                    imaging_list.append(imaging.name)
                    channel_list.append(channel.name)
        
        # all_acq_times.append(times)
        df_one_fish = pd.DataFrame({'acquisition_start_time': tp_list, 
                                    'acquisition_path': acq_folder_path_list,
                                    'fish': fish_list,
                                    'pos': pos_list,
                                    'imaging_mode': imaging_list,
                                    'channel': channel_list
                                    })
        # delta_t_df = format_time_df(times)
        df_per_fish_list.append(df_one_fish)

all_df = pd.concat(df_per_fish_list, ignore_index=True)
all_df.to_csv(save_directory.joinpath("acquisition_times.csv"))
