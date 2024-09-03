import os
import pathlib
from copy import deepcopy

import pandas as pd
from natsort import natsorted

import misc_functions_rplab

#raw string path to Acquisition folder
acq_folder_path = input("Enter the path of Acquisition folder for original images: ")

save_directory_default = os.path.expanduser(os.path.join("~", "Documents"))
save_directory = input("Enter the Save folder for original images [default-Documents]: ") or save_directory_default

acq_folder = pathlib.Path(acq_folder_path)
save_directory = pathlib.Path(save_directory).joinpath(f"{acq_folder.parent.name}_delta_t")
save_directory.mkdir(parents=True, exist_ok=True)

def format_time_df(times):
    delta_t_df = pd.DataFrame(times)
    delta_t_df = delta_t_df.reset_index()
    # Rename colnames
    col_names = ['bf_snap_acq_start_time', 'gfp_ztack_acq_start_time', 'rfp_ztack_acq_start_time']
    delta_col_names = [f'delta_({col})_s' for col in col_names]
    delta_t_df = delta_t_df.rename(columns={'index': 'time_point',
                                            'BF snap': col_names[0],
                                            'GFP zstack': col_names[1],
                                            'RFP zstack': col_names[2]})
    #parse to get time_point in integer
    delta_t_df['time_point'] = delta_t_df['time_point'].str.extract(r'(\d+)').astype(int)

    for col_name, del_col_name in zip(col_names, delta_col_names) : #run for all columns except the time_point
        delta_t_df[col_name] = pd.to_datetime(delta_t_df[col_name]) #str to datetime objects
        delta_t_df[del_col_name] = (pd.to_datetime(delta_t_df[col_name])).diff().dt.total_seconds() #del t
        # only keep the time, drop the year
        # delta_t_df[col] = delta_t_df[col].dt.time
    mean_values = delta_t_df[delta_col_names].mean()
    # print(mean_values)
    std_values = delta_t_df[delta_col_names].std()
    # print(std_values)
    coe_df = (std_values/mean_values) * 100
    if len(coe_df[coe_df>5])>0: #give error if coe more than 5%
        print("ERROR:: Bad acquisition time interval (coe > 5%). Listed below..")
        print('Mean values:')
        print(mean_values[coe_df>5])
        print('STD values:')
        print(std_values[coe_df>5])
    else:
        print("**Good** acquisition time interval (coe < 5%)..")
        print('Mean values:')
        print(mean_values)
    return(delta_t_df)

for fish in natsorted([dir for dir in acq_folder.iterdir() if dir.is_dir()]):
    times = {}
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
                times[f"{channel.name} {imaging.name}"] = deepcopy(channel_time)

    delta_t_df = format_time_df(times)
    delta_t_df.to_csv(save_directory.joinpath(f"{fish.name}_delta_t.csv"))